import pty,os,sys,time,select,re
home,text,out=sys.argv[1:4]
env=dict(os.environ,HOME=home,PI_OFFLINE="1")
pid,fd=pty.fork()
if pid==0:
    os.chdir(os.environ["PICWD"]); os.execvpe("pi",["pi","--offline","--tui-mode","regular","--no-session"],env)
buf=b""
def rd(t):
    global buf
    end=time.time()+t
    while time.time()<end:
        r,_,_=select.select([fd],[],[],0.3)
        if r:
            try: buf+=os.read(fd,65536)
            except OSError: return
rd(4); os.write(fd,text.encode().decode("unicode_escape").encode("latin1")); rd(4)
os.write(fd,b"\x03"); rd(1); os.write(fd,b"\x03"); rd(1)
try: os.kill(pid,9)
except: pass
s=re.sub(rb"\x1b\[[0-9;?<>=]*[a-zA-Z]|\x1b\][^\x07\x1b]*(\x07|\x1b\\)",b"",buf).decode(errors="replace")
open(out,"w").write(s)
