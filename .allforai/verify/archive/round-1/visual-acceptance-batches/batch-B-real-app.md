# Batch B — image sessions in the real packaged app with the real Qwen-Image model

Node: image-session-verify · requirement `image-sessions` rev 1 · design `docs/superpowers/specs/2026-09-24-image-sessions-design.md`

## Review goal
Judge every screenshot below **by looking at the image** against `.allforai/visual-qa/visual-acceptance-criteria.md`
(global rules + the per-state section named in the table). Confirmed acceptance AC-7: 「在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误」.

## How these were captured
- `real-*`: an isolated copy of the packaged app (`scripts/build-app.sh`, Developer ID signed, scratch output path, own data root, ports 8791/8792) running the **real** `image-models/qwen-image-2.1-heretic` model through its bundled MLX runtime. No mock layers. Screens come from the app's own WKWebView (`scripts/visual-capture.py`, WKWebView takeSnapshot) after resizing the window to 1280×800 (wide) and 900×700 (narrow). Known capture property: WKWebView takeSnapshot never draws document-level scrollbars (element-level ones are drawn) — a missing page scrollbar is not a defect. Images are real model outputs at 512×512.
- The journey (`.allforai/verify/real_journey.py`, record `.allforai/verify/evidence/real/journey.json`): generate → 在这张基础上改 → generate (×3 rounds) → 换个构图 → start + 取消 → 新会话 + generate → switch back → stop and restart the app → delete the second session → 素材库 preview.
- The two re-captured harness states use headless Chromium with the scripted executor (gradient PNG) exactly as batch A, now with the data preconditions the criteria state (B already has a finished attempt; runtime present but model missing).

## Evidence
| state | viewport | screenshot | record | what / criteria |
|---|---|---|---|---|
| real-running | wide | `.allforai/verify/evidence/real/real-running-wide.png` | `.allforai/verify/evidence/real/real-running-wide.json` (probe readback) | running — first real Qwen-Image generation in progress (512×512, 6 steps); criteria § `running` |
| real-running | narrow | `.allforai/verify/evidence/real/real-running-narrow.png` | `.allforai/verify/evidence/real/real-running-narrow.json` (probe readback) | running — first real Qwen-Image generation in progress (512×512, 6 steps); criteria § `running` |
| real-refine-prefill | wide | `.allforai/verify/evidence/real/real-refine-prefill-wide.png` | `.allforai/verify/evidence/real/real-refine-prefill-wide.json` (probe readback) | after 「在这张基础上改」 on attempt 2, before submitting; criteria § `refine-prefill` |
| real-refine-prefill | narrow | `.allforai/verify/evidence/real/real-refine-prefill-narrow.png` | `.allforai/verify/evidence/real/real-refine-prefill-narrow.json` (probe readback) | after 「在这张基础上改」 on attempt 2, before submitting; criteria § `refine-prefill` |
| real-timeline-three-rounds | wide | `.allforai/verify/evidence/real/real-timeline-three-rounds-wide.png` | `.allforai/verify/evidence/real/real-timeline-three-rounds-wide.json` (probe readback) | three real rounds generate → refine → generate in one session; criteria § `timeline-three-rounds` |
| real-timeline-three-rounds | narrow | `.allforai/verify/evidence/real/real-timeline-three-rounds-narrow.png` | `.allforai/verify/evidence/real/real-timeline-three-rounds-narrow.json` (probe readback) | three real rounds generate → refine → generate in one session; criteria § `timeline-three-rounds` |
| real-attempt-selected-actions | wide | `.allforai/verify/evidence/real/real-attempt-selected-actions-wide.png` | `.allforai/verify/evidence/real/real-attempt-selected-actions-wide.json` (probe readback) | attempt 1 selected (expanded) with the two actions; criteria § `attempt-selected-actions` |
| real-attempt-selected-actions | narrow | `.allforai/verify/evidence/real/real-attempt-selected-actions-narrow.png` | `.allforai/verify/evidence/real/real-attempt-selected-actions-narrow.json` (probe readback) | attempt 1 selected (expanded) with the two actions; criteria § `attempt-selected-actions` |
| real-attempt-cancelled | wide | `.allforai/verify/evidence/real/real-attempt-cancelled-wide.png` | `.allforai/verify/evidence/real/real-attempt-cancelled-wide.json` (probe readback) | a real generation cancelled with 取消 (5th attempt); criteria § `attempt-cancelled` |
| real-attempt-cancelled | narrow | `.allforai/verify/evidence/real/real-attempt-cancelled-narrow.png` | `.allforai/verify/evidence/real/real-attempt-cancelled-narrow.json` (probe readback) | a real generation cancelled with 取消 (5th attempt); criteria § `attempt-cancelled` |
| real-after-restart | wide | `.allforai/verify/evidence/real/real-after-restart-wide.png` | `.allforai/verify/evidence/real/real-after-restart-wide.json` (probe readback) | after stopping the app processes and starting again on the same data root; criteria § `(AC-3; global rules)` |
| real-after-restart | narrow | `.allforai/verify/evidence/real/real-after-restart-narrow.png` | `.allforai/verify/evidence/real/real-after-restart-narrow.json` (probe readback) | after stopping the app processes and starting again on the same data root; criteria § `(AC-3; global rules)` |
| real-delete-confirm | wide | `.allforai/verify/evidence/real/real-delete-confirm-wide.png` | `.allforai/verify/evidence/real/real-delete-confirm-wide.json` (probe readback) | delete confirmation for the second session; criteria § `delete-confirm` |
| real-delete-confirm | narrow | `.allforai/verify/evidence/real/real-delete-confirm-narrow.png` | `.allforai/verify/evidence/real/real-delete-confirm-narrow.json` (probe readback) | delete confirmation for the second session; criteria § `delete-confirm` |
| real-library-after-delete | wide | `.allforai/verify/evidence/real/real-library-after-delete-wide.png` | `.allforai/verify/evidence/real/real-library-after-delete-wide.json` (probe readback) | 素材库 preview of the deleted session's image; criteria § `library-after-delete` |
| real-library-after-delete | narrow | `.allforai/verify/evidence/real/real-library-after-delete-narrow.png` | `.allforai/verify/evidence/real/real-library-after-delete-narrow.json` (probe readback) | 素材库 preview of the deleted session's image; criteria § `library-after-delete` |
| running-other-session (re-captured, harness) | wide | `.allforai/verify/screens-recapture/running-other-session-wide.png` | `.allforai/verify/screens-recapture/running-other-session-wide.json` | criteria § `running-other-session` — now with the stated data precondition |
| running-other-session (re-captured, harness) | narrow | `.allforai/verify/screens-recapture/running-other-session-narrow.png` | `.allforai/verify/screens-recapture/running-other-session-narrow.json` | criteria § `running-other-session` — now with the stated data precondition |
| model-missing (re-captured, harness) | wide | `.allforai/verify/screens-recapture/model-missing-wide.png` | `.allforai/verify/screens-recapture/model-missing-wide.json` | criteria § `model-missing` — now with the stated data precondition |
| model-missing (re-captured, harness) | narrow | `.allforai/verify/screens-recapture/model-missing-narrow.png` | `.allforai/verify/screens-recapture/model-missing-narrow.json` | criteria § `model-missing` — now with the stated data precondition |

## Visual questions
1. Layout at both widths: session list left with 「新会话」 on top, timeline right, composer at the bottom; no overlap, nothing off-screen, no horizontal scroll.
2. Are the two action buttons 「在这张基础上改」「换个构图」 fully visible on the expanded card, at both widths? Is any button text or title clipped?
3. Real images: do thumbnails and the expanded image show real pictures (no blank frame, no broken icon, no grey placeholder)? Cancelled cards: icon block and no image frame.
4. 「种子」 must not be visible except inside an expanded 「高级参数」 block.
5. After restart: are the session list, the attempts and their images still there?
6. Per-state must-show / must-not-show items from the criteria doc.

## Blocking failure codes
`occlusion`, `clipped_text`, `blank_image_frame`, `broken_image`, `horizontal_scroll`, `seed_word_in_main_flow`, `missing_required_element`, `wrong_state`, `foreign_pane_content`.

## Output contract
Severity per issue: `blocker` | `major` | `minor` | `note`, each naming screenshot path(s), criteria item, observation and repair suggestion; list every screenshot you opened in `inspected[]`.
