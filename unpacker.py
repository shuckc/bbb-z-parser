import sys
import pycdlib
from io import BytesIO
import struct

PAC_ENTRY = struct.Struct('<BLL12sHHL')
def print_installer_pac(v: bytes):
    p = 0x80 - 8
    entrysz = 29
    data_from = 99999999
    tsize = 0
    for i in range(400):
        r = v[p:p+entrysz]
        flg,offset,typ,nameb,f1,f2,sz = PAC_ENTRY.unpack_from(r, 0)
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


def print_game_pac(v: bytes) -> None:
    assert v[0:5] == bytes.fromhex("00000000FF")
    assert v[-4:] == b"JMP2"
    entries = struct.unpack("<L", v[-8:-4])[0]
    entrysz = 24
    s = len(v) - 8 - entries*entrysz
    print(f" entries {entries} sz {len(v)} s {s}")
    for i in range(entries):
        r = v[s:s+entrysz]
        s += entrysz
        name, flags, s1, s2 = struct.unpack('<12sLLL', r)
        assert flags == 0
        name = name.rstrip(b"\x00")
        print(f"  {name.decode():12} {flags:4} {s1:8} {s2:8}")

iso = pycdlib.PyCdlib()
iso.open(sys.argv[1])

for child in iso.list_children(iso_path='/'):
    print(child.file_identifier())
for child in iso.list_children(iso_path='/Z/'):
    print(child.file_identifier())
for child in iso.list_children(iso_path='/CUTS/'):
    print(child.file_identifier())


def check_file(func, iso, iso_path):
    print(iso_path)
    extracted = BytesIO()
    iso.get_file_from_iso_fp(extracted, iso_path=iso_path)
    func(extracted.getvalue())

check_file(print_installer_pac, iso, '/Z.PAC;1')
check_file(print_game_pac, iso, '/Z/MAIN.PAC;1')
check_file(print_game_pac, iso, '/Z/HEADFX.PAC;1')
check_file(print_game_pac, iso, '/Z/SHEADFX.PAC;1')
check_file(print_game_pac, iso, '/Z/WARDATA.PAC;1')

iso.close()
