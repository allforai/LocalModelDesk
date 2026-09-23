import * as api from "../api.js";
import { createJobView } from "../widgets/jobview.js";
import { confirmDialog } from "../widgets/confirm.js";

export function createImagePane(root, ctx = {}) {
  const fields = ["prompt", "width", "height", "steps", "seed"];
  const els = Object.fromEntries([...fields, "start", "error", "hint", "model"].map(
    (name) => [name, root.querySelector(`[data-image-${name}]`)]));
  const jobView = createJobView(root, { mediaTag: "img", kind: "image" });
  let pending = false, allowed = false, busyReason = "正在检查服务状态…";
  let modelReason = "正在检查模型…", runtimeReason = "正在检查 MLX 运行环境…";

  function updateAvailability() {
    const reason = pending ? "正在提交…" : !allowed ? busyReason : runtimeReason || modelReason;
    els.start.disabled = pending || !allowed || !!runtimeReason || !!modelReason;
    els.start.title = reason;
    els.hint.textContent = reason;
    els.model.textContent = modelReason || "模型文件完整 · 可离线生成";
  }
  function setModelStatus(status) {
    modelReason = status?.state === "present" ? "" : status?.reason || (
      status?.state === "partial" ? "模型不完整，请到「资源」页继续下载或校验" :
      status?.state === "missing" ? "尚未安装图片模型，请到「资源」页下载" : "暂时无法确认模型状态，请稍后重试");
    updateAvailability();
  }
  function setRuntimeStatus(capability) {
    runtimeReason = capability?.present ? "" : capability?.detail || "图片 MLX 运行环境不可用，请检查服务或应用安装";
    updateAvailability();
  }
  function setHeavyAllowed(value, reason = "") {
    allowed = value; busyReason = reason; updateAvailability();
  }
  function readParams() {
    const params = { prompt: els.prompt.value };
    if (!params.prompt.trim()) throw new Error("请填写图片提示词");
    for (const name of fields.slice(1)) {
      const raw = els[name].value.trim();
      if (!raw || !Number.isInteger(Number(raw))) throw new Error("宽、高、步数和种子须为整数");
      params[name] = Number(raw);
    }
    if ([params.width, params.height].some((n) => n < 256 || n > 2048 || n % 16))
      throw new Error("宽高须为 256–2048 范围内的 16 的倍数");
    if (params.steps < 1 || params.steps > 100) throw new Error("步数须为 1–100 的整数");
    if (params.seed < 0 || params.seed > 4294967295) throw new Error("种子须为 0–4294967295 的整数");
    return params;
  }
  async function submit(params) {
    try { return await api.startImageJob(params); }
    catch (error) {
      if (error.code !== "insufficient_memory") throw error;
      const ok = await (ctx.confirm ?? confirmDialog)(root.ownerDocument, {
        title: "内存可能不足", message: error.message, confirmLabel: "仍要生成",
      });
      return ok ? api.startImageJob({ ...params, force: true }) : null;
    }
  }
  els.start.addEventListener("click", async () => {
    if (els.start.disabled) return;
    els.error.textContent = "";
    pending = true; updateAvailability();
    try {
      const job = await submit(readParams());
      if (!job) return;
      jobView.start(job);
      if (job.status === "running") { allowed = false; busyReason = "图片生成中"; }
      ctx.onStarted?.(job);
    } catch (error) { els.error.textContent = error.message; }
    finally { pending = false; updateAvailability(); }
  });
  function fill(values) {
    for (const name of fields) if (values[name] != null) els[name].value = String(values[name]);
  }
  updateAvailability();
  return { fill, jobView, setHeavyAllowed, setModelStatus, setRuntimeStatus };
}
