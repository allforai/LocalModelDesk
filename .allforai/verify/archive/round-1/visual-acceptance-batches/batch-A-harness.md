# Batch A — image sessions, harness screenshots (real Chromium, scripted media executor)

Node: image-session-verify · requirement `image-sessions` rev 1 · design `docs/superpowers/specs/2026-09-24-image-sessions-design.md`

## Review goal
Judge every screenshot below **by looking at the image** against the visual acceptance standard. Do not pass a
screenshot from its `.json` DOM-check record alone; the record only tells you what automation measured.

## Acceptance standard (read these first)
- `.allforai/visual-qa/visual-acceptance-criteria.md` — global rules + per-state must-show / must-not-show
- `.allforai/visual-qa/visual-acceptance-criteria.json` — the same, machine-readable
- `.allforai/visual-qa/visual-evidence-requirements.json` — which states and viewports are required
- Confirmed acceptance AC-7: 「在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误」

## How these were captured
- `python3 -m pytest tests/e2e/test_image_flow.py tests/e2e/test_image_sessions.py` with `LMD_IMAGE_SESSIONS_SHOTS=.allforai/verify/screens`
- Real DeskApp + real desk/static in headless Chromium (Playwright, native scrollbars on), viewport 1280×800 (wide) and 900×700 (narrow), viewport capture (not full page).
- Mock layers (declared, not defects): the media executor is scripted and writes a small **gradient PNG** instead of running Qwen-Image, so every "generated image" is an abstract colour gradient by design; fake LLM, fake memory reader, fixed clock (times may look identical). `session-list-load-failed` uses a Playwright route that answers 500 for GET /api/image-sessions.
- A separate batch (B) covers the real app window with the real model.

## Evidence
| state | viewport | screenshot | DOM-check record | criteria |
|---|---|---|---|---|
| first-entry-auto-session | wide | `.allforai/verify/screens/first-entry-auto-session-wide.png` | `.allforai/verify/screens/first-entry-auto-session-wide.json` | visual-acceptance-criteria.md § `first-entry-auto-session` |
| first-entry-auto-session | narrow | `.allforai/verify/screens/first-entry-auto-session-narrow.png` | `.allforai/verify/screens/first-entry-auto-session-narrow.json` | visual-acceptance-criteria.md § `first-entry-auto-session` |
| empty-session | wide | `.allforai/verify/screens/empty-session-wide.png` | `.allforai/verify/screens/empty-session-wide.json` | visual-acceptance-criteria.md § `empty-session` |
| empty-session | narrow | `.allforai/verify/screens/empty-session-narrow.png` | `.allforai/verify/screens/empty-session-narrow.json` | visual-acceptance-criteria.md § `empty-session` |
| running | wide | `.allforai/verify/screens/running-wide.png` | `.allforai/verify/screens/running-wide.json` | visual-acceptance-criteria.md § `running` |
| running | narrow | `.allforai/verify/screens/running-narrow.png` | `.allforai/verify/screens/running-narrow.json` | visual-acceptance-criteria.md § `running` |
| running-other-session | wide | `.allforai/verify/screens/running-other-session-wide.png` | `.allforai/verify/screens/running-other-session-wide.json` | visual-acceptance-criteria.md § `running-other-session` |
| running-other-session | narrow | `.allforai/verify/screens/running-other-session-narrow.png` | `.allforai/verify/screens/running-other-session-narrow.json` | visual-acceptance-criteria.md § `running-other-session` |
| timeline-three-rounds | wide | `.allforai/verify/screens/timeline-three-rounds-wide.png` | `.allforai/verify/screens/timeline-three-rounds-wide.json` | visual-acceptance-criteria.md § `timeline-three-rounds` |
| timeline-three-rounds | narrow | `.allforai/verify/screens/timeline-three-rounds-narrow.png` | `.allforai/verify/screens/timeline-three-rounds-narrow.json` | visual-acceptance-criteria.md § `timeline-three-rounds` |
| attempt-selected-actions | wide | `.allforai/verify/screens/attempt-selected-actions-wide.png` | `.allforai/verify/screens/attempt-selected-actions-wide.json` | visual-acceptance-criteria.md § `attempt-selected-actions` |
| attempt-selected-actions | narrow | `.allforai/verify/screens/attempt-selected-actions-narrow.png` | `.allforai/verify/screens/attempt-selected-actions-narrow.json` | visual-acceptance-criteria.md § `attempt-selected-actions` |
| refine-prefill | wide | `.allforai/verify/screens/refine-prefill-wide.png` | `.allforai/verify/screens/refine-prefill-wide.json` | visual-acceptance-criteria.md § `refine-prefill` |
| refine-prefill | narrow | `.allforai/verify/screens/refine-prefill-narrow.png` | `.allforai/verify/screens/refine-prefill-narrow.json` | visual-acceptance-criteria.md § `refine-prefill` |
| attempt-failed | wide | `.allforai/verify/screens/attempt-failed-wide.png` | `.allforai/verify/screens/attempt-failed-wide.json` | visual-acceptance-criteria.md § `attempt-failed` |
| attempt-failed | narrow | `.allforai/verify/screens/attempt-failed-narrow.png` | `.allforai/verify/screens/attempt-failed-narrow.json` | visual-acceptance-criteria.md § `attempt-failed` |
| attempt-cancelled | wide | `.allforai/verify/screens/attempt-cancelled-wide.png` | `.allforai/verify/screens/attempt-cancelled-wide.json` | visual-acceptance-criteria.md § `attempt-cancelled` |
| attempt-cancelled | narrow | `.allforai/verify/screens/attempt-cancelled-narrow.png` | `.allforai/verify/screens/attempt-cancelled-narrow.json` | visual-acceptance-criteria.md § `attempt-cancelled` |
| attempt-interrupted | wide | `.allforai/verify/screens/attempt-interrupted-wide.png` | `.allforai/verify/screens/attempt-interrupted-wide.json` | visual-acceptance-criteria.md § `attempt-interrupted` |
| attempt-interrupted | narrow | `.allforai/verify/screens/attempt-interrupted-narrow.png` | `.allforai/verify/screens/attempt-interrupted-narrow.json` | visual-acceptance-criteria.md § `attempt-interrupted` |
| attempt-file-missing | wide | `.allforai/verify/screens/attempt-file-missing-wide.png` | `.allforai/verify/screens/attempt-file-missing-wide.json` | visual-acceptance-criteria.md § `attempt-file-missing` |
| attempt-file-missing | narrow | `.allforai/verify/screens/attempt-file-missing-narrow.png` | `.allforai/verify/screens/attempt-file-missing-narrow.json` | visual-acceptance-criteria.md § `attempt-file-missing` |
| model-missing | wide | `.allforai/verify/screens/model-missing-wide.png` | `.allforai/verify/screens/model-missing-wide.json` | visual-acceptance-criteria.md § `model-missing` |
| model-missing | narrow | `.allforai/verify/screens/model-missing-narrow.png` | `.allforai/verify/screens/model-missing-narrow.json` | visual-acceptance-criteria.md § `model-missing` |
| runtime-unavailable | wide | `.allforai/verify/screens/runtime-unavailable-wide.png` | `.allforai/verify/screens/runtime-unavailable-wide.json` | visual-acceptance-criteria.md § `runtime-unavailable` |
| runtime-unavailable | narrow | `.allforai/verify/screens/runtime-unavailable-narrow.png` | `.allforai/verify/screens/runtime-unavailable-narrow.json` | visual-acceptance-criteria.md § `runtime-unavailable` |
| busy-other-media | wide | `.allforai/verify/screens/busy-other-media-wide.png` | `.allforai/verify/screens/busy-other-media-wide.json` | visual-acceptance-criteria.md § `busy-other-media` |
| busy-other-media | narrow | `.allforai/verify/screens/busy-other-media-narrow.png` | `.allforai/verify/screens/busy-other-media-narrow.json` | visual-acceptance-criteria.md § `busy-other-media` |
| rename | wide | `.allforai/verify/screens/rename-wide.png` | `.allforai/verify/screens/rename-wide.json` | visual-acceptance-criteria.md § `rename` |
| rename | narrow | `.allforai/verify/screens/rename-narrow.png` | `.allforai/verify/screens/rename-narrow.json` | visual-acceptance-criteria.md § `rename` |
| delete-confirm | wide | `.allforai/verify/screens/delete-confirm-wide.png` | `.allforai/verify/screens/delete-confirm-wide.json` | visual-acceptance-criteria.md § `delete-confirm` |
| delete-confirm | narrow | `.allforai/verify/screens/delete-confirm-narrow.png` | `.allforai/verify/screens/delete-confirm-narrow.json` | visual-acceptance-criteria.md § `delete-confirm` |
| delete-confirm-running | wide | `.allforai/verify/screens/delete-confirm-running-wide.png` | `.allforai/verify/screens/delete-confirm-running-wide.json` | visual-acceptance-criteria.md § `delete-confirm-running` |
| delete-confirm-running | narrow | `.allforai/verify/screens/delete-confirm-running-narrow.png` | `.allforai/verify/screens/delete-confirm-running-narrow.json` | visual-acceptance-criteria.md § `delete-confirm-running` |
| library-after-delete | wide | `.allforai/verify/screens/library-after-delete-wide.png` | `.allforai/verify/screens/library-after-delete-wide.json` | visual-acceptance-criteria.md § `library-after-delete` |
| library-after-delete | narrow | `.allforai/verify/screens/library-after-delete-narrow.png` | `.allforai/verify/screens/library-after-delete-narrow.json` | visual-acceptance-criteria.md § `library-after-delete` |
| session-list-load-failed | wide | `.allforai/verify/screens/session-list-load-failed-wide.png` | `.allforai/verify/screens/session-list-load-failed-wide.json` | visual-acceptance-criteria.md § `session-list-load-failed` |
| session-list-load-failed | narrow | `.allforai/verify/screens/session-list-load-failed-narrow.png` | `.allforai/verify/screens/session-list-load-failed-narrow.json` | visual-acceptance-criteria.md § `session-list-load-failed` |
| corrupt-session | wide | `.allforai/verify/screens/corrupt-session-wide.png` | `.allforai/verify/screens/corrupt-session-wide.json` | visual-acceptance-criteria.md § `corrupt-session` |
| corrupt-session | narrow | `.allforai/verify/screens/corrupt-session-narrow.png` | `.allforai/verify/screens/corrupt-session-narrow.json` | visual-acceptance-criteria.md § `corrupt-session` |
| verify-four-attempts (supplementary) | wide | `.allforai/verify/screens/verify-four-attempts-wide.png` | `.allforai/verify/screens/verify-four-attempts-wide.json` | AC-1/AC-2: four attempts (3 refine rounds + 换个构图) at 768×512 · 20 步; global rules only |
| verify-four-attempts (supplementary) | narrow | `.allforai/verify/screens/verify-four-attempts-narrow.png` | `.allforai/verify/screens/verify-four-attempts-narrow.json` | AC-1/AC-2: four attempts (3 refine rounds + 换个构图) at 768×512 · 20 步; global rules only |
| verify-switch-back (supplementary) | wide | `.allforai/verify/screens/verify-switch-back-wide.png` | `.allforai/verify/screens/verify-switch-back-wide.json` | AC-4: session B after switching A→B→A→B, two attempts of its own; global rules only |
| verify-switch-back (supplementary) | narrow | `.allforai/verify/screens/verify-switch-back-narrow.png` | `.allforai/verify/screens/verify-switch-back-narrow.json` | AC-4: session B after switching A→B→A→B, two attempts of its own; global rules only |
| verify-after-delete (supplementary) | wide | `.allforai/verify/screens/verify-after-delete-wide.png` | `.allforai/verify/screens/verify-after-delete-wide.json` | AC-5: after deleting session A, the remaining session is current; global rules only |
| verify-after-delete (supplementary) | narrow | `.allforai/verify/screens/verify-after-delete-narrow.png` | `.allforai/verify/screens/verify-after-delete-narrow.json` | AC-5: after deleting session A, the remaining session is current; global rules only |
| verify-failed-and-cancelled (supplementary) | wide | `.allforai/verify/screens/verify-failed-and-cancelled-wide.png` | `.allforai/verify/screens/verify-failed-and-cancelled-wide.json` | AC-6: one failed (内存不足) + one cancelled attempt after a page reload; global rules only |
| verify-failed-and-cancelled (supplementary) | narrow | `.allforai/verify/screens/verify-failed-and-cancelled-narrow.png` | `.allforai/verify/screens/verify-failed-and-cancelled-narrow.json` | AC-6: one failed (内存不足) + one cancelled attempt after a page reload; global rules only |

## Visual questions
1. Layout: session list on the left with 「新会话」 on top, timeline on the right, composer (prompt + 「生成图片」 + folded 「高级参数」) at the bottom; nothing overlapping, nothing pushed off-screen, no horizontal scroll — at both widths.
2. Truncation: any button text clipped? any session title or text cut without an ellipsis? do the two action buttons 「在这张基础上改」「换个构图」 stay fully visible (wrapping to a new line is allowed, clipping is not)?
3. Blank states: any empty grey image box, broken-image icon, or blank region where content should be? failed / cancelled / missing-file cards must show an icon block, not an image frame.
4. The word 「种子」 must not appear anywhere visible except inside an expanded 「高级参数」 block.
5. Per-state must-show / must-not-show items from the criteria doc — check each one.
6. Chinese copy is correct and readable; contrast adequate; current session is highlighted.

## Blocking failure codes
`occlusion`, `clipped_text`, `blank_image_frame`, `broken_image`, `horizontal_scroll`, `seed_word_in_main_flow`, `missing_required_element`, `wrong_state`, `foreign_pane_content`.

## Output contract (for the reviewer)
Severity per issue: `blocker` | `major` | `minor` | `note`. Every issue names the screenshot path(s), the criteria item, what you saw, and a repair suggestion. List every screenshot you actually opened in `inspected[]`; a screenshot you did not open cannot be passed.
