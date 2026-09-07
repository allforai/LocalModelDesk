// Small, dependency-free outline icon set. Icons are decorative when paired with text.
const NS = "http://www.w3.org/2000/svg";

const PATHS = {
  settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V21h-3v-.78a1.7 1.7 0 0 0-1.03-1.56A1.7 1.7 0 0 0 8.8 19l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 15a1.7 1.7 0 0 0-1.56-1.03H4v-3h1.44A1.7 1.7 0 0 0 7 9.94a1.7 1.7 0 0 0-.34-1.88L6.6 8l2.12-2.12.06.06a1.7 1.7 0 0 0 1.88.34A1.7 1.7 0 0 0 11.7 4.7V4h3v.7a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06L19.8 8l-.06.06a1.7 1.7 0 0 0-.34 1.88 1.7 1.7 0 0 0 1.56 1.03H22v3h-1.04A1.7 1.7 0 0 0 19.4 15Z",
  chat: "M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z",
  video: "M3 5h13a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Zm15 5 5-3v10l-5-3Z",
  music: "M9 18V5l11-2v13M9 9l11-2M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm11-2a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  drive: "M4 5h16l2 7H2l2-7Zm-2 7v5a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5M6 16h.01M10 16h.01",
  library: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13Zm0 0V6.5M8 8h8",
  plus: "M12 5v14M5 12h14",
  power: "M12 2v10M5.6 5.6a9 9 0 1 0 12.8 0",
  send: "m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13",
  sparkles: "m12 3-1.4 3.6L7 8l3.6 1.4L12 13l1.4-3.6L17 8l-3.6-1.4L12 3ZM5 14l-.9 2.1L2 17l2.1.9L5 20l.9-2.1L8 17l-2.1-.9L5 14Zm14-1-1.1 2.9L15 17l2.9 1.1L19 21l1.1-2.9L23 17l-2.9-1.1L19 13Z",
  refresh: "M20 6v5h-5M4 18v-5h5M19 11a7 7 0 0 0-12-4L4 11m1 2a7 7 0 0 0 12 4l3-4",
  x: "M18 6 6 18M6 6l12 12",
  copy: "M8 8h11a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2Zm8 0V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h1",
  folder: "M3 5h7l2 2h9v12H3V5Z",
  import: "M12 3v12m-5-5 5 5 5-5M4 19h16",
  pencil: "m4 20 4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20Zm10-12 3 3",
  trash: "M3 6h18M8 6V3h8v3m3 0-1 15H6L5 6m4 4v7m6-7v7",
  download: "M12 3v12m-5-5 5 5 5-5M5 21h14",
  pause: "M8 5v14M16 5v14",
  play: "m8 5 11 7-11 7V5Z",
  sliders: "M4 7h10m4 0h2M4 17h2m4 0h10M14 4v6M6 14v6",
  memory: "M7 2v3m5-3v3m5-3v3M7 19v3m5-3v3m5-3v3M2 7h3m-3 5h3m-3 5h3m14-10h3m-3 5h3m-3 5h3M5 5h14v14H5V5Zm4 4h6v6H9V9Z",
  brain: "M9.5 4.5A3 3 0 0 0 4 6a3 3 0 0 0-1 5.8A3.5 3.5 0 0 0 6 18h3.5V4.5Zm5 0A3 3 0 0 1 20 6a3 3 0 0 1 1 5.8A3.5 3.5 0 0 1 18 18h-3.5V4.5ZM9.5 9H7m7.5 3H18",
  activity: "M3 12h4l2-6 4 12 2-6h6",
  check: "m5 12 4 4L19 6",
};

export function iconNode(doc, name) {
  if (!doc.createElementNS) {
    const fallback = doc.createElement("span");
    fallback.className = `icon icon-${name}`;
    return fallback;
  }
  const svg = doc.createElementNS(NS, "svg");
  const path = doc.createElementNS(NS, "path");
  svg.setAttribute("class", "icon");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  path.setAttribute("d", PATHS[name] ?? PATHS.activity);
  svg.append(path);
  return svg;
}

export function addIcon(control, name, doc = control?.ownerDocument ?? globalThis.document) {
  if (!control || control.querySelector?.(".icon")) return control;
  if (!doc) return control;
  control.append(iconNode(doc, name));
  control.classList?.add?.("with-icon");
  return control;
}

export function setIcon(control, name, doc = control?.ownerDocument ?? globalThis.document) {
  if (!control || !doc) return control;
  const fresh = iconNode(doc, name);
  fresh.className = fresh.className ? fresh.className : "icon";
  if (fresh.setAttribute) fresh.setAttribute("class", `icon icon-${name}`); else fresh.className = `icon icon-${name}`;
  const existing = control.children ? [...control.children].find((child) => String(child.className ?? "").includes("icon")) : control.querySelector?.(".icon");
  if (existing && control.replaceChild) control.replaceChild(fresh, existing);
  else if (existing && control.children) control.children[control.children.indexOf(existing)] = fresh;
  else { control.append(fresh); control.classList?.add?.("with-icon"); }
  return control;
}

export function hydrateIcons(root = document) {
  for (const control of root.querySelectorAll("[data-icon-name]")) {
    addIcon(control, control.dataset.iconName);
  }
}
