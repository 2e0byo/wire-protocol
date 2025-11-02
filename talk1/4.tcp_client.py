#!/usr/bin/env python3
import socket
from typing import Iterator
from collections import defaultdict
from dataclasses import dataclass


def lines(conn) -> Iterator[bytes]:
    buffer = b""
    while True:
        chunk = conn.recv(1024)
        if not chunk:
            break
        while b"\r\n" in chunk:
            idx = chunk.index(b"\r\n") + 2
            yield (chunk[:idx] + buffer)
            chunk = chunk[idx:]
            buffer = b""
        if chunk:
            buffer = chunk

    if buffer:
        yield buffer


@dataclass
class Response:
    status_code: int
    headers: dict[str, list[str]]
    body: str


def get(srv: str, port: int = 80, path: str = "/") -> Response:
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )
    sock.connect((srv, port))
    sock.sendall(f"GET {path} HTTP/1.1\r\n".encode())
    sock.sendall(f"Host: {srv}:{port}\r\n".encode())
    sock.sendall(b"\r\n")
    state = "status"
    headers = defaultdict(list)
    body = b""
    status = None
    for line in lines(sock):
        match (line, state):
            case (status, "status"):
                protocol, status, *msg = status.split()
                assert protocol.lower() == b"http/1.1", protocol
                status = int(status)
                state = "header"
            case (b"\r\n", "header"):
                state = "body"
            case (header, "header"):
                k, _, v = header.partition(b": ")
                headers[k.decode().lower()].append(v.decode().strip())
            case (data, "body"):
                body += data
        if (length := headers.get("content-length")) and len(body) == length[0]:
            break

    return Response(status, dict(headers), body.decode())


def get_url(url: str) -> Response:
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
    return get(netloc, port, path)


if __name__ == "__main__":
    print(get_url("http://localhost:8000"))
