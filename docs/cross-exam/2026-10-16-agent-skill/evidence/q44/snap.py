import Quartz,subprocess,sys,json
pids=subprocess.run("pgrep -f LocalModelDesk.app/Contents/MacOS/LocalModelDesk",shell=True,capture_output=True,text=True).stdout.split()
pids={int(p) for p in pids}
w=Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll,Quartz.kCGNullWindowID)
out=[]
for x in w:
    if x.get('kCGWindowOwnerPID') in pids or 'LocalModelDesk' in (x.get('kCGWindowOwnerName') or ''):
        out.append({k:x.get(k) for k in ('kCGWindowOwnerName','kCGWindowName','kCGWindowIsOnscreen','kCGWindowLayer','kCGWindowOwnerPID')}|{'bounds':dict(x.get('kCGWindowBounds') or {})})
print(json.dumps({'n':len(out),'windows':out}))
