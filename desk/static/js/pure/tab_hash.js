// Pure hash <-> tab mapping so the shell's error page (G29) can restore the tab that was
// active before it replaced the desk shell, and a reload keeps the current tab (G37).
const TABS = new Set(["chat", "video", "music", "resources", "library"]);

export function tabFromHash(hash) {
  const m = /^#tab=([a-z]+)$/.exec(hash ?? "");
  return m && TABS.has(m[1]) ? m[1] : "chat";
}
