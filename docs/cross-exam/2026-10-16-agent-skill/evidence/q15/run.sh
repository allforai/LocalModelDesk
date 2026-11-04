#!/bin/zsh
# $1=tag $2=prompt $3=signal
tag=$1; prompt=$2; sig=$3
ts(){ while IFS= read -r l; do echo "$(date +%T) $l"; done }
~/.local/bin/lmdesk image gen 盘问-排队 "$prompt" --size 1024x1024 >$tag-stdout.txt 2> >(ts >$tag-stderr.txt) &
pid=$!
echo $pid > $tag-pid.txt
for i in $(seq 1 60); do
  s=$(curl -s http://127.0.0.1:8766/api/media/job | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("status"),d.get("params",{}).get("prompt"))' 2>/dev/null)
  echo "$(date +%T) $s" >> $tag-jobpoll-pre.txt
  case "$s" in running*"$prompt"*) break;; esac
  sleep 2
done
sleep 15
echo "$(date +%T) sending $sig to $pid" >> $tag-jobpoll-pre.txt
ps -o pid,ppid,command -p $pid >> $tag-jobpoll-pre.txt
kill -$sig $pid
wait $pid; echo $? > $tag-exitcode.txt
for i in 1 2 3 4 5 6 7; do
  echo "== $(date +%T)" >> $tag-jobpoll-post.txt
  curl -s http://127.0.0.1:8766/api/media/job | python3 -c 'import sys,json;d=json.load(sys.stdin);d.pop("log",None);print(json.dumps(d,ensure_ascii=False))' >> $tag-jobpoll-post.txt
  sleep 5
done
~/.local/bin/lmdesk image show 盘问-排队 > $tag-show.txt 2>&1
