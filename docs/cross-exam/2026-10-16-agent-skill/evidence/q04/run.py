import sys,json
from pathlib import Path
from desk.agent_skill import installer
R=Path(sys.argv[1]); home=Path(sys.argv[2]); keys=set(sys.argv[3].split(','))
print(json.dumps(installer.apply(home,R/"desk/agent_skill/bundled/local-model-desk",R/"bin/lmdesk",keys,which=lambda c:None),ensure_ascii=False,indent=1))
