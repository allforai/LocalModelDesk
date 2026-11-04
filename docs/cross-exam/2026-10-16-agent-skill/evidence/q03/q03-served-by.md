host: local filesystem only; temp HOME from mktemp -d (tmp.ImUjLpOtz7, deleted after); unrelated symlink target tmp.Bgc49rroAg (deleted); no network
process: dist python3.13 (Contents/Resources/python/bin/python3.13), PYTHONPATH=dist Resources, PYTHONDONTWRITEBYTECODE=1, driver q03-driver.py -> AgentSkillService(mode=bundle) -> installer.apply (real code, real filesystem operations)
mock_layers: none (no response of the system under test was replaced by fake data)
test conditions (not mock layers):
  - which=lambda c: None injected into AgentSkillService: makes command-based detection report "not found". Affects only the "detected" field in each row (detection falls back to path existence). Does not affect link_state / install / uninstall decisions or any filesystem result.
  - HOME is a temp dir passed as the home argument (not an env override): all link/file operations land there.
  - PYTHONDONTWRITEBYTECODE=1 so the dist bundle is not written to.
checked_absent: real ~ not touched; running dist app not touched; no stub/mock server; no MSW/json-server
