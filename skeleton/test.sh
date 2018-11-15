#!/bin/bash
for i in `seq 1 20`; do
curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.1:80/board' &
done