host: local macOS; temp HOME (mktemp, deleted afterwards) and a separate temp cwd
process: dist python3.13 + PYTHONPATH=dist Resources, desk.agent_skill.installer.apply; pi v1.2.0 (/opt/homebrew/bin/pi) in a pty with --offline, only ctrl+o and "/skill" typed, no prompt sent
mock_layers: [] (nothing intercepts requests or replaces real backend responses; symlink operations and pi skill discovery were real)
test condition (not a mock layer): installer.apply was called with which=lambda c: None (injected command detection).
  Affected: only the "detected" field of each row (command-based detection returned false; path-based detection still ran against the temp HOME). 
  Not affected: state, target, message, result, shared_note, the symlinks created/removed, and pi's skill discovery.
checked_absent: [real ~ modified, model calls, lmdesk invoked, dist app touched, MSW/json-server/stub switches]
