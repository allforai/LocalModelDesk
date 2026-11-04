import subprocess, sys, time, json, signal, urllib.request, threading, os
tag, delay, nparts, sigdelay_mode = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
A,B="2b687f6bf28c42cf87855751878a5cd3","a9173d38223c4e8b9150c75b4ee44997"
parts=[A,B]*(nparts//2)
t0=time.time()
def ts(): return f"{time.time()-t0:7.3f}"
def job():
    try:
        d=json.load(urllib.request.urlopen("http://127.0.0.1:8766/api/media/job"));d.pop("log",None);return d
    except Exception as e: return {"err":str(e)}
out=open(f"{tag}-stdout.txt","w");errf=open(f"{tag}-stderr.txt","w")
p=subprocess.Popen(["/Users/aa/.local/bin/lmdesk","video","join","验收-视频",*parts],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
def rd(f,o):
    for l in f: o.write(f"[{ts()}] {l}");o.flush()
th=[threading.Thread(target=rd,args=(p.stdout,out)),threading.Thread(target=rd,args=(p.stderr,errf))]
[t.start() for t in th]
log=open(f"{tag}-timeline.txt","w")
def L(s): log.write(f"[{ts()}] {s}\n");log.flush()
if sigdelay_mode=="onsubmit":
    # wait until stderr has '已提交'
    while "已提交" not in open(f"{tag}-stderr.txt").read() and p.poll() is None: time.sleep(0.02)
time.sleep(delay)
L(f"job before signal: {json.dumps(job(),ensure_ascii=False)}")
if p.poll() is None:
    L("send SIGINT"); p.send_signal(signal.SIGINT)
else: L(f"process already exited rc={p.returncode}")
for i in range(7):
    L(f"poll{i*5}s job={json.dumps(job(),ensure_ascii=False)}  rc={p.poll()}")
    time.sleep(5)
p.wait();[t.join() for t in th]
L(f"exit code {p.returncode}")
