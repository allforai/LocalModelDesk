"""Replay the saved comparison requests against an already loaded model.
No loading, downloading, scoring by an LLM, or modification of baseline results.
"""
import argparse,json,time,urllib.request,urllib.error,subprocess
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--comparison-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--gateway",default="http://127.0.0.1:8770")
    parser.add_argument("--desk",default="http://127.0.0.1:8766")
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    def save(name,value):
        (args.output/(name+".json")).write_text(json.dumps(value,ensure_ascii=False,indent=2))
    def get(url):
        with urllib.request.urlopen(url,timeout=5) as r:return json.load(r)
    status=get(args.desk+"/api/llm/status")
    assert status["state"]["status"]=="loaded" and status["state"]["model_key"]=="qwen38-flash-next"
    def measure():
        return {"desk_memory":get(args.desk+"/api/memory"),"swap":subprocess.check_output(["sysctl","vm.swapusage"],text=True).strip(),"os_pressure_level":int(subprocess.check_output(["sysctl","-n","kern.memorystatus_vm_pressure_level"],text=True)),"processes":subprocess.check_output(["ps","-axo","pid=,rss=,comm="],text=True).splitlines()}
    def call(name,body):
        body["model"]="qwen38-flash-next"
        save(name+"-request",body)
        before=measure(); started=time.time()
        req=urllib.request.Request(args.gateway+"/v1/chat/completions",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=1200) as r:
                raw_bytes=r.read();http_status=r.status
            (args.output/(name+"-response.json")).write_bytes(raw_bytes)
            raw=json.loads(raw_bytes)
            out={"infrastructure_ok":True,"response":raw,"content":raw["choices"][0]["message"].get("content"),"finish_reason":raw["choices"][0]["finish_reason"],"seconds":time.time()-started}
        except urllib.error.HTTPError as e:
            (args.output/(name+"-response.json")).write_bytes(e.read())
            out={"infrastructure_ok":False,"error":str(e),"http_status":e.code,"seconds":time.time()-started}
        except Exception as e:
            out={"infrastructure_ok":False,"error":str(e),"seconds":time.time()-started}
        out.update(started_at=started,finished_at=time.time(),memory_before=before,memory_after=measure())
        save(name,out); print(name,out["infrastructure_ok"],round(out["seconds"],2),out.get("finish_reason"),flush=True)
        return out
    results={}
    for name in ["intervals","toposort","extraction","writing","reasoning","fiction","reasoning-thinking","vision","tool-first"]:
        body=json.loads((args.comparison_root/"gemma"/(name+"-request.json")).read_text())
        results[name]=call(name,body)
        if name=="tool-first" and results[name]["infrastructure_ok"]:
            message=results[name]["response"]["choices"][0]["message"]
            calls=message.get("tool_calls") or []
            valid=len(calls)==1 and calls[0]["function"]["name"]=="get_stock" and json.loads(calls[0]["function"]["arguments"])=={"sku":"SKU-Z17"}
            results[name]["score"]={"passed":int(valid),"total":1};save(name,results[name])
            if valid:
                body["messages"] += [message,{"role":"tool","tool_call_id":calls[0]["id"],"content":'{"sku":"SKU-Z17","available":13}'}]
                results["tool-final"]=call("tool-final",body)
        save("results",results)
    save("finished",{"time":time.time(),"status":get(args.desk+"/api/llm/status")})

if __name__=="__main__":main()
