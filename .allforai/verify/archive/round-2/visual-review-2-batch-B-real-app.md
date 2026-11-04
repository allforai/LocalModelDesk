# Reviewer 2 — batch-B-real-app

**Status: passed_with_warnings**

已逐张用图像查看工具打开22/22张截图。0 blocker、0 major、1 minor、1 note。主要会话布局、真实图片、双动作、运行/取消/失败及删除后素材库预览符合可见视觉要求；删除确认取消按钮缺少明确焦点反馈。

Reviewer: reviewer-2 · Backend: codex exec · Model: GPT-6

## 方法与范围

已阅读指定batch及视觉标准，逐张用view_image打开全部22张PNG；未读取证据JSON、其他review报告、reconciliation/closure-audit或archive。结论来自截图像素。未以静态截图声称验证aria属性、naturalWidth、精确scrollWidth或真实键盘焦点。图片页均未见主流程“种子”、横向溢出、破图、空白图片框或视频/音乐面板混入。素材库按其专属状态及D-50a审查，不要求图片页会话布局。

## Blockers

无。

## Majors

无。

## Minors

### R2-batch-B-real-app-001 — focus_indicator_not_visible

- Severity: minor
- Criteria: visual-acceptance-criteria.md § delete-confirm：取消获得焦点
- Observation: 两个确认框中取消按钮只有普通暗色边框，没有可辨识的焦点环；背景会话项仍可见蓝色双轮廓。截图不能证明实际DOM焦点落在哪里，但没有呈现取消为默认焦点的视觉反馈。
- Repair suggestion: 核实打开弹层时将焦点移到取消按钮，并提供清晰的焦点样式；补拍可辨识取消焦点的两个视口。
- Screenshots:
  - `.allforai/verify/evidence/real/real-delete-confirm-wide.png`
  - `.allforai/verify/evidence/real/real-delete-confirm-narrow.png`

## Notes

### R2-batch-B-real-app-002 — static_evidence_limit

- Severity: note
- Criteria: visual-acceptance-criteria.md § attempt-failed；batch-B-real-app.md AC-3/global
- Observation: 失败详情保持折叠，因此无法目视确认内部code/message及日志尾部。重启后wide显示第4次灯塔图片；narrow只显示末尾取消和失败卡片，不能独立证明屏外图片恢复。可见部分没有破图或错误状态。
- Repair suggestion: 如需对隐藏内容作独立视觉证明，补充展开详情截图及重启后滚到完成图片的narrow截图；本项不判定应用缺陷。
- Screenshots:
  - `.allforai/verify/evidence/real/real-attempt-failed-wide.png`
  - `.allforai/verify/evidence/real/real-attempt-failed-narrow.png`
  - `.allforai/verify/evidence/real/real-after-restart-wide.png`
  - `.allforai/verify/evidence/real/real-after-restart-narrow.png`

时间线上方/下方部分卡片处于滚动区域外属于截图声明的滚动位置。top与末尾截图合并可见三次尝试顺序、全部缩略图及第3次完整展开区；未将滚动区域的正常裁边当成元素互相遮挡。WKWebView不绘制页面滚动条按batch说明处理，未据此推断DOM尺寸。

## 每张截图检查记录

下列pass仅指该截图可见范围；delete-confirm的fail对应minor视觉反馈问题，不代表blocker或major。

| Screenshot | State | Viewport | Verdict | Observation |
|---|---|---|---|---|
| `.allforai/verify/evidence/real/real-running-wide.png` | real-running | wide | pass | running：生成中卡片、进度条、取消、折叠日志、会话生成中标记及禁用生成按钮均可见；无图片占位或完成动作。 |
| `.allforai/verify/evidence/real/real-running-narrow.png` | real-running | narrow | pass | running：生成中卡片、进度条、取消、折叠日志、会话生成中标记及禁用生成按钮均可见；无图片占位或完成动作。 |
| `.allforai/verify/evidence/real/real-refine-prefill-wide.png` | real-refine-prefill | wide | pass | refine-prefill：第2次提示词与有光标的输入内容一致，沿用第2次构图提示及×可见；高级参数折叠，无新running卡片。 |
| `.allforai/verify/evidence/real/real-refine-prefill-narrow.png` | real-refine-prefill | narrow | pass | refine-prefill：第2次提示词与有光标的输入内容一致，沿用第2次构图提示及×可见；高级参数折叠，无新running卡片。 |
| `.allforai/verify/evidence/real/real-timeline-three-rounds-wide.png` | real-timeline-three-rounds | wide | pass | timeline-three-rounds：末尾第3次展开，真实灯塔大图、完整提示词、折叠高级参数和两个动作完整显示。第1/2次由同视口top截图补充检查。 |
| `.allforai/verify/evidence/real/real-timeline-three-rounds-narrow.png` | real-timeline-three-rounds | narrow | pass | timeline-three-rounds：末尾第3次展开，真实灯塔大图、完整提示词、折叠高级参数和两个动作完整显示。第1/2次由同视口top截图补充检查。 |
| `.allforai/verify/evidence/real/real-timeline-three-rounds-top-wide.png` | real-timeline-three-rounds-top | wide | pass | timeline-three-rounds：第1、2、3次顺序正确，三张真实缩略图、摘要、512×512及6步可见；第3次下部在滚动区域外，由同视口末尾截图补充检查。 |
| `.allforai/verify/evidence/real/real-timeline-three-rounds-top-narrow.png` | real-timeline-three-rounds-top | narrow | pass | timeline-three-rounds：第1、2、3次顺序正确，三张真实缩略图、摘要、512×512及6步可见；第3次下部在滚动区域外，由同视口末尾截图补充检查。 |
| `.allforai/verify/evidence/real/real-attempt-selected-actions-wide.png` | real-attempt-selected-actions | wide | pass | attempt-selected-actions：第1次展开，灯塔大图完整且明显低于60vh，两动作并排完整可见；未见第二张展开卡片。 |
| `.allforai/verify/evidence/real/real-attempt-selected-actions-narrow.png` | real-attempt-selected-actions | narrow | pass | attempt-selected-actions：第1次展开，灯塔大图完整且明显低于60vh，两动作并排完整可见；未见第二张展开卡片。 |
| `.allforai/verify/evidence/real/real-attempt-cancelled-wide.png` | real-attempt-cancelled | wide | pass | attempt-cancelled：第5次已取消、手动停止说明、灰色×图标块和两个动作均可见，无空图片框或生成中状态。 |
| `.allforai/verify/evidence/real/real-attempt-cancelled-narrow.png` | real-attempt-cancelled | narrow | pass | attempt-cancelled：第5次已取消、手动停止说明、灰色×图标块和两个动作均可见，无空图片框或生成中状态。 |
| `.allforai/verify/evidence/real/real-attempt-failed-wide.png` | real-attempt-failed | wide | pass | attempt-failed：第6次失败、红色×图标块、生成程序异常退出原因、折叠详情和两个动作均可见。折叠详情内的code/message和日志内容无法由本截图确认。 |
| `.allforai/verify/evidence/real/real-attempt-failed-narrow.png` | real-attempt-failed | narrow | pass | attempt-failed：第6次失败、红色×图标块、生成程序异常退出原因、折叠详情和两个动作均可见。折叠详情内的code/message和日志内容无法由本截图确认。 |
| `.allforai/verify/evidence/real/real-after-restart-wide.png` | real-after-restart | wide | pass | AC-3/global：两个会话仍在，灯塔会话高亮且标示6次生成，第5次取消和第6次失败仍显示；布局及动作完整。 wide还能看到第4次真实灯塔缩略图。 |
| `.allforai/verify/evidence/real/real-after-restart-narrow.png` | real-after-restart | narrow | pass | AC-3/global：两个会话仍在，灯塔会话高亮且标示6次生成，第5次取消和第6次失败仍显示；布局及动作完整。 narrow停在末尾，第4次图片在可见范围外，不能单凭此图确认图片恢复；wide提供了可见图片证据。 |
| `.allforai/verify/evidence/real/real-delete-confirm-wide.png` | real-delete-confirm | wide | fail | delete-confirm：标题、完整保留素材库图片的文案、取消和红色删除按钮可见；取消未呈现可辨识焦点，见001。 |
| `.allforai/verify/evidence/real/real-delete-confirm-narrow.png` | real-delete-confirm | narrow | fail | delete-confirm：标题、完整保留素材库图片的文案、取消和红色删除按钮可见；取消未呈现可辨识焦点，见001。 |
| `.allforai/verify/evidence/real/real-after-delete-wide.png` | real-after-delete | wide | pass | library-after-delete图片页部分：竹林会话已从左栏消失，仅剩高亮灯塔会话及既有尝试，输入区正常。 |
| `.allforai/verify/evidence/real/real-after-delete-narrow.png` | real-after-delete | narrow | pass | library-after-delete图片页部分：竹林会话已从左栏消失，仅剩高亮灯塔会话及既有尝试，输入区正常。 |
| `.allforai/verify/evidence/real/real-library-after-delete-wide.png` | real-library-after-delete | wide | pass | library-after-delete：竹林小径真实预览与同名完成条目可见，操作文字完整；素材库种子元数据按D-50a豁免。 |
| `.allforai/verify/evidence/real/real-library-after-delete-narrow.png` | real-library-after-delete | narrow | pass | library-after-delete：竹林小径真实预览与同名完成条目可见，操作文字完整；素材库种子元数据按D-50a豁免。 |
