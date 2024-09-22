import pytest

from zparser.bititerator import BitIterator


def test_sv_bitarray():
    ba = BitIterator(b"\x6a\x1c")  # 0110 1010 0001 1100
    for d in "0110101000011100":
        assert ba.read_bit1() == int(d)
    assert ba.remain() == 0
    ba.reset()
    for d in "0110101000011100":
        assert ba.read_bit1() == int(d)
    assert ba.remain() == 0
    ba.reset()
    for i, d in enumerate("12220130"):
        print(i, d)
        assert ba.read_bit2() == int(d)
    ba.reset()
    for d in ["6A", "1C"]:
        assert ba.read_bit8() == int(d, 16)

    ba = BitIterator(b"\x01")
    len(ba) == 8
    assert ba.bit_position == 0

    assert ba.read_bit2() == 0
    assert ba.bit_position == 2
    assert ba.read_bit2() == 0
    assert ba.bit_position == 4

    assert ba.read_bit1() == 0
    assert ba.bit_position == 5

    assert ba.read_bit1() == 0
    assert ba.bit_position == 6

    assert ba.read_bit2() == 1
    assert ba.bit_position == 8

    with pytest.raises(IndexError):
        ba.read_bit1()

    with pytest.raises(IndexError):
        ba.read_bit2()

    with pytest.raises(IndexError):
        ba.read_bit8()

    ba = BitIterator(b"\xff\x00\xfe")
    assert ba.remain() == 24
    assert ba.read_bit8() == 255
    assert ba.read_bit8() == 0
    assert ba.remain() == 8
    assert ba.read_bit8() == 254
    assert ba.remain() == 0

    ba.reset()
    assert ba.remain() == 24
    assert ba.read_bit1() == 1  # top bit of FF
    assert ba.read_bit8() == 254  # FE
    assert ba.read_bit8() == 1  # 01
    assert ba.remain() == 7
    with pytest.raises(IndexError):
        ba.read_bit8()  # 01
    assert ba.read_bit2() == 3  # 11
    assert ba.read_bit2() == 3  # 11
    assert ba.read_bit2() == 3  # 11
    assert ba.remain() == 1
    with pytest.raises(IndexError):
        ba.read_bit2()  # 01
    assert ba.read_bit1() == 0  # 0
    assert ba.remain() == 0
    with pytest.raises(IndexError):
        ba.read_bit1()
