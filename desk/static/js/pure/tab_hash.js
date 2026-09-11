// Pure hash <-> tab mapping so the shell's error page (G29) can restore the tab that was
// active before it replaced the desk shell, and a reload keeps the current tab (G37).
const TABS = new Set(["chat", "video", "music", "resources", "library"]);

export function tabFromHash(hash) {
  const m = /^#tab=([a-z]+)$/.exec(hash ?? "");
  return m && TABS.has(m[1]) ? m[1] : "chat";
}

// Decides which tab a freshly opened window should land on (cross-exam J6: the native
// shell could carry over a stale/empty hash from the previous run and land on whatever
// tab happened to be open last, e.g. "music", instead of a deterministic start). Any
// hash outside the whitelist — including "", "#", or garbage — falls back to "chat".
// Reuses the same whitelist/fallback rule as tabFromHash; kept as a separate named
// export because the two callers answer different questions (restoring the tab across
// a reload vs. deciding the tab for a brand-new launch), even though the rule is
// currently identical.
export function initialTab(hash) {
  return tabFromHash(hash);
}
