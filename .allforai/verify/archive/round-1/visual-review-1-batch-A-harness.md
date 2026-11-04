# Visual review 1 — batch-A-harness (image sessions, harness screenshots)

- Reviewer: reviewer-1 · claude -p fresh context · claude-opus-5-5
- Standard: `.allforai/visual-qa/visual-acceptance-criteria.md` (global rules + per-state), AC-7
- I opened all 48 screenshots listed in the batch as images. I did not pass any screenshot based only on its `.json` record.
- Declared mock layers, not counted as defects: gradient PNG instead of real Qwen output, which is why the images look landscape while the meta says 1024×1024; fixed clock; 500 route for `session-list-load-failed`.

**Status: failed_visual_review** — no blockers, 3 majors, 6 minors, 5 notes.

---

## Blockers

None. No horizontal scroll, broken-image icon, blank image frame, clipped button text, overlapping pieces, or foreign pane content on the image page. 「种子」 does not appear anywhere on the image page.

## Majors

### R1-001 — Narrow: the two action buttons on the last (open) card are hidden below the composer
- Screenshots: `.allforai/verify/screens/timeline-three-rounds-narrow.png`, `.allforai/verify/screens/verify-four-attempts-narrow.png`, `.allforai/verify/screens/verify-switch-back-narrow.png`
- Criteria: `timeline-three-rounds` must-show「最后一次（第 3 次）展开：大图、完整提示词、折叠的「高级参数」、「在这张基础上改」「换个构图」两个按钮」; must-not-show「按钮文字被裁切」; AC-7「两个动作按钮，无遮挡、截断」; D-78.
- Observation: At 900×700 the timeline does not scroll far enough down. The open last card ends partway down.
  - In timeline-three-rounds-narrow, the「高级参数」 row is cut in half at the timeline's bottom edge and neither action button can be seen.
  - In verify-switch-back-narrow, only the top ~2px of the button borders show above the composer.
  - verify-four-attempts-narrow shows the same thing.
  - At wide width the same screens are scrolled so both buttons are fully visible. The timeline scrollbar at narrow width shows more content below.
- Repair suggestion: After opening a session, finishing a generation, or re-rendering, scroll the timeline so the whole open card is visible, down to its action row (for example `scrollIntoView({block:'end'})` on the card's actions row, or `scrollTop = scrollHeight` when the last card is the open one). Re-take the narrow shots.

### R1-002 — `running-other-session` has the wrong setup: session B has no attempts
- Screenshots: `.allforai/verify/screens/running-other-session-wide.png`, `.allforai/verify/screens/running-other-session-narrow.png`
- Criteria: `running-other-session` setup「会话 B 至少 1 次完成尝试」; must-show「会话 B 高亮，时间线是 B 的尝试」「「生成图片」与「换个构图」禁用，「在这张基础上改」可用」.
- Observation: The highlighted session B is「新会话 · 0 次生成」, and its timeline shows the empty state「还没有图片」. With no attempt card, neither required button state can be seen: 「换个构图」 disabled and 「在这张基础上改」 enabled. Nothing proves that an open B card shows no running indicator from A.
  - These parts are correct: 「甲会话的…」 has the 生成中 badge, the status line reads「「甲会话的灯塔」正在生成图片」 with a 「回到该会话」 button, and 「生成图片」 is disabled.
- Repair suggestion: Seed session B with at least one done attempt, open it while A is running, and re-capture both widths.

### R1-003 — `model-missing` status line shows the runtime reason, not the model reason
- Screenshots: `.allforai/verify/screens/model-missing-wide.png`, `.allforai/verify/screens/model-missing-narrow.png`
- Criteria: `model-missing` must-show「头部模型状态与状态行「尚未安装图片模型，请到「资源」页下载」」.
- Observation: The header subtitle correctly reads「尚未安装图片模型，请到「资源」页下载」. But the status line under the composer reads「图片 MLX 运行环境缺失，请安装 .venv-image 或使用包含图片运行时的应用」. That is exactly the `runtime-unavailable` text. So either the fixture also marks the runtime as missing, or the status line puts the runtime reason ahead of the model reason. 「生成图片」 is disabled, which is correct.
- Repair suggestion: Make the `model-missing` fixture keep `image_runtime.present=true` so only the model is missing. If both are missing, decide which reason comes first: tell the user about the model first, since that is what they can fix on the 资源 page. Re-capture.

## Minors

### R1-004 — Session titles in the list are cut much shorter than the space allows
- Screenshots: `running-wide.png` (「会失败的…」 for「会失败的一张」), `empty-session-wide.png` / `timeline-three-rounds-*.png` (「一只橘猫坐在窗边…」), `verify-four-attempts-*.png` (「清晨的港口， 渔船…」), `delete-confirm-running-*.png` (「删除时还…」)
- Criteria: global rule — an ellipsis is allowed on session titles; `timeline-three-rounds`「会话标题是第 1 次的提示词（≤24 字 + …）」.
- Observation: Titles are cut at about 4–9 characters in a ~240px list item that has room for about 14. Even the 6-character「会失败的一张」 is cut when the 生成中 badge is shown. The title box seems to hold back space for the hover 改名/删除 icons even when they are hidden. A space also shows after the full-width comma in「清晨的港口， 渔船…」.
- Repair suggestion: Let the title grow to fill the row (`flex:1; min-width:0`) and only hold back room for the action icons while they are visible (hover or focus). Check whether the extra space comes from the title text or from CSS.

### R1-005 — The large image in the open card renders at thumbnail size
- Screenshots: `timeline-three-rounds-wide.png`, `attempt-selected-actions-*.png`, `refine-prefill-*.png`, `busy-other-media-*.png`, `rename-*.png`, `verify-*.png`
- Criteria: `timeline-three-rounds` must-show「大图」; `attempt-selected-actions`「大图完整显示（不超过 60vh、不被裁切）」; D-74.
- Observation: The 「大图」 in the open card is about 96×64, the same size as the thumbnail right above it, so it looks like a duplicate thumbnail. It is fully visible and not cropped, so the letter of the rule is met. It may just be the small mock PNG shown at its natural size, but the harness cannot prove the large-image layout.
- Repair suggestion: Size the open-card image to the timeline column (`width:100%; max-height:60vh; object-fit:contain`) so it does not depend on the image's natural size. Or have the mock write a PNG at the declared size. Batch B must confirm that a real 1024×1024 image renders large.

### R1-006 — Cancelled card has the 「已取消」 badge but no explanation line
- Screenshots: `attempt-cancelled-wide.png`, `attempt-cancelled-narrow.png`, `verify-failed-and-cancelled-*.png`
- Criteria: `attempt-cancelled` must-show「卡片带「已取消」标记与说明」; design line 81「已取消：这次生成被手动停止」.
- Observation: The failed and interrupted cards show a reason line under the meta, such as「生成程序异常退出」 or「内存不足，生成被中止」. The cancelled card shows only the grey 「已取消」 badge. Design §7.5 lets the reason text be「已取消」, so this may be deliberate de-duplication. Still, the card is thinner than the other two.
- Repair suggestion: Add a muted line such as「这次生成被手动停止」 (design line 81), or state in the criteria that the badge counts as the explanation.

### R1-007 — Header media status says idle while an image is generating
- Screenshots: `running-wide.png`, `running-narrow.png`, `delete-confirm-running-*.png`
- Criteria: global consistency, AC-7 (no wrong state).
- Observation: The running card and 「正在生成这个会话里的第 N 次」 are shown. At the same time the header says「媒体：空闲 · 可开下一件重活」 (narrow:「可开工」) and 内存里：无. In `running-other-session` the header correctly reads「媒体：生成中 · 不可：媒体作业进行中」. The header may just not have been polled yet, but the screenshot contradicts itself.
- Repair suggestion: Refresh the header status right after a media job is submitted, or wait for the header to update before taking the running screenshots.

### R1-008 — Delete dialog: no visible focus on 「取消」
- Screenshots: `delete-confirm-wide.png`, `delete-confirm-narrow.png`, `delete-confirm-running-*.png`
- Criteria: `delete-confirm` must-show「「取消」获得焦点，「删除」为危险样式」.
- Observation: 「删除」 is red (danger) as required. 「取消」 has only its normal thin border, and no focus ring can be seen, so the screenshot cannot show where focus is.
- Repair suggestion: Give dialog buttons a clear `:focus-visible` ring, or trigger focus-visible by keyboard before capture.

### R1-009 — `library-after-delete` shows only half of its must-show items; preview touches the 刷新 button
- Screenshots: `library-after-delete-wide.png`, `library-after-delete-narrow.png`
- Criteria: `library-after-delete` must-show「图片页会话列表里已无该会话」「素材库列出该图片并能预览出真实图片」.
- Observation: Only the 素材库 page was captured. It lists 「将被删除分组的灯塔」 and previews the gradient image, which is correct. The image-page list without the deleted session is not in these shots, though `verify-after-delete-*` covers it. The preview image sits right under the 刷新 button with no gap.
- Repair suggestion: Point this criteria item to `verify-after-delete-*`. Add vertical spacing between 刷新 and the preview.

## Notes
- N-1: The 素材库 rows show「种子 4086044872」. That is the library pane, not the image-page main flow, so it is outside BR-7. Recorded for the record.
- N-2: `running-other-session`: session B's composer still holds A's prompt「甲会话的灯塔」. The draft is shared across sessions. That fits「草稿不应被改」 in `empty-session`, but users may find it confusing.
- N-3: `rename-*`: there is only one session in the list, so「其他会话项不变」 cannot be checked. The rename input fits inside the left column and has focus.
- N-4: `attempt-interrupted` / `attempt-file-missing`: the seeded attempt time is 15:00 and the others are 05:19. This comes from the fixed clock and fixture, not a UI defect.
- N-5: The 改名/删除 icons are hidden unless hovered in every normal session item. The corrupt item shows only the red delete icon, which is correct.

## Per-screenshot verdicts
| screenshot | verdict | notes |
|---|---|---|
| first-entry-auto-session-wide/narrow | pass | One highlighted 新会话, two-line empty state, 生成图片 enabled, 高级参数 folded |
| empty-session-wide/narrow | pass | New session on top and highlighted; draft kept; composer focused |
| running-wide/narrow | pass | Running card, progress bar, 取消, 日志, 生成中 badge, status line; see R1-004, R1-007 |
| running-other-session-wide/narrow | fail | R1-002 |
| timeline-three-rounds-wide | pass | 第1 (scrolled partly out) → 第2 → 第3, buttons visible; R1-005 |
| timeline-three-rounds-narrow | fail | R1-001 |
| attempt-selected-actions-wide/narrow | pass | Only 第1 open; buttons fully visible |
| refine-prefill-wide/narrow | pass | 「沿用第 2 次的构图 ×」, prompt prefilled, 高级参数 folded, no new card |
| attempt-failed-wide/narrow | pass | Red icon block, 失败 badge + reason, 详情 with code/log, buttons |
| attempt-cancelled-wide/narrow | pass | Grey icon block, 已取消 badge, buttons; R1-006 |
| attempt-interrupted-wide/narrow | pass | 「应用在生成途中关闭，这次没有完成」 + failure icon block |
| attempt-file-missing-wide/narrow | pass | image icon block, 图片文件已不在 + 可能已在访达中移动或删除, buttons |
| model-missing-wide/narrow | fail | R1-003 |
| runtime-unavailable-wide/narrow | pass | Runtime reason in status line, 生成图片 disabled |
| busy-other-media-wide/narrow | pass | 媒体作业进行中, 生成图片 + 换个构图 disabled, no 回到该会话 |
| rename-wide/narrow | pass | Inline input with focus, fits the column |
| delete-confirm-wide/narrow | pass | Correct title/body, red 删除; R1-008 |
| delete-confirm-running-wide/narrow | pass | Extra sentence present |
| library-after-delete-wide/narrow | pass | Image listed and previewed; R1-009 |
| session-list-load-failed-wide/narrow | pass | 「会话列表读不出来：磁盘读不出来」 + 重试, 会话还没加载好, disabled |
| corrupt-session-wide/narrow | pass | 无法读取的会话 / 文件已损坏 / delete only, timeline copy, disabled with reason |
| verify-four-attempts-wide | pass | 第3/第4 at 768×512 · 20 步, buttons visible |
| verify-four-attempts-narrow | fail | R1-001 |
| verify-switch-back-wide | pass | 乙会话 highlighted, its own 2 attempts |
| verify-switch-back-narrow | fail | R1-001 |
| verify-after-delete-wide/narrow | pass | Only 留下来的会话 remains, current |
| verify-failed-and-cancelled-wide/narrow | pass | 「内存不足，生成被中止」 + 已取消, icon blocks |
