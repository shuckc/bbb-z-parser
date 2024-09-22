class BitIterator:
    """bytes are indexed low to high, bits are indexed MSB down to LSB.
    Within a n-bit stride read, the highest bit of the n returned is
    the highest unread bit"""

    def __init__(self, bs: bytes):
        self.bs = bs
        self.bit_position = 0

    def __len__(self) -> int:
        return len(self.bs) * 8

    def reset(self) -> None:
        self.bit_position = 0

    def _get_16(self):
        bytepos, bit = divmod(self.bit_position, 8)
        i = int(self.bs[bytepos]) << 8
        if bytepos < len(self.bs) - 1:
            i += int(self.bs[bytepos + 1])
        # if bit is 0, highest bit is in the right place, otherwise
        # shift left by bit
        return i << bit

    def read_bit1(self) -> int:
        # return 0 or 1
        if self.remain() < 1:
            raise IndexError
        r = (self._get_16() & 0x8000) >> 15
        self.bit_position += 1
        return r

    def read_bit2(self) -> int:
        # return 0..3
        if self.remain() < 2:
            raise IndexError
        r = (self._get_16() & 0xC000) >> 14
        self.bit_position += 2
        return r

    def read_bit8(self) -> int:
        if self.remain() < 8:
            raise IndexError
        # return 0..255
        r = (self._get_16() & 0xFF00) >> 8
        self.bit_position += 8
        return r

    def remain(self) -> int:
        return len(self) - self.bit_position
