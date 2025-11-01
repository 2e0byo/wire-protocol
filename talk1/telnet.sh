#!/usr/bin/env bash
SRV=${SRV:-localhost}
PORT=${PORT:-8000}
# NOTE use telnet in live demo
nc $SRV $PORT <<EOF
GET / HTTP/1.1
Host: $SRV

EOF
