# Native shell visual acceptance runbook

This is a human-only reality gate for the menu bar, Dock, and native dialogs. Orca
cannot inspect these surfaces (`menubar/dock/dialogs = false`), so do not fabricate
automation evidence or a signoff.

## Preparation

- Start the packaging-produced LocalModelDesk `.app` (or the binary built by
  `scripts/build-shell-app.sh` with a fake service). Do not use a real model workload
  or unrelated listener while testing.
- Capture a screenshot or recording for each observation and retain the relevant
  command output. Run listener checks with:

  ```sh
  lsof -iTCP:8766 -sTCP:LISTEN
  lsof -iTCP:8767 -sTCP:LISTEN
  ```

## Checks

1. **Dock — R-shell-05.** After launch, LocalModelDesk has a Dock icon, participates
   in Command-Tab, and clicking its Dock icon activates its window.
2. **Menu-bar appearance — R-shell-02.** A status text item starts as `启动中…` and,
   when ready, becomes `空闲`. Its menu contains exactly the status-detail row, a
   memory row in the form `内存 已用 x.x / 共 y GiB`, `打开窗口`, and `退出`.
3. **Menu-bar freshness — R-shell-02.** Load an LLM or start a video job; within ten
   seconds the title becomes `已加载 …` or `出片中`. If those modules are unavailable,
   alter the fake service `/api/state` payload and record the resulting title; defer
   real-model coupling to its integration phase.
4. **Window recovery — R-shell-03.** Close the window. The menu-bar item remains and
   port 8766 remains listening. `打开窗口` and a Dock click each restore the window
   with its content unchanged.
5. **First run — R-shell-07.** Temporarily rename or remove the configuration to
   trigger first run. Confirm the three-button NSAlert. `选择其他目录…` must open a
   native NSOpenPanel that selects directories only and permits directory creation.
   Complete default, custom-directory, and legacy-adopt/point paths successfully.
   A read-only directory must show the server error text verbatim and allow `重选`.
6. **Quit cleanup — R-shell-04.** Select `退出`. The Dock icon and menu-bar item
   disappear, and both listener commands return no listeners.

## Evidence and verdict

The human reviewer, not this task, records per-check evidence in
`docs/superpowers/runs/2026-08-31-localmodeldesk-app/signoffs/shell-visual.md`.
All six checks must be observed. If any check fails, the shell is not accepted; fix it
and repeat this runbook. Only after all checks pass may the reviewer add this exact,
standalone line to the signoff:

```text
VERDICT: PASS
```
