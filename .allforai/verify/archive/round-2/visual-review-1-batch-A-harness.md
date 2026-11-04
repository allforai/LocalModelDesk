# Visual review 1 — batch A (harness screenshots)

- Reviewer: reviewer-1 · claude -p fresh context · model claude-opus-5-5
- Batch: `batch-A-harness` (verify round 2)
- Standard: `.allforai/visual-qa/visual-acceptance-criteria.md` + batch visual questions 1–6
- Screenshots opened as images: **54 / 54** (all listed in the batch table; all present, all readable)
- **Status: `failed_visual_review`** — 1 major, 3 minor, 6 notes. No blockers.

## Summary

Nearly everything checks out. At both widths the layout is correct: the session list with 「新会话」 is on the left, the timeline on the right, and the composer at the bottom with 「高级参数」 folded. Nothing overlaps, there is no horizontal scroll, and no button text is clipped. 「在这张基础上改」 and 「换个构图」 are fully visible everywhere they should be. Failed, cancelled, interrupted and missing-file cards all show icon blocks, not image frames. There are no broken images. 「种子」 appears nowhere on the image page. On the library page it appears only in item metadata, which D-50a exempts. Each state's must-show and must-not-show copy is present, including both delete-dialog sentences, the 「回到该会话」 button, the corrupt-session copy and the load-failed copy with 「重试」.

The one problem that fails this batch is **the size of the expanded 「大图」**. When a finished card is expanded, the large image is shrunk so the whole card fits in the timeline. It also shares that space with a duplicate 96×96 thumbnail and a second full copy of the prompt. As a result, in the 900×700 viewport the "large" image is 96–147 px tall. In two screenshots it is the same size as the thumbnail right above it. Nothing is cut off, but the user cannot really look at the image they just made, and that image is the main output of this page.

---

## Blockers

None.

## Majors

### R1-batch-A-harness-001 — In the narrow viewport the expanded 「大图」 is thumbnail-sized (`missing_required_element`)

- **Screenshots (narrow, 900×700):**
  - `.allforai/verify/screens/busy-other-media-narrow.png`: the large image is ≈96×96, the same size as the thumbnail directly above it
  - `.allforai/verify/screens/running-other-session-narrow.png`: the large image is ≈96×96, the same size as the thumbnail
  - `.allforai/verify/screens/verify-selected-full-size-narrow.png`: ≈110×110
  - `.allforai/verify/screens/refine-prefill-narrow.png`: ≈110×110
  - `.allforai/verify/screens/timeline-three-rounds-narrow.png`: ≈126×126
  - `.allforai/verify/screens/attempt-selected-actions-narrow.png`: ≈147×147
  - `.allforai/verify/screens/rename-narrow.png`, `verify-switch-back-narrow.png`, `verify-after-delete-narrow.png`: ≈147×147
  - `.allforai/verify/screens/verify-four-attempts-narrow.png`: ≈221×147 (768×512 image)
  - For comparison, wide (1280×800): 182–247 px (`running-other-session-wide.png` 182 px, `verify-selected-full-size-wide.png` 211 px, `timeline-three-rounds-wide.png` 247 px). That is small too, but still usable.
- **Criteria:** `timeline-three-rounds` must show 「最后一次展开：大图…」. `attempt-selected-actions` must show 「大图完整显示（不超过 60vh、不被裁切）」. Design D-74: the large image may be as wide as the timeline column and up to 60vh tall. At 900×700 that is ≈500 px wide × 420 px tall, so the space exists.
- **Observation:** The image is never clipped and it respects the 60vh limit, so the letter of the criteria holds. But the expanded card spends vertical space on a 96×96 thumbnail and a full prompt line in the header, then repeats the full prompt under the image. The large image gets whatever height is left. In two narrow screenshots it is exactly as big as the thumbnail. In the rest it is at most 1.5× the thumbnail. A 1024×1024 result shown at about 100–150 px does not count as a 「大图」, and expanding the card adds almost nothing.
- **Repair suggestion:** (a) Drop the thumbnail from the expanded card header, since the large image replaces it. Keep 「第 N 次 · HH:MM」 and 「宽×高 · N 步」 as text. (b) Show the prompt once, either in the header or under the image. Together (a) and (b) free about 130 px of height. (c) Give the image a real minimum instead of fitting the whole card into the visible timeline. For example, use `max-height: min(60vh, <timeline height − ~150px>)` with a floor around 240–280 px. Let the actions scroll into view (see the batch-B pattern) rather than shrinking the image. Then re-capture the narrow screenshots listed above.

## Minors

### R1-batch-A-harness-002 — Session titles cut to 3–4 characters when the 「生成中」 badge is shown (`clipped_text`, ellipsis allowed)

- **Screenshots:** `running-wide.png`/`running-narrow.png` (「会失败的…」), `running-other-session-wide.png`/`-narrow.png` (「甲会话：…」), `running-other-session-new-empty-wide.png`/`-narrow.png` (「甲会话的…」), `delete-confirm-running-wide.png`/`-narrow.png` (「删除时还…」)
- **Criteria:** Global rules. An ellipsis is allowed on session titles, so this is not a blocking clip. Batch visual question 6 (readable).
- **Observation:** About 90 px of empty space sits to the right of the 「● 生成中」 badge, yet the title is cut after 3–4 characters. The space looks reserved for the edit/delete buttons, which are not shown on these items. 「甲会话：…」 hides everything that tells two sessions apart. In practice, the session that is generating is the one whose name you can't read.
- **Repair suggestion:** Only reserve action-button width when the buttons are rendered, or when the item is hovered or current. Or move the 「生成中」 badge to the meta line (「1 次生成 · 09:26 · ● 生成中」) so the title gets the whole row.

### R1-batch-A-harness-003 — Expanded card shows the full prompt twice, plus a duplicate thumbnail

- **Screenshots:** every expanded finished card, e.g. `timeline-three-rounds-wide.png`, `attempt-selected-actions-wide.png`, `verify-selected-full-size-wide.png`, `busy-other-media-wide.png`
- **Criteria:** D-73/D-74. The collapsed card has a 提示词摘要 of at most two lines; the expanded card adds the full prompt.
- **Observation:** In the expanded card, the header prompt appears in full (not as a summary). The same text repeats under the image. The thumbnail repeats the large image. This clutter is also what causes R1-001.
- **Repair suggestion:** When a card is expanded, hide the header thumbnail and header prompt, or turn the header prompt into a one-line summary.

### R1-batch-A-harness-004 — 「新会话」 button sits directly on the first session card

- **Screenshots:** all image-page screenshots, e.g. `first-entry-auto-session-wide.png`, `empty-session-narrow.png`
- **Criteria:** Global "no overlap". This is not an overlap, only spacing.
- **Observation:** The bottom edge of the 「新会话」 button (y≈146) touches the top border of the first session item (y≈147) with no gap. It looks cramped, and at a glance the button seems to overlap the highlighted item's border.
- **Repair suggestion:** Add about 8–12 px of margin under the 「新会话」 button.

## Notes (no action required for this gate)

- **N-005:** `model-missing-*.png` and `runtime-unavailable-*.png` still show the empty-state line 「在下面写下想要的画面，点「生成图片」…」 while 「生成图片」 is disabled. The status line explains why, so this passes, but the empty state could point to the reason instead.
- **N-006:** `library-after-delete-*.png` is captured scrolled to the bottom of the library. The app header and tabs are off-screen, and in the narrow capture the target row 「将被删除分组的灯塔」 is cut at the bottom edge. The must-show item 「图片页会话列表里已无该会话」 does not appear in this pair; it is shown by `verify-after-delete-*.png`. The real preview image and the 「正在预览：将被删除分组的灯塔」 label are visible, so the state passes.
- **N-007:** `rename-*.png` has only one session, so 「其他会话项不变」 cannot be judged. The input fits in the left column.
- **N-008:** `verify-four-attempts-*.png`: the session title reads 「清晨的港口， 渔船…」 with an odd space after the comma. It probably comes from the first attempt's prompt text. Check how the title is derived.
- **N-009:** `running-other-session-*.png`: while you view B, the composer still holds 「甲会话：正在生成」. This looks consistent with a global draft (compare 「草稿不应被改」 in `empty-session`), but it makes B's composer look like A's.
- **N-010:** `attempt-interrupted-wide.png`: the timeline is scrolled, so the top card's header 「第 1 次」 is cut by the scroll container edge. This is normal scroll clipping, not a defect.

## Per-screenshot verdicts

| screenshot | verdict | note |
|---|---|---|
| first-entry-auto-session-wide / -narrow | pass | one 「新会话」, highlighted; two-line empty state; button enabled; advanced folded |
| empty-session-wide / -narrow | pass | new session on top, highlighted; empty state; prompt focused (draft kept) |
| running-wide / -narrow | pass | 「第 2 次 · 生成中…（已用 0秒）」, progress bar, 取消, 日志, badge, disabled button + status line; minor R1-002 |
| running-other-session-wide | pass | A has badge; B highlighted; status + 「回到该会话」; 生成/换个构图 disabled, 改 enabled; R1-001 (wide, small) / R1-002 |
| running-other-session-narrow | **fail** | R1-001: large image ≈96 px = thumbnail |
| timeline-three-rounds-wide | pass | 第 3 次 expanded with both actions; image 247 px |
| timeline-three-rounds-narrow | **fail** | R1-001: large image ≈126 px |
| timeline-three-rounds-top-wide / -narrow | pass | 第 1→2→3 order, three real thumbnails, summaries + 1024×1024 · 40 步 |
| attempt-selected-actions-wide | pass | 第 1 次 expanded alone; both actions visible |
| attempt-selected-actions-narrow | **fail** | R1-001: large image ≈147 px |
| refine-prefill-wide | pass | chip 「沿用第 2 次的构图 ×」, prompt prefilled + focused, advanced folded, no new card |
| refine-prefill-narrow | **fail** | R1-001: large image ≈110 px (refine-prefill must-show items themselves pass) |
| attempt-failed-wide / -narrow | pass | 失败 badge, 「生成程序异常退出」, danger icon block, 详情 with code + log tail, both actions |
| attempt-cancelled-wide / -narrow | pass | 已取消 badge + 「这次生成被手动停止」, grey icon block, both actions |
| attempt-interrupted-wide / -narrow | pass | 「应用在生成途中关闭，这次没有完成」, danger icon block, no progress |
| attempt-file-missing-wide / -narrow | pass | 「图片文件已不在」 + 「可能已在访达中移动或删除」, grey image icon, actions enabled |
| model-missing-wide / -narrow | pass | header + status line copy; button disabled; N-005 |
| runtime-unavailable-wide / -narrow | pass | runtime reason in status line; button disabled; N-005 |
| busy-other-media-wide | pass | 「媒体作业进行中」, 生成/换个构图 disabled, no 「回到该会话」 |
| busy-other-media-narrow | **fail** | R1-001: large image ≈96 px = thumbnail |
| rename-wide | pass | inline input with title, focused, fits column; N-007 |
| rename-narrow | **fail** | R1-001: large image ≈147 px (rename must-show items themselves pass) |
| delete-confirm-wide / -narrow | pass | 删除会话 title, exact body copy, 取消 focused, 删除 danger |
| delete-confirm-running-wide / -narrow | pass | base body + appended running sentence; R1-002 in list behind |
| library-after-delete-wide / -narrow | pass | real preview image, rows listed; N-006 |
| session-list-load-failed-wide / -narrow | pass | 「会话列表读不出来：磁盘读不出来」 + 重试; button disabled; 「会话还没加载好」 |
| corrupt-session-wide / -narrow | pass | 无法读取的会话 / 文件已损坏 / delete only; timeline copy; reason 「请选择其他会话或新建一个」 |
| running-other-session-new-empty-wide / -narrow | pass | empty B highlighted; A with badge; status + 「回到该会话」; R1-002 |
| verify-four-attempts-wide | pass | 第 4 次 768×512 · 20 步 expanded, both actions; N-008 |
| verify-four-attempts-narrow | **fail** | R1-001: large image ≈221×147 |
| verify-switch-back-wide | pass | B highlighted, own 第 2 次 expanded |
| verify-switch-back-narrow | **fail** | R1-001: large image ≈147 px |
| verify-after-delete-wide | pass | only 留下来的会话 remains, current |
| verify-after-delete-narrow | **fail** | R1-001: large image ≈147 px |
| verify-failed-and-cancelled-wide / -narrow | pass | 「内存不足，生成被中止」 failed + cancelled cards, icon blocks, both actions |
| verify-selected-full-size-wide | pass | header, whole image, prompt, advanced, both actions together; image 211 px |
| verify-selected-full-size-narrow | **fail** | R1-001: large image ≈110 px |
