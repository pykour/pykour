#!/usr/bin/env bash

echo
pykour run main:app --workers $1 > /dev/null 1>&1 &
pid=$!

sleep 5

wrk -t8 -c$2 -d3s --latency http://127.0.0.1:8000/ > report.txt

kill $pid
