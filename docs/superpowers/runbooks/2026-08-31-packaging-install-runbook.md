# LocalModelDesk macOS installation reality-gate runbook

This is a human-only gate. It intentionally installs into `/Applications`, opens a
desktop app, and may stop local services. Do not run it from an implementation
agent. Do not use real model directories for any destructive check.

Record the operator, macOS version, date/time, every command's exit status, and
screenshots in
`docs/superpowers/runs/2026-08-31-localmodeldesk-app/signoffs/packaging-reality.md`.
That signoff is evidence, not a template to pre-fill: add `VERDICT: PASS` as a
standalone final line only after every required check has passed.

## 0. Preconditions and evidence

From the repository root, record the checkout commit and verify the candidate:

```bash
git rev-parse HEAD
scripts/verify-app.sh dist/LocalModelDesk.app
codesign -dvvv dist/LocalModelDesk.app 2>&1
spctl --assess --type execute --verbose=4 dist/LocalModelDesk.app
```

Expected: verification succeeds; the bundle identifier is
`com.aa.localmodeldesk`; the displayed signing identity is the intended Developer
ID Application identity with hardened runtime. The app is deliberately not
notarized, so an initial Gatekeeper warning is expected and must be documented,
not treated as a reason to bypass the test.

Before installing, capture a baseline for the configured model directory and
user data directory. Do not copy, move, purge, or otherwise mutate real model
weights during this gate.

```bash
MODEL_ROOT="$HOME/Library/Application Support/LocalModelDesk/models"
DATA_ROOT="$HOME/Library/Application Support/LocalModelDesk"
test -d "$MODEL_ROOT" && du -sh "$MODEL_ROOT" || true
test -d "$DATA_ROOT" && du -sh "$DATA_ROOT" || true
```

## 1. Install to /Applications

Run the production install path (authorization may be requested by the host):

```bash
scripts/install-app.sh --app dist/LocalModelDesk.app --dest /Applications
test -d /Applications/LocalModelDesk.app
/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' \
  /Applications/LocalModelDesk.app/Contents/Info.plist
```

Expected: the installer verifies before using `ditto`, reports
`installed: /Applications/LocalModelDesk.app`, and the final command prints
`com.aa.localmodeldesk`. Capture Finder evidence that the installed app has its
expected icon.

## 2. Gatekeeper and first-run adoption

Open `/Applications/LocalModelDesk.app` by double-clicking. If Gatekeeper blocks
the unnotarized Developer ID app, use Finder's contextual **Open** action and
confirm the system dialog. Capture the dialog and the successful launch; then
quit and reopen normally once to confirm the approval persists.

On the first-run screen, choose an existing model root only with the non-copying
adoption option (point to the existing directory). Confirm the resource UI
recognizes its `llms`, `minimax-h3`, and/or `minimax-music3` contents as
applicable. Record before/after `du -sh` for that root and confirm no 339G
download or duplicate copy began. The selected path must match the persisted
configuration:

```bash
plutil -p "$HOME/Library/Application Support/LocalModelDesk/config.json" 2>/dev/null \
  || cat "$HOME/Library/Application Support/LocalModelDesk/config.json"
du -sh "$MODEL_ROOT"
```

Expected: first run completes, the resource panel reflects the selected location,
and model bytes are unchanged apart from metadata outside the model root.

## 3. App lifetime, menu bar, and window reopening

After first-run completion, confirm all of the following and capture screenshots:

1. The main desk window and Dock icon appear, and a LocalModelDesk status item
   appears in the menu bar.
2. The embedded desk service starts; record the listening state without sending
   a model request:

   ```bash
   lsof -nP -iTCP:8766 -iTCP:8767 -iTCP:8770 -sTCP:LISTEN
   ```

3. Close the main window with its red close control. Expected: the process does
   not quit, the menu-bar item remains, and no model download or generation is
   started merely by closing the window.
4. Use the menu-bar item to reopen the main window. Expected: the original desk
   shell returns and the embedded service remains available.

## 4. Quit containment

Choose **Quit** from the LocalModelDesk menu-bar menu (do not merely close the
window). Wait briefly for orderly shutdown, then run:

```bash
lsof -nP -iTCP:8766 -iTCP:8767 -iTCP:8770 -sTCP:LISTEN
```

Expected: the command has no output; the Dock and menu-bar item disappear; no
embedded desk or mlx-lm listener remains. Record any remaining PID as a defect
instead of killing it silently, so the owner can investigate the failed cleanup.

## 5. Default uninstall: retain user data and all models

With the app quit, run the production uninstall without `--purge-data`:

```bash
scripts/uninstall-app.sh
test ! -e /Applications/LocalModelDesk.app
launchctl print "gui/$UID/com.aa.localmodeldesk"
```

Expected: the app bundle is absent and the final `launchctl` command reports that
the service is not found. Its nonzero status is expected evidence, so record it.
Confirm the data and model roots remain present and compare their recorded size
to the pre-uninstall baseline:

```bash
test -d "$DATA_ROOT"
test -d "$MODEL_ROOT"
du -sh "$DATA_ROOT" "$MODEL_ROOT"
```

## 6. Optional purge safety check — disposable fixture only

Never pass a real data root or model root to this check. Create a disposable
fixture under a fresh temporary directory, place sentinel files in `models/`,
`llms/`, `minimax-h3/`, and `minimax-music3/`, and point the uninstall script at
that fixture with `--purge-data`. Confirm ordinary fixture data is removed while
all model sentinels remain. Separately use a deliberately malformed `config.json`
and confirm the command fails without deleting anything.

Example fixture setup (adjust the temporary path only):

```bash
FIXTURE="$(mktemp -d /tmp/localmodeldesk-purge.XXXXXX)"
mkdir -p "$FIXTURE/data/models" "$FIXTURE/data/llms" "$FIXTURE/data/minimax-h3" "$FIXTURE/data/minimax-music3"
touch "$FIXTURE/data/models/keep" "$FIXTURE/data/llms/keep" \
  "$FIXTURE/data/minimax-h3/keep" "$FIXTURE/data/minimax-music3/keep" "$FIXTURE/data/remove-me"
printf '{"models_root":"%s"}\n' "$FIXTURE/data/models" > "$FIXTURE/data/config.json"
scripts/uninstall-app.sh --app-path "$FIXTURE/missing.app" --data-root "$FIXTURE/data" \
  --launch-agents-dir "$FIXTURE/LaunchAgents" --purge-data
test -e "$FIXTURE/data/models/keep"
test -e "$FIXTURE/data/llms/keep"
test -e "$FIXTURE/data/minimax-h3/keep"
test -e "$FIXTURE/data/minimax-music3/keep"
test ! -e "$FIXTURE/data/remove-me"
```

Remove only this known fixture after recording its outcome. If any required
observation differs from this runbook, file a packaging/shell defect and do not
write `VERDICT: PASS`.
