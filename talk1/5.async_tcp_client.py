#!/usr/bin/env python3
"""
Slightly off-piste, but the blocking socket API isn't the nicest. Asyncio gives
us file-like abstractions on top which I prefer to work with, so I thought I'd
show them here. Hopefully this shows you (if you've wondered) why `async` (i.e.
coorperative multitasking) has taken all the languages by storm: look how nice
this kind of network code becomes!
"""

import asyncio
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Response:
    status_code: int
    headers: dict[str, list[str]]
    body: str


async def get_url(url: str) -> Response:
    scheme, rest = url.split("://")
    assert scheme == "http", f"This basic client only supports http, got {scheme}"
    netloc, sep, rest = rest.partition("/")
    path = (sep + rest) or "/"
    assert "@" not in netloc, "This basic client doesn't handle credentials"
    if ":" in netloc:
        netloc, port = netloc.split(":")
        port = int(port)
    else:
        port = 80

    return await get(netloc, port, path)


async def get(srv: str, port:int, path: str) -> Response:
    reader, writer = await asyncio.open_connection(srv, port)
    writer.write(f"GET {path} HTTP/1.1\r\n".encode())
    writer.write(f"Host: {srv}\r\n".encode())
    writer.write(b"\r\n")
    await writer.drain()

    state = "status"
    headers = defaultdict(list)
    body = b""
    async for line in reader:
        match (line, state):
            case (b"", _):
                break
            case (status, "status"):
                protocol, status, *msg = status.split()
                assert protocol.lower() == b"http/1.1", protocol
                status = int(status)
                state = "header"
            case (b"\r\n", "header"):
                state = "body"
                break
            case (header, "header"):
                k, _, v = header.partition(b": ")
                headers[k.decode().lower()].append(v.decode().strip())

    assert state == "body"
    if (length := headers.get("content-length")):
        # headers is a dict[str, list[str]]
        length = int(length[0])
        body = await reader.read(length)
        assert len(body) == length
    else:
        body = await reader.read()

    return Response(status, dict(headers), body.decode())

if __name__ == "__main__":
    resp = asyncio.run(get_url("http://localhost:8000"))
    print(resp)

