#!/bin/bash
# run a command, sample its RssAnon/RssFile every 0.1 s, print the maxima
"$@" > probe.out 2>&1 &
pid=$!; ma=0; mf=0
while kill -0 $pid 2>/dev/null; do
  read a f < <(awk '/RssAnon/{a=$2}/RssFile/{f=$2}END{print a+0, f+0}' /proc/$pid/status 2>/dev/null)
  [ "${a:-0}" -gt $ma ] && ma=$a; [ "${f:-0}" -gt $mf ] && mf=$f
  sleep 0.1
done
wait $pid; echo "exit $? ; max anon $((ma/1024)) MB, max file-backed $((mf/1024)) MB"
