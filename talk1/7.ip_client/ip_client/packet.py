#!/usr/bin/env python3

import struct
from dataclasses import dataclass
from typing import ClassVar, Self

# TODO: add newer flags
# TODO: parse options
# TODO: Frame class with header + data + checksum computation
# TODO: Add test for every frame in capture and work out what each is


@dataclass
class Flags:
    # later TCP has more flags here:
    # is_accurate_ecn
    # is_congestion_window_reduced
    # is ecn_echo
    urgent_data_follows: bool
    is_acknowledgement: bool
    is_push: bool
    is_reset: bool
    is_synchronize: bool
    is_finished: bool

    @classmethod
    def parse_raw(cls, data: int) -> Self:
        """
        Parse flags from the raw bits.

        This is not the most idiomatic way to do this, but it is the easiest to
        explain on camera. See `enum.IntFlag` for a more pythonic solution.
        """
        assert data < 2**6

        # >> is a bitwise left shift, filling from the right with zeros i.e.
        # 0b0011_0000 >> 2 == 0b0000_1100

        # bitwise and with 1 = zero out everything except the LSB.
        is_finished = bool(data & 1)
        data >>= 1
        is_synchronize = bool(data & 1)
        data >>= 1
        is_reset = bool(data & 1)
        data >>= 1
        is_push = bool(data & 1)
        data >>= 1
        is_acknowledgement = bool(data & 1)
        data >>= 1
        urgent_data_follows = bool(data & 1)

        return cls(
            urgent_data_follows,
            is_acknowledgement,
            is_push,
            is_reset,
            is_synchronize,
            is_finished,
        )

    def into_raw(self) -> int:
        """
        Turn flags into bitflags.

        This is also not the most idiomatic way to do this.
        """
        data = 0

        # << is a bitwise right shift, filling from the left with zeros i.e.
        # 0b0011_0000 << 2 == 0b1100_0000

        # bitwise or with bool interpreted as int = set LSB if bool
        data |= self.urgent_data_follows
        data <<= 1
        data |= self.is_acknowledgement
        data <<= 1
        data |= self.is_push
        data <<= 1
        data |= self.is_reset
        data <<= 1
        data |= self.is_synchronize
        data <<= 1
        data |= self.is_finished

        assert data < 2**8
        return data


@dataclass
class Header:
    source_port: int
    destination_port: int
    sequence_number: int
    acknowledgment_number: int
    data_offset: int
    flags: Flags
    window: int
    checksum: int
    urgent_pointer: int
    options: bytes

    _struct: ClassVar[struct.Struct] = struct.Struct(
        "!"  # big-endian (network byte order)
        "H"  # u16:     source_port
        "H"  # u16:     destination_port
        "L"  # u32:     sequence_number
        "L"  # u32:     acknowledgment_number
        "B"  # u8:      data offset + reserved
        "B"  # u8:      flags (as bitflags)
        "H"  # u16:     window
        "H"  # u16:     checksum
        "H"  # u16:     urgent_pointer
    )

    def header_length_bytes(self) -> int:
        return self.data_offset * 4

    @classmethod
    def parse_raw(cls, data: bytearray | bytes) -> Self:
        (
            source_port,
            destination_port,
            sequence_number,
            acknowledgment_number,
            offset,
            flags,
            window,
            checksum,
            urgent_pointer,
        ) = cls._struct.unpack(data[:20])
        # offset is the 4 high bits of offset
        offset >>= 4
        options_end = offset * 4
        options = bytes(data[20:options_end])

        flags = Flags.parse_raw(flags)

        return cls(
            source_port,
            destination_port,
            sequence_number,
            acknowledgment_number,
            offset,
            flags,
            window,
            checksum,
            urgent_pointer,
            options,
        )

    def into_raw(self) -> bytes:
        flags = self.flags.into_raw()
        return (
            self._struct.pack(
                self.source_port,
                self.destination_port,
                self.sequence_number,
                self.acknowledgment_number,
                self.data_offset << 4,
                flags,
                self.window,
                self.checksum,
                self.urgent_pointer,
            )
            + self.options
        )
