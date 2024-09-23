import array
import os
import struct
import sys
from collections import namedtuple
from io import BytesIO
import imageio
import numpy
import pycdlib
from zparser.bititerator import BitIterator

PAC_ENTRY = struct.Struct("<BLL12sHHL")


def print_installer_pac(v: bytes, fn: str):
    p = 0x80 - 8
    entrysz = 29
    data_from = 99999999
    tsize = 0
    for i in range(400):
        r = v[p : p + entrysz]
        flg, offset, typ, nameb, f1, f2, sz = PAC_ENTRY.unpack_from(r, 0)
        name = nameb.decode()
        if offset < data_from:
            data_from = offset
        print(f"  {flg} {offset:10} {typ:10} {name:10} {sz:8} {f1:6} {f2:6}")
        tsize += sz
        p += entrysz
        if p + entrysz > data_from:
            break
    print(f"position {p}")
    print(f"total outsize {tsize}")
    # print("head of buffer")
    # print(v[p:p+1000].hex())
    # print(v[p:p+1000])


def print_game_pac(v: bytes, fn: str) -> None:
    assert v[0:5] == bytes.fromhex("00000000FF")
    assert v[-4:] == b"JMP2"
    entries = struct.unpack("<L", v[-8:-4])[0]
    entrysz = 24
    s = len(v) - 8 - entries * entrysz
    print(f" entries {entries} sz {len(v)} s {s}")
    for i in range(entries):
        r = v[s : s + entrysz]
        s += entrysz
        name, flags, s1, s2 = struct.unpack("<12sLLL", r)
        assert flags == 0
        name = name.rstrip(b"\x00")
        print(f"  {name.decode():12} {flags:4} {s1:8} {s2:8}")


def check_file(func, iso, iso_path):
    print(iso_path)
    extracted = BytesIO()
    iso.get_file_from_iso_fp(extracted, iso_path=iso_path)
    func(extracted.getvalue(), iso_path.rstrip(";1").replace("/", "-")[1:].lower())


JV_FILEHEADER = struct.Struct("<2sBB76sHHHHLLBB6x")
assert JV_FILEHEADER.size == 104
JV_TABLE_ENTRY = struct.Struct("<LLLBBBx")
assert JV_TABLE_ENTRY.size == 16

JVFileHeader = namedtuple(
    "JVFileHeader", "jv pm1 pm2 copy w h frames fdelay maxchunk freq flags vol"
)
JVTableEntry = namedtuple(
    "JVTableEntry", "chunksz audiosz videosz palette audiotype videotype"
)

VIDEOTYPE_COMP0 = 0
VIDEOTYPE_COMP1 = 1
VIDEOTYPE_BLANK = 2


def print_jv(v: bytes, fn: str) -> None:
    header = b" Compression by John M Phillips Copyright (C) 1995 The Bitmap Brothers Ltd.\x00"

    jv = JVFileHeader._make(JV_FILEHEADER.unpack_from(v, 0))
    assert jv.jv == b"JV"
    assert jv.copy == header
    print(
        f"  JV header w{jv.w:3} x h{jv.h} frames {jv.frames} rate {jv.fdelay}ms chunk {jv.maxchunk} afreq {jv.freq}"
    )
    s = JV_FILEHEADER.size

    # read 'tables'
    entry = []
    for i in range(jv.frames):
        tentry = JVTableEntry._make(JV_TABLE_ENTRY.unpack_from(v, s))
        s += JV_TABLE_ENTRY.size
        entry.append(tentry)
        assert tentry.audiotype == 0
        print(tentry)
        assert tentry.chunksz == tentry.audiosz + tentry.videosz + 768 * tentry.palette
        assert tentry.chunksz > 0
        assert 0 <= tentry.videotype < 3

    # read chunks
    # palette is 256*3 ie 8-bit indexed RGB
    chunks = []
    for tentry in entry:
        audio = v[s : s + tentry.audiosz]
        s += tentry.audiosz
        assert 0 <= tentry.palette <= 1
        psz = 768 * tentry.palette
        palette = v[s : s + psz]
        s += psz
        video = v[s : s + tentry.videosz]
        s += tentry.videosz
        chunks.append((audio, palette, video))

        if tentry.videotype == VIDEOTYPE_BLANK:
            assert len(video) == 1  # blank to palette index

    assert len(v) == s

    # audio is u8 pcm
    audio = b"".join([c[0] for c in chunks])
    with open(f"out/{fn}.pcm_u8", "wb") as w:
        w.write(audio)

    # video frames
    palette = b""
    pixels = jv.w * jv.h
    assert jv.w % 8 == 0
    assert jv.h % 8 == 0
    pix_index = array.array("B", [0] * pixels)
    rgb_index = array.array("B", [0] * pixels * 3)

    ims = []

    for entry, (a, p, v) in zip(entry, chunks):
        print(f"decoding frame")
        if p:
            palette = p
            assert len(palette) == 768

        # this is make_index_frame
        d = BitIterator(v)
        if entry.videotype == VIDEOTYPE_BLANK:
            assert len(v) == 1
            blank_index = d.read_bit8()
            for i in range(pixels):
                pix_index[i] = blank_index
            assert d.remain() == 0
        elif entry.videotype == VIDEOTYPE_COMP0:
            assert len(v) == 0
            # not sure ? Do we clear or zero the frame
        elif entry.videotype == VIDEOTYPE_COMP1:
            print(f"COMP1 data {len(v)}")
            ok = True
            while ok and d.remain() > 8:
                try:
                    for r in range(0, jv.h, 8):
                        for c in range(0, jv.w, 8):
                                bitstr_decode8x8(d, pix_index, r*jv.w + c, jv)
                except IndexError:
                    print('frame corrupted')
                    ok = False

                print(f"plotting {d.remain()}")
                # preview frame
                # unpack pix_index -> rgb_index using palette

                for i in range(pixels):
                    rgb_index[i*3 + 0] = palette[pix_index[i]*3 + 0]
                    rgb_index[i*3 + 1] = palette[pix_index[i]*3 + 1]
                    rgb_index[i*3 + 2] = palette[pix_index[i]*3 + 2]

                ar = numpy.array(rgb_index).reshape((jv.h, jv.w, 3))
                ims.append(ar)

    with open(f"out/{fn}.mp4", "wb") as w:
        # w.write(audio)
        imageio.mimwrite(w, ims, fps=int(1/jv.fdelay), format="mp4")


def bitstr_decode2x2(bitit, dest, idx, jv):
    mark = bitit.read_bit2()
    #print(f"   in 2x2 {idx} mark {mark} bi {bitit}")

    if mark == 0:
        # this 2x2 square is unchanged, return
        pass
    elif mark == 1:
        # set 4 pixels all same colour
        idx = bitit.read_bit8()
        for r in range(2):
            for c in range(2):
                dest[idx+c+ r*jv.w] = idx
    elif mark == 2:
        # read two different colour indexes (c0,c1), followed by
        # 4 single bits (one per pixel) to nominate c0 or c1
        c0c1 = [bitit.read_bit8(), bitit.read_bit8()]
        for r in range(2):
            for c in range(2):
                dest[idx+r*jv.w + c] = c0c1[bitit.read_bit1()]

    elif mark == 3:
        # copy 4 indexes
        for r in range(2):
            for c in range(2):
                origin = idx+r*jv.w+c
                dest[origin] = bitit.read_bit8()


def bitstr_decode4x4(bitit, dest, idx, jv):
    mark = bitit.read_bit2()
    #print(f"  in 4x4 {idx} mark {mark} bi {bitit}")
    if mark == 0:
        # this 4x4 square is unchanged, return
        pass
    elif mark == 1:
        # set 16 pixels all same colour
        idx = bitit.read_bit8()
        for r in range(4):
            for c in range(4):
                dest[idx+c+ r*jv.w] = idx
    elif mark == 2:
        # read two different colour indexes (c0,c1), followed by
        # 16 single bits (one per pixel) to nominate c0 or c1
        c0c1 = [bitit.read_bit8(), bitit.read_bit8()]
        for r in reversed(range(4)):
            # TODO: c-iter ordering bitstream.cpp:123 looks odd here
            for c in range(4):
                dest[idx+r*jv.w + c] = c0c1[bitit.read_bit1()]

    elif mark == 3:
        # decompose the 4x4 into 4 tiles of 2x2
        for r in range(0, 4, 2):
            for c in range(0, 4, 2):
                origin = idx+r*jv.w+c
                bitstr_decode2x2(bitit, dest, origin, jv)


def bitstr_decode8x8(bitit, dest, idx, jv):
    mark = bitit.read_bit2()
    #print(f" in 8x8 {idx} mark {mark} bi {bitit}")
    if mark == 0:
        # this 8x8 square is unchanged, return
        pass
    elif mark == 1:
        # set 64 pixels all same colour
        idx = bitit.read_bit8()
        for r in range(8):
            for c in range(8):
                dest[idx+c+ r*jv.w] = idx
    elif mark == 2:
        # read two different colour indexes (c0,c1), followed by
        # 64 single bits (one per pixel) to nominate c0 or c1
        c0c1 = [bitit.read_bit8(), bitit.read_bit8()]
        for r in reversed(range(8)):
            for c in range(8):
                dest[idx+r*jv.w + c] = c0c1[bitit.read_bit1()]

    elif mark == 3:
        # decompose the 8x8 into 4 tiles of 4x4
        for r in range(0, 8, 4):
            for c in range(0, 8, 4):
                origin = idx+r*jv.w+c
                bitstr_decode4x4(bitit, dest, origin, jv)



if __name__ == "__main__":
    iso = pycdlib.PyCdlib()
    iso.open(sys.argv[1])
    os.makedirs("out", exist_ok=True)

    for child in iso.list_children(iso_path="/"):
        print(child.file_identifier())
    for child in iso.list_children(iso_path="/Z/"):
        print(child.file_identifier())

    check_file(print_installer_pac, iso, "/Z.PAC;1")
    check_file(print_game_pac, iso, "/Z/MAIN.PAC;1")
    check_file(print_game_pac, iso, "/Z/HEADFX.PAC;1")
    check_file(print_game_pac, iso, "/Z/SHEADFX.PAC;1")
    check_file(print_game_pac, iso, "/Z/WARDATA.PAC;1")

    for child in iso.list_children(iso_path="/CUTS/"):
        print(child.file_identifier())
        if child.file_identifier().startswith(b"."):
            continue
        check_file(print_jv, iso, "/CUTS/" + child.file_identifier().decode())

    iso.close()
