#!/bin/zsh
# usage: run_ask.sh tag model
E=/Users/aa/LocalModelDesk/docs/cross-exam/2026-10-16-agent-skill/evidence/q41
t=$1; m=$2
( while true; do echo "=== $(date +%H:%M:%S)"; curl -s localhost:8766/api/state | python3 -c 'import sys,json;d=json.load(sys.stdin);print("state holder=",d.get("holder"),"holders=",d.get("holders"),"media_busy=",d.get("media_busy"))'; curl -s localhost:8766/api/llm/status | python3 -c 'import sys,json;d=json.load(sys.stdin);print("llm",json.dumps(d["state"],ensure_ascii=False),"loaded_model=",d.get("loaded_model"),"active_chats=",d.get("active_chats"),"ui_recent=",d.get("ui_chat_recent"),"loaded_by=",d.get("loaded_by"))'; sleep 5; done > $E/$t-samples.txt 2>&1 ) &
sp=$!
echo "start $(date +%H:%M:%S)" > $E/$t-meta.txt
~/.local/bin/lmdesk ask "用一个词回答：草是什么颜色" --model $m --timeout 240 </dev/null > $E/$t-stdout.txt 2> >(while IFS= read -r l; do echo "$(date +%H:%M:%S) $l"; done > $E/$t-stderr.txt)
echo $? > $E/$t-exit.txt
echo "end $(date +%H:%M:%S)" >> $E/$t-meta.txt
sleep 1; kill $sp
