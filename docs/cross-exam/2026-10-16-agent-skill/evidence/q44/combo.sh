#!/bin/bash
# usage: combo.sh a|b 1|2|3
E=$1; C=$2; D=/Users/aa/LocalModelDesk/docs/cross-exam/2026-10-16-agent-skill/evidence/q44; P=$D/run-$E$C; mkdir -p $P
front(){ osascript -e 'tell application "System Events" to get name of first process whose frontmost is true' 2>&1; }
# ensure running, then quit
if ! pgrep -f 'LocalModelDesk.app/Contents/MacOS/LocalModelDesk' >/dev/null; then open /Users/aa/LocalModelDesk/dist/LocalModelDesk.app; sleep 6; fi
echo "pre-quit: $(ps -axo pid,ppid,lstart,args | grep -E 'LocalModelDesk|desk' | grep -v grep)" > $P/prequit.txt
MAIN=$(pgrep -f 'LocalModelDesk.app/Contents/MacOS/LocalModelDesk'|head -1)
if [ $E = a ]; then osascript -e 'tell application "LocalModelDesk" to quit' >$P/quit.out 2>&1; else kill $MAIN; fi
for i in $(seq 1 40); do sleep 0.5; pgrep -f 'LocalModelDesk.app' >/dev/null || break; done
sleep 1
echo "after-quit procs: $(pgrep -fl 'LocalModelDesk.app')" > $P/postquit.txt
lsof -nP -iTCP:8766 -sTCP:LISTEN >> $P/postquit.txt 2>&1; echo "listen-lines: $(lsof -nP -iTCP:8766 -sTCP:LISTEN | wc -l)" >> $P/postquit.txt
osascript -l JavaScript $D/snap.js > $P/windows-before.json; echo "front-before: $(front)" > $P/front-before.txt
# poller
( for i in $(seq 1 600); do ps -axo pid,ppid,lstart,args | grep -E 'desk.agent_cli|bin/lmdesk' | grep -v grep; sleep 0.05; done >> $P/argv-raw.txt ) &
POLL=$!
S=$(python3 -c 'import time;print(time.time())')
case $C in
1) ~/.local/bin/lmdesk status --json </dev/null >$P/stdout.txt 2>$P/stderr.txt; RC=$?;;
2) env -i HOME=$HOME PATH=/usr/bin:/bin ~/.local/bin/lmdesk status --json </dev/null >$P/stdout.txt 2>$P/stderr.txt; RC=$?;;
3) ~/.local/bin/claude -p "运行 ~/.local/bin/lmdesk status --json 并原样告诉我输出" --allowedTools Bash </dev/null >$P/stdout.txt 2>$P/stderr.txt; RC=$?;;
esac
EN=$(python3 -c 'import time;print(time.time())')
echo "rc=$RC elapsed=$(python3 -c "print(round($EN-$S,2))")" > $P/result.txt
sleep 3
echo "listen: $(lsof -nP -iTCP:8766 -sTCP:LISTEN | tail -n +2)" >> $P/result.txt
ps -axo pid,ppid,lstart,args | grep -E 'LocalModelDesk|python3.13' | grep -v grep > $P/spawned-procs.txt
for p in $(pgrep -f 'LocalModelDesk.app/Contents/MacOS/LocalModelDesk'); do ps -o pid,ppid,lstart,command -p $p; PP=$(ps -o ppid= -p $p); ps -o pid,ppid,lstart,command -p $PP; done >> $P/spawned-procs.txt 2>&1
osascript -l JavaScript $D/snap.js > $P/windows-after.json; echo "front-after: $(front)" > $P/front-after.txt
sleep 2; kill $POLL 2>/dev/null; wait 2>/dev/null
for f in result postquit front-before front-after; do cat $P/$f.txt; done; echo STDOUT; head -c 600 $P/stdout.txt; echo STDERR; head -c 400 $P/stderr.txt; echo WIN; cat $P/windows-after.json | head -c 600; echo; echo ARGV; sort -u $P/argv-raw.txt | tee $P/argv-poll.txt
