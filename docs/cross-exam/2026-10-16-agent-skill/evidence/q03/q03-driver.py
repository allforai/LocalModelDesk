import sys, json
from pathlib import Path
from desk.agent_skill.service import AgentSkillService
home=Path(sys.argv[1]); wanted=sys.argv[2].split(",") if sys.argv[2] else []
s=AgentSkillService(Path(sys.argv[3]),"bundle",home,which=lambda c:None)
print("skill_dir",s.skill_dir); print("cli_path",s.cli_path)
r=s.apply(wanted)
for t in r["targets"]: print(json.dumps(t,ensure_ascii=False))
print("cli",json.dumps(r["cli"],ensure_ascii=False))
