# Native shell visual acceptance

This human-only gate covers surfaces Orca computer-use cannot observe: menu bar, Dock, and native dialogs.

1. Confirm LocalModelDesk appears in Dock, participates in Command-Tab, and reopens its window from the Dock.
2. Confirm the menu-bar item transitions from starting to idle and exposes status, memory, open-window, and quit entries.
3. Confirm the menu-bar status updates within ten seconds when an LLM or media job becomes active.
4. Close the window and confirm the service stays alive; reopen from both menu bar and Dock without losing state.
5. Trigger first run and confirm the NSAlert/NSOpenPanel directory flows, including a server error shown verbatim for a bad path.
6. Quit and confirm the app, menu item, and listeners on ports 8766/8767 all disappear.
7. Record screenshots/video and command output in
   `docs/superpowers/runs/2026-08-31-localmodeldesk-app/signoffs/shell-visual.md`.
8. Only when every check passes, add a standalone line: `VERDICT: PASS`.
