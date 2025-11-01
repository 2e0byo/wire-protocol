#!/usr/bin/env bash
ETH=${ETH:-any}
SRV=${SRV:-localhost}
PORT=${PORT:-8000}
# workaround for permissions
mkdir shark || true
chmod a+rwx shark

sudo tshark \
  -i $ETH \
  -f "tcp and host $SRV and port $PORT" \
  --hexdump all \
  -a duration:10 \
  -w shark/tcp.pcap \
  > shark/capture.log 2>&1

sudo mv shark/tcp.pcap ./
sudo mv shark/capture.log ./
sudo chown john tcp.pcap
sudo chown john capture.log
rmdir shark
