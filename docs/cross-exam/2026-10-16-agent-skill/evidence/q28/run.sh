#!/bin/bash
E=$(pwd); B=http://127.0.0.1:8766
ts(){ python3 -c 'import time;print("%.3f"%time.time())'; }
: > timeline.txt
# sampler
( while [ ! -f stop ]; do t=$(ts); echo "== $t" >> timeline.txt; curl -s -m 5 $B/api/llm/status </dev/null >> timeline.txt; echo >> timeline.txt; curl -s -m 5 $B/api/media/job </dev/null | python3 -c 'import sys,json
try:
 d=json.load(sys.stdin); d.pop("log",None); print(json.dumps(d,ensure_ascii=False))
except Exception as e: print("ERR",e)' >> timeline.txt; sleep 3; done ) &
SP=$!
# stream
python3 - <<'PY' > stream_events.txt 2> stream_stderr.txt &
import urllib.request,json,time
body=json.dumps({"messages":[{"role":"user","content":"请写一篇约800字的中文文章，主题是樱花与春天。"}],"max_tokens":4096}).encode()
req=urllib.request.Request("http://127.0.0.1:8766/api/llm/chat/stream",data=body,headers={"Content-Type":"application/json"})
print("%.3f START"%time.time(),flush=True)
n=0
try:
  with urllib.request.urlopen(req,timeout=900) as r:
    print("%.3f HTTP %s"%(time.time(),r.status),flush=True)
    for line in r:
      n+=1
      print("%.3f %s"%(time.time(),line.decode().rstrip()),flush=True)
except Exception as e:
  print("%.3f EXC %r"%(time.time(),e),flush=True)
print("%.3f END lines=%d"%(time.time(),n),flush=True)
PY
STP=$!
sleep 1.5
echo "$(ts) lmdesk start" > lmdesk_start.txt
perl -e 'alarm 1000; exec @ARGV' ~/.local/bin/lmdesk image gen 盘问-排队 "一棵樱花树" --size 512x512 --steps 8 --timeout 900 </dev/null > lmdesk_stdout.txt 2> >(while IFS= read -r l; do echo "$(ts) $l"; done > lmdesk_stderr.txt)
echo $? > lmdesk_exit.txt
echo "$(ts) lmdesk end" >> lmdesk_start.txt
wait $STP
sleep 4
touch stop; wait $SP; rm -f stop
