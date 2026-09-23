// 从 GitHub 装一个 skill 的确认弹层（R-skill-11）。
//
// skill 就是指令：装别人写的 skill，等于让一个陌生人的指令去驱动用户的模型。
// 所以这里的规矩比 confirm.js 严：
//   1. 装之前用户必须看到完整的 SKILL.md 正文——不是 description，不是摘要，
//      不是前 N 行，是后端 preview 接口吐回来的整段 body，可以滚动看完。这是
//      唯一能防住「仓库名字和描述说一套、正文做另一套」的办法。
//   2. 用户确认之前什么都不落盘：装（install）是分开的、显式的第二步。
//   3. 取消（含 Esc、点遮罩）要调用 discard，不能把暂存干晾着——虽然后端启动时
//      会扫一遍孤儿暂存，但用户显式取消这个动作本身该把暂存收干净，不指望
//      「反正启动会扫」。
//   4. 装完不等于开：装完之后只落盘，芯片栏里仍然是关的，用户得自己去点。
//      这句话必须在界面上说出来，不然用户以为装了就在用，发现没生效会以为
//      装失败了。
//
// 跟 confirm.js 共用同一套遮罩/弹层/Esc/点遮罩关闭骨架，但内容形状完全不一样
// （两段式：先填 URL，预览成功后原地换成正文+附件+确认），所以另起一个函数，
// 不往 confirmDialog 的参数表里硬塞第二种用法。
//
// 参数 api 直接传真实的 api.js 模块（或测试里的等价物），用它的
// previewSkill / installSkill / discardSkill 三个函数——命名跟 api.js 里
// 导出的名字完全一致，调用方不用再包一层转换。
export function skillInstallDialog(doc, api) {
  return new Promise((resolve) => {
    const overlay = doc.createElement("div"); overlay.className = "overlay";
    const box = doc.createElement("div"); box.className = "dialog dialog-wide";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "从 GitHub 安装 skill");

    // 只有走完一次成功的 preview 之后才有值——取消时按它是否非空决定要不要
    // discard：URL 输入阶段用户直接取消，后端根本还没建暂存目录，没什么可扔。
    let stagingId = null;
    let settled = false;

    const settle = (value) => {
      if (settled) return;
      settled = true;
      doc.removeEventListener?.("keydown", onKey);
      overlay.remove();
      resolve(value);
    };

    // 取消路径统一走这里：有暂存就扔，没有就直接关。discard 失败不挡住关闭——
    // 暂存目录反正启动时会被后端扫掉，UI 这层没有更好的办法，也不该为了一次
    // 清理失败把「取消」这个动作本身卡住。
    const cancel = async () => {
      if (settled) return;
      const pending = stagingId;
      stagingId = null;
      settle(null);
      if (pending) { try { await api.discardSkill(pending); } catch { /* 启动扫描兜底 */ } }
    };

    const onKey = (event) => { if (event.key === "Escape") cancel(); };
    doc.addEventListener?.("keydown", onKey);
    overlay.addEventListener("click", (event) => { if (event.target === overlay) cancel(); });

    // 清空复用同一个 box：真实 DOM 里 textContent = "" 本身就会移除所有子节点，
    // 不能直接赋值 box.children（真实 DOM 下这是只读属性，只有测试用的假 DOM
    // 才允许直接赋值）。
    const clearBox = () => { box.textContent = ""; };

    function renderUrlStep(errorText = "", prefillUrl = "") {
      clearBox();
      const h = doc.createElement("h3"); h.textContent = "从 GitHub 安装 skill";
      const p = doc.createElement("p"); p.textContent = "填仓库地址，先看完整篇 SKILL.md 再决定装不装。";
      const input = doc.createElement("input");
      input.type = "text";
      input.placeholder = "https://github.com/owner/repo";
      input.value = prefillUrl;
      (input.dataset ??= {}).skillInstallUrl = "1";
      const err = doc.createElement("p"); err.className = "inline-error";
      (err.dataset ??= {}).skillInstallError = "1";
      err.textContent = errorText;
      const row = doc.createElement("div"); row.className = "dialog-actions";
      const cancelBtn = doc.createElement("button"); cancelBtn.textContent = "取消";
      (cancelBtn.dataset ??= {}).skillInstallCancel = "1";
      const nextBtn = doc.createElement("button"); nextBtn.className = "btn-primary"; nextBtn.textContent = "预览";
      (nextBtn.dataset ??= {}).skillInstallSubmit = "1";
      cancelBtn.addEventListener("click", cancel);
      nextBtn.addEventListener("click", async () => {
        const url = (input.value ?? "").trim();
        if (!url) { renderUrlStep("请填一个地址", url); return; }
        nextBtn.disabled = true;
        try {
          const preview = await api.previewSkill(url);
          if (settled) return; // 用户在请求飞的时候点了取消/Esc
          stagingId = preview.staging_id;
          renderPreviewStep(preview);
        } catch (error) {
          // 后端这条消息是特地写来告诉用户具体错在哪、该怎么改的——原样显示，
          // 不换成一句通用的「安装失败」（R-skill-11 明确写了这条）。
          if (!settled) renderUrlStep(error.message ?? String(error), url);
        }
      });
      row.append(cancelBtn, nextBtn);
      box.append(h, p, input, err, row);
      input.focus?.();
    }

    function renderPreviewStep(preview) {
      clearBox();
      const h = doc.createElement("h3"); h.textContent = preview.name;
      const desc = doc.createElement("p"); desc.textContent = preview.description;
      // 完整正文，可滚动——不截断、不摘要（R-skill-11 第 1 条）。
      const bodyBox = doc.createElement("pre");
      bodyBox.className = "skill-install-body";
      (bodyBox.dataset ??= {}).skillInstallBody = "1";
      bodyBox.textContent = preview.body ?? "";
      const attachments = doc.createElement("p");
      (attachments.dataset ??= {}).skillInstallAttachments = "1";
      attachments.textContent = (preview.attachments ?? []).length
        ? `附件：${preview.attachments.join("、")}`
        : "没有附件。";
      // 装了不等于开——用户看完这句才点确认（R-skill-11 第 3 条：说清楚，不然
      // 用户会以为装失败了）。
      const notice = doc.createElement("p"); notice.className = "hint";
      (notice.dataset ??= {}).skillInstallOffNotice = "1";
      notice.textContent = "确认后只会落盘，芯片栏里仍是关的——要用得自己去那边点开，不会自动启用。";
      const err = doc.createElement("p"); err.className = "inline-error";
      (err.dataset ??= {}).skillInstallError = "1";
      const row = doc.createElement("div"); row.className = "dialog-actions";
      const cancelBtn = doc.createElement("button"); cancelBtn.textContent = "取消";
      (cancelBtn.dataset ??= {}).skillInstallCancel = "1";
      const okBtn = doc.createElement("button"); okBtn.className = "btn-primary"; okBtn.textContent = "确认安装";
      (okBtn.dataset ??= {}).skillInstallConfirm = "1";
      cancelBtn.addEventListener("click", cancel);
      okBtn.addEventListener("click", async () => {
        okBtn.disabled = true;
        try {
          const result = await api.installSkill(stagingId);
          stagingId = null; // 已经落盘：万一 settle 之后还有取消路径被触发，不用再 discard 一个已经不存在的暂存
          settle(result);
        } catch (error) {
          if (!settled) { err.textContent = error.message ?? String(error); okBtn.disabled = false; }
        }
      });
      row.append(cancelBtn, okBtn);
      box.append(h, desc, bodyBox, attachments, notice, err, row);
      cancelBtn.focus?.();
    }

    renderUrlStep();
    overlay.append(box);
    doc.body.append(overlay);
  });
}
