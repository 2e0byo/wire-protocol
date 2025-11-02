#!/usr/bin/env bash
SRV=${SRV:-localhost}
PORT=${PORT:-8000}
curl -v "http://$SRV:$PORT"
