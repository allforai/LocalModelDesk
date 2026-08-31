# Packaging install acceptance

This human-only gate may modify `/Applications` and must not be run by an implementation agent.

1. Build and verify `dist/LocalModelDesk.app` with the repository scripts.
2. Install to `/Applications`; confirm Gatekeeper launch, correct bundle identity, icon, and first-run model-directory adoption.
3. Confirm embedded service startup, menu/Dock behavior, window reopening, and clean Quit.
4. Run the uninstall flow. Confirm the app and LaunchAgent are removed while user data remains by default.
5. Exercise purge only against an explicitly prepared disposable fixture, never the real model directories.
6. Record commands, timestamps, screenshots, bundle verification, and outcomes in
   `docs/superpowers/runs/2026-08-31-localmodeldesk-app/signoffs/packaging-reality.md`.
7. Only when every check passes, add a standalone line: `VERDICT: PASS`.
