#!/usr/bin/env python3

import struct
from dataclasses import dataclass
from typing import ClassVar, Self
import pytest
from inline_snapshot import snapshot

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
    is_urgent: bool
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
        is_urgent = bool(data & 1)

        return cls(
            is_urgent,
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
        data |= self.is_urgent
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


#  Header = struct.Struct("")
class TestFlags:
    @pytest.mark.parametrize(
        "raw,attr",
        [
            (0b0000_0001, "is_finished"),
            (0b0000_0010, "is_synchronize"),
            (0b0000_0100, "is_reset"),
            (0b0000_1000, "is_push"),
            (0b0001_0000, "is_acknowledgement"),
            (0b0010_0000, "is_urgent"),
        ],
    )
    def test_attr_parsed_from_correct_bit(self, raw: int, attr: str):
        assert getattr(Flags.parse_raw(raw), attr)

    @pytest.mark.parametrize(
        "raw",
        [
            0b0000_0001,
            0b0000_0010,
            0b0000_0100,
            0b0000_1000,
            0b0001_0000,
            0b0010_0000,
            0b0011_1010,
        ],
    )
    def test_attr_round_tripped(self, raw: int):
        parsed = Flags.parse_raw(raw)

        assert parsed.into_raw() == raw

    def test_all_attrs_parsed(self):
        raw = 0b0010_1100

        parsed = Flags.parse_raw(raw)

        assert not parsed.is_finished
        assert not parsed.is_synchronize
        assert parsed.is_reset
        assert parsed.is_push
        assert not parsed.is_acknowledgement
        assert parsed.is_urgent


class TestHeader:
    def test_round_tripped(self):
        header = Header(
            source_port=123,
            destination_port=345,
            sequence_number=1,
            acknowledgment_number=2,
            data_offset=8,  # not actually correct...
            flags=Flags(
                is_urgent=True,
                is_acknowledgement=True,
                is_push=False,
                is_reset=False,
                is_synchronize=True,
                is_finished=False,
            ),
            window=234,
            checksum=23,
            urgent_pointer=23,
            options=b"\x04\x12\x23",
        )

        raw = header.into_raw()
        parsed = header.parse_raw(raw)

        assert header == parsed

    def test_parsed_from_wireshark_capture(self):
        # TODO figure out what this packet actually is
        raw = bytes.fromhex(
            "1f40e9bc749c4fe327c9123fa012ffcbfe3000000204ffd70402080a4a03ce6a4a03ce6a01030307"
        )
        parsed = Header.parse_raw(raw)

        assert parsed.source_port == 8_000
        assert parsed.destination_port == 59_836
        assert parsed.sequence_number == 1956401123
        assert parsed.acknowledgment_number == 667488831
        assert parsed.data_offset == 10  # todo handle data offset
        assert not parsed.flags.is_urgent
        assert parsed.flags.is_acknowledgement
        assert not parsed.flags.is_push
        assert not parsed.flags.is_reset
        assert parsed.flags.is_synchronize
        assert not parsed.flags.is_finished
        assert parsed.window == 65483
        assert parsed.options == bytes.fromhex(
            "0204ffd70402080a4a03ce6a4a03ce6a01030307"
        )

        assert parsed.header_length_bytes() == 40

    def test_parsed_from_wireshark_capture_of_request(self):
        raw_header = "e9bc1f4027c9123f749c4fe480180200fe7600000101080a4a03ce6a4a03ce6a"
        raw_payload = "474554202f20485454502f312e310d0a486f73743a206c6f63616c686f73743a383030300d0a557365722d4167656e743a206375726c2f382e31362e300d0a4163636570743a202a2f2a0d0a0d0a"
        raw_data = bytes.fromhex(raw_header + raw_payload)

        parsed = Header.parse_raw(raw_data)

        assert parsed.source_port == 59_836
        assert parsed.destination_port == 8_000
        assert parsed.acknowledgment_number == 1956401124
        assert parsed.sequence_number == 667488831
        assert parsed.data_offset == 8
        assert not parsed.flags.is_urgent
        assert parsed.flags.is_acknowledgement
        assert parsed.flags.is_push
        assert not parsed.flags.is_reset
        assert not parsed.flags.is_synchronize
        assert not parsed.flags.is_finished
        assert parsed.window == 512
        assert parsed.checksum == 0xFE76
        assert parsed.options == bytes.fromhex("0101080a4a03ce6a4a03ce6a")

        data = raw_data[parsed.header_length_bytes() :]

        assert data.decode() == snapshot("""\
GET / HTTP/1.1\r
Host: localhost:8000\r
User-Agent: curl/8.16.0\r
Accept: */*\r
\r
""")

    def test_parsed_from_wireshark_capture_of_response(self):
        raw_header = "1f40e9bc749c4fe427c9128d80180200feae00000101080a4a03ce6b4a03ce6a"
        raw_payload = "485454502f312e3120323030204f4b0d0a646174653a205361742c203031204e6f7620323032352031353a30303a353320474d540d0a7365727665723a20757669636f726e0d0a636f6e74656e742d6c656e6774683a2031310d0a636f6e74656e742d747970653a20746578742f706c61696e3b20636861727365743d7574662d380d0a0d0a"
        raw_data = bytes.fromhex(raw_header + raw_payload)

        parsed = Header.parse_raw(raw_data)

        assert parsed.source_port == 8_000
        assert parsed.destination_port == 59_836
        assert parsed.sequence_number == 1956401124
        assert parsed.acknowledgment_number == 667488909
        assert parsed.data_offset == 8
        assert not parsed.flags.is_urgent
        assert parsed.flags.is_acknowledgement
        assert parsed.flags.is_push
        assert not parsed.flags.is_reset
        assert not parsed.flags.is_synchronize
        assert not parsed.flags.is_finished
        assert parsed.window == 512
        assert parsed.checksum == 0xFEAE
        assert parsed.options == bytes.fromhex("0101080a4a03ce6b4a03ce6a")

        assert parsed.header_length_bytes() == 32

        data = raw_data[parsed.header_length_bytes() :]

        assert data.decode() == snapshot("""\
HTTP/1.1 200 OK\r
date: Sat, 01 Nov 2025 15:00:53 GMT\r
server: uvicorn\r
content-length: 11\r
content-type: text/plain; charset=utf-8\r
\r
""")

    def test_roundtrips_from_wireshark_capture_of_request(self):
        raw_header = "e9bc1f4027c9123f749c4fe480180200fe7600000101080a4a03ce6a4a03ce6a"
        raw_payload = "474554202f20485454502f312e310d0a486f73743a206c6f63616c686f73743a383030300d0a557365722d4167656e743a206375726c2f382e31362e300d0a4163636570743a202a2f2a0d0a0d0a"
        raw_data = bytes.fromhex(raw_header + raw_payload)

        parsed = Header.parse_raw(raw_data)
        dumped = parsed.into_raw() + raw_data[parsed.header_length_bytes() :]

        assert dumped == raw_data

    def test_roundtrips_from_wireshark_capture_of_response(self):
        raw_header = "1f40e9bc749c4fe427c9128d80180200feae00000101080a4a03ce6b4a03ce6a"
        raw_payload = "485454502f312e3120323030204f4b0d0a646174653a205361742c203031204e6f7620323032352031353a30303a353320474d540d0a7365727665723a20757669636f726e0d0a636f6e74656e742d6c656e6774683a2031310d0a636f6e74656e742d747970653a20746578742f706c61696e3b20636861727365743d7574662d380d0a0d0a"
        raw_data = bytes.fromhex(raw_header + raw_payload)

        parsed = Header.parse_raw(raw_data)
        dumped = parsed.into_raw() + raw_data[parsed.header_length_bytes() :]

        assert dumped == raw_data
