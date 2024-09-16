import sys
import pycdlib
from io import BytesIO
import struct

PAC_ENTRY = struct.Struct('<B12sLLLL')
def print_pac(v: bytes):
    p = 0x80
    entrysz = 29

    tsize = 0
    for i in range(400):
        r = v[p+i*entrysz:p+(i+1)*entrysz]
        edir,nameb,f1,sz,f2,f3 = PAC_ENTRY.unpack_from(r, 0)
        name = nameb.decode()
        print(f" {i:03} {edir} {name:10} {sz:8} {f1:10} {f2:10}")
        if f3 != 0:
            break
        tsize += sz
    print(f"position {p+(i+1)*entrysz}")
    print(f"total outsize {tsize}")

iso = pycdlib.PyCdlib()
iso.open(sys.argv[1])

for child in iso.list_children(iso_path='/'):
    print(child.file_identifier())
for child in iso.list_children(iso_path='/Z/'):
    print(child.file_identifier())


def extract_pac(iso, iso_path):
    print(iso_path)
    extracted = BytesIO()
    iso.get_file_from_iso_fp(extracted, iso_path=iso_path)
    print_pac(extracted.getvalue())

extract_pac(iso, '/Z.PAC;1')
# extract_pac(iso, '/Z/MAIN.PAC;1')

iso.close()
