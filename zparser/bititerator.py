class BitIterator:
    """bytes are indexed low to high, bits are indexed MSB down to LSB.
    Within a n-bit stride read, the highest bit of the n returned is
    the highest unread bit"""

    def __init__(self, bs: bytes):
        self.bs = bs
        self.bit_position = 0

    def __len__(self) -> int:
        return len(self.bs) * 8

    def __repr__(self) -> str:
        return f"BitIterator(bitpos={self.bit_position},bitlen={len(self)},sz={len(self.bs)})"

    def reset(self) -> None:
        self.bit_position = 0

    def _get_8(self) -> int:
        """Return the next 8 unread bits, without moving the read pointer.
        First unread bit is shifted to the MSB of the 8-bit result. The read
        may stride over 1 or 2 bytes of the input buffer. If the 2nd byte
        would be beyond the buffer it reads as zero.
        """
        bytepos, bit = divmod(self.bit_position, 8)
        i = int(self.bs[bytepos]) << 8
        if bytepos < len(self.bs) - 1:
            i += int(self.bs[bytepos + 1])
        # if bit is 0, highest bit is in the right place, otherwise
        # shift left by bit
        return (i << bit) >> 8

    def read_bit1(self) -> int:
        # return 0 or 1
        if self.remain() < 1:
            raise IndexError()
        r = (self._get_8() & 0x80) >> 7
        self.bit_position += 1
        return r

    def read_bit2(self) -> int:
        # return 0..3
        if self.remain() < 2:
            raise IndexError()
        r = (self._get_8() & 0xC0) >> 6
        self.bit_position += 2
        return r

    def read_bit8(self) -> int:
        # return 0..255
        if self.remain() < 8:
            raise IndexError()
        r = self._get_8() & 0xFF
        self.bit_position += 8
        return r

    def remain(self) -> int:
        return len(self) - self.bit_position
