#! /usr/bin/env python3
import httpx

PORT = 8000
SRV = "localhost"


def fetch() -> str:
    return httpx.get(f"http://{SRV}:{PORT}").text


if __name__ == "__main__":
    print(fetch())
