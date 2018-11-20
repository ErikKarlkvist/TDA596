#!/bin/bash
for i in `seq 1 20`; do
curl -d 'entry=a'${i} -X 'POST' 'http://10.1.0.1:80/board' &
done
for i in `seq 1 20`; do
curl -d 'entry=b'${i} -X 'POST' 'http://10.1.0.4:80/board' &
done
for i in `seq 1 20`; do
curl -d 'entry=c'${i} -X 'POST' 'http://10.1.0.5:80/board' &
done
for i in `seq 1 20`; do
curl -d 'entry=d'${i} -X 'POST' 'http://10.1.0.8:80/board' &
done