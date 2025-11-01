#!/usr/bin/env python3
"""
A very basic FastAPI server.

This talk is about the client, not the server, so we just use an off-the-shelf
library you're probably already familiar with here.
"""
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.get("/")
def root() -> PlainTextResponse:
    return PlainTextResponse("hello world")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)

