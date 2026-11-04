# Visual review 2 (codex exec, GPT-6)
Overall status: **failed_visual_review** — merged mechanically from the two batch reports below (verbatim).

---

<!-- verbatim: visual-review-2-batch-A-harness.md -->
# Independent visual review — reviewer 2 / batch-A-harness

Backend: codex exec. Model: GPT-6.

Status: **failed_visual_review**. Inspected all 48 supplied PNGs using view_image. Failed visual review: 5 major issues, 2 minor issues, 1 scope note; no missing or unreadable screenshots. Judgments use visible pixels, not DOM-check records.

Read the batch harness and both acceptance-standard formats plus evidence requirements. Opened every listed screenshot individually with the image-viewing tool. No screenshot DOM-check records or other reviewers’ reports were read. No application changes or recaptures were made.

Scope: pass means the visible state meets the applicable visual checks, not proof of ARIA attributes, DOM focus, click behavior, persistence or hidden content. No visible broken images, empty image frames, horizontal page scrollbars, or foreign video/music pane content were found. Ordinary clipping of nonrequired history at a vertical scroll boundary is not automatically an overlap defect. The specifically required timeline content and action visibility gaps are identified below. Library layout is assessed as the explicitly requested library state rather than incorrectly requiring the image composer on that tab.

## Blockers

None.

## Majors

### R2-batch-A-harness-001 — wrong_state

Criteria: visual-acceptance-criteria.md § running-other-session; AC-4/AC-7

Screenshots:
- `.allforai/verify/screens/running-other-session-wide.png`
- `.allforai/verify/screens/running-other-session-narrow.png`

Observation: Both images select 新会话 with 0 次生成 and show 还没有图片. The required completed B attempt and its enabled refine / disabled variation controls are absent. A running badge and named return link are visible.

Repair suggestion: Prepare B with a completed attempt before starting A; select and expand B, then recapture both widths. This evidence cannot establish the required busy-state action behavior.

### R2-batch-A-harness-002 — missing_required_element

Criteria: visual-acceptance-criteria.md § timeline-three-rounds must-show 1–4

Screenshots:
- `.allforai/verify/screens/timeline-three-rounds-wide.png`
- `.allforai/verify/screens/timeline-three-rounds-narrow.png`

Observation: The first attempt header and prompt are above the timeline viewport in wide; narrow shows only its bottom edge. Thus neither capture shows 第1次→第2次→第3次 with three complete thumbnails. Narrow also cuts off the expanded third card before its advanced disclosure and action buttons.

Repair suggestion: Adjust timeline/card sizing or provide complementary viewport evidence showing the complete ordered history and selected card controls. Recalculate scroll positioning after changing viewport size; do not treat offscreen content as visually verified.

### R2-batch-A-harness-003 — missing_required_element

Criteria: batch-A-harness.md visual questions 1–2; AC-7

Screenshots:
- `.allforai/verify/screens/refine-prefill-narrow.png`
- `.allforai/verify/screens/verify-four-attempts-narrow.png`
- `.allforai/verify/screens/verify-switch-back-narrow.png`

Observation: The expanded card extends below the timeline viewport. Refine-prefill and four-attempts omit both action buttons; switch-back shows only their top borders at the bottom edge, with no readable labels. The composer itself remains visible.

Repair suggestion: Keep the selected card actions visible after resize and composer growth, for example by scrolling the action row into view or using a persistent action row. Recapture at 900×700. A screenshot does not establish whether manual scrolling would recover them.

### R2-batch-A-harness-004 — wrong_state

Criteria: visual-acceptance-criteria.md § model-missing must-show 1

Screenshots:
- `.allforai/verify/screens/model-missing-wide.png`
- `.allforai/verify/screens/model-missing-narrow.png`

Observation: Header correctly says 尚未安装图片模型，请到「资源」页下载, but the bottom status instead says 图片 MLX 运行环境缺失，请安装 .venv-image 或使用包含图片运行时的应用. Required model-download status is absent there. Generate appears disabled.

Repair suggestion: Capture model-missing with runtime available and show the model-download explanation in the status line; if multiple failures coexist, make the priority explicit and add separate evidence.

### R2-batch-A-harness-005 — seed_word_in_main_flow

Criteria: visual-acceptance-criteria.md global forbidden seed word; visual-acceptance-criteria.json states[library-after-delete].must_not_show

Screenshots:
- `.allforai/verify/screens/library-after-delete-wide.png`
- `.allforai/verify/screens/library-after-delete-narrow.png`

Observation: Both library rows visibly show 种子 followed by numbers outside any expanded 高级参数. The gradient preview itself is present and unbroken. The JSON standard explicitly repeats this prohibition for library-after-delete.

Repair suggestion: Move seed metadata into an expanded advanced disclosure, or obtain an explicit acceptance-standard change if the library is intended to be exempt; the current written standard does not exempt it.


## Minors

### R2-batch-A-harness-006 — missing_required_element

Criteria: visual-acceptance-criteria.md § attempt-cancelled must-show 1

Screenshots:
- `.allforai/verify/screens/attempt-cancelled-wide.png`
- `.allforai/verify/screens/attempt-cancelled-narrow.png`

Observation: The 已取消 badge, gray X icon and two actions are clear, but no separate cancellation explanation is visible; the repeated text 会被取消的一张 is the prompt.

Repair suggestion: Add a brief explanation such as 已取消本次生成，未生成图片 below the status, preserving the existing controls.

### R2-batch-A-harness-007 — focus_not_visible

Criteria: visual-acceptance-criteria.md § delete-confirm: 取消获得焦点

Screenshots:
- `.allforai/verify/screens/delete-confirm-wide.png`
- `.allforai/verify/screens/delete-confirm-narrow.png`
- `.allforai/verify/screens/delete-confirm-running-wide.png`
- `.allforai/verify/screens/delete-confirm-running-narrow.png`

Observation: Cancel has an ordinary dark button border with no discernible focus indicator in these captures. Dialog wording, danger styling and running continuation sentence are readable. Actual DOM focus cannot be established from these pixels.

Repair suggestion: Give the initially focused Cancel button a clearly visible focus treatment and capture it; verify keyboard focus separately.


## Notes

### R2-batch-A-harness-008 — evidence_scope

Criteria: batch-A-harness.md declared mock layers; § attempt-selected-actions; § library-after-delete

Screenshots:
- `.allforai/verify/screens/attempt-selected-actions-wide.png`
- `.allforai/verify/screens/attempt-selected-actions-narrow.png`
- `.allforai/verify/screens/library-after-delete-wide.png`
- `.allforai/verify/screens/library-after-delete-narrow.png`

Observation: Gradient images render at approximately 96×64, including expanded/preview images. This is consistent with the declared small PNG fixture, not a broken-image defect. Library views cannot simultaneously show the image-session sidebar; verify-after-delete provides the complementary remaining-session view.

Repair suggestion: Keep fixture limitations explicit and use batch B to assess real-resolution image sizing. Do not claim model-output quality or actual-resolution preview coverage from batch A.


## Per-screenshot inspection

| Screenshot | State / viewport | Verdict | Observation |
|---|---|---|---|
| `.allforai/verify/screens/first-entry-auto-session-wide.png` | first-entry-auto-session / wide | pass | One highlighted 新会话, centered empty guidance, enabled-looking generate button and folded advanced control; no image placeholder. |
| `.allforai/verify/screens/first-entry-auto-session-narrow.png` | first-entry-auto-session / narrow | pass | One highlighted 新会话, centered empty guidance, enabled-looking generate button and folded advanced control; no image placeholder. |
| `.allforai/verify/screens/empty-session-wide.png` | empty-session / wide | pass | New empty session is first and highlighted; older session remains listed; prompt has a blue focus border and no prior attempt cards appear. |
| `.allforai/verify/screens/empty-session-narrow.png` | empty-session / narrow | pass | New empty session is first and highlighted; older session remains listed; prompt has a blue focus border and no prior attempt cards appear. |
| `.allforai/verify/screens/running-wide.png` | running / wide | pass | Expanded running attempt, progress, cancel and folded log are visible; sidebar running badge and disabled-looking generate with specific status are present. |
| `.allforai/verify/screens/running-narrow.png` | running / narrow | pass | Expanded running attempt, progress, cancel and folded log are visible; sidebar running badge and disabled-looking generate with specific status are present. |
| `.allforai/verify/screens/running-other-session-wide.png` | running-other-session / wide | fail | Empty selected session instead of required completed B attempt; named A status and return link visible. See 001. |
| `.allforai/verify/screens/running-other-session-narrow.png` | running-other-session / narrow | fail | Empty selected session instead of required completed B attempt; named A status and return link visible. See 001. |
| `.allforai/verify/screens/timeline-three-rounds-wide.png` | timeline-three-rounds / wide | fail | Required first attempt is cropped above timeline viewport; narrow also omits third-card actions. See 002. |
| `.allforai/verify/screens/timeline-three-rounds-narrow.png` | timeline-three-rounds / narrow | fail | Required first attempt is cropped above timeline viewport; narrow also omits third-card actions. See 002. |
| `.allforai/verify/screens/attempt-selected-actions-wide.png` | attempt-selected-actions / wide | pass | First attempt expanded, gradient fully visible, both action labels complete; following cards collapsed within a vertically scrollable timeline. |
| `.allforai/verify/screens/attempt-selected-actions-narrow.png` | attempt-selected-actions / narrow | pass | First attempt expanded, gradient fully visible, both action labels complete; following cards collapsed within a vertically scrollable timeline. |
| `.allforai/verify/screens/refine-prefill-wide.png` | refine-prefill / wide | pass | 第2次 composition chip with ×, matching prompt and blue input focus border visible; no running card. Narrow card actions offscreen: 003. |
| `.allforai/verify/screens/refine-prefill-narrow.png` | refine-prefill / narrow | fail | 第2次 composition chip with ×, matching prompt and blue input focus border visible; no running card. Narrow card actions offscreen: 003. |
| `.allforai/verify/screens/attempt-failed-wide.png` | attempt-failed / wide | pass | Red X and failure badge, human-readable abnormal-exit reason, expanded code/log details and both actions visible. |
| `.allforai/verify/screens/attempt-failed-narrow.png` | attempt-failed / narrow | pass | Red X and failure badge, human-readable abnormal-exit reason, expanded code/log details and both actions visible. |
| `.allforai/verify/screens/attempt-cancelled-wide.png` | attempt-cancelled / wide | fail | Gray X, 已取消 badge and both actions visible; no progress or blank frame. Missing explanatory copy: 006. |
| `.allforai/verify/screens/attempt-cancelled-narrow.png` | attempt-cancelled / narrow | fail | Gray X, 已取消 badge and both actions visible; no progress or blank frame. Missing explanatory copy: 006. |
| `.allforai/verify/screens/attempt-interrupted-wide.png` | attempt-interrupted / wide | pass | Red failure icon and 应用在生成途中关闭，这次没有完成 are visible; no running progress. |
| `.allforai/verify/screens/attempt-interrupted-narrow.png` | attempt-interrupted / narrow | pass | Red failure icon and 应用在生成途中关闭，这次没有完成 are visible; no running progress. |
| `.allforai/verify/screens/attempt-file-missing-wide.png` | attempt-file-missing / wide | pass | Gray image icon, 图片文件已不在 and movement/deletion explanation visible; both actions appear enabled. |
| `.allforai/verify/screens/attempt-file-missing-narrow.png` | attempt-file-missing / narrow | pass | Gray image icon, 图片文件已不在 and movement/deletion explanation visible; both actions appear enabled. |
| `.allforai/verify/screens/model-missing-wide.png` | model-missing / wide | fail | Model warning in header, runtime warning in bottom status; generate disabled-looking. See 004. |
| `.allforai/verify/screens/model-missing-narrow.png` | model-missing / narrow | fail | Model warning in header, runtime warning in bottom status; generate disabled-looking. See 004. |
| `.allforai/verify/screens/runtime-unavailable-wide.png` | runtime-unavailable / wide | pass | Runtime-missing explanation and disabled-looking generate visible; no layout clipping. |
| `.allforai/verify/screens/runtime-unavailable-narrow.png` | runtime-unavailable / narrow | pass | Runtime-missing explanation and disabled-looking generate visible; no layout clipping. |
| `.allforai/verify/screens/busy-other-media-wide.png` | busy-other-media / wide | pass | Completed card remains visible; variation and generate dimmed, refine available-looking; media-busy reason present and no return-to-session control. |
| `.allforai/verify/screens/busy-other-media-narrow.png` | busy-other-media / narrow | pass | Completed card remains visible; variation and generate dimmed, refine available-looking; media-busy reason present and no return-to-session control. |
| `.allforai/verify/screens/rename-wide.png` | rename / wide | pass | Focused blue-bordered title input fits within sidebar and contains current prompt-derived title. |
| `.allforai/verify/screens/rename-narrow.png` | rename / narrow | pass | Focused blue-bordered title input fits within sidebar and contains current prompt-derived title. |
| `.allforai/verify/screens/delete-confirm-wide.png` | delete-confirm / wide | fail | Centered readable dialog preserves-image wording and red delete button; Cancel focus not visually distinct: 007. |
| `.allforai/verify/screens/delete-confirm-narrow.png` | delete-confirm / narrow | fail | Centered readable dialog preserves-image wording and red delete button; Cancel focus not visually distinct: 007. |
| `.allforai/verify/screens/delete-confirm-running-wide.png` | delete-confirm-running / wide | fail | Readable continuation-to-library sentence in contained dialog; Cancel focus not visually distinct: 007. |
| `.allforai/verify/screens/delete-confirm-running-narrow.png` | delete-confirm-running / narrow | fail | Readable continuation-to-library sentence in contained dialog; Cancel focus not visually distinct: 007. |
| `.allforai/verify/screens/library-after-delete-wide.png` | library-after-delete / wide | fail | Retained image listed, selected and previewed without breakage; forbidden seed metadata visible: 005. |
| `.allforai/verify/screens/library-after-delete-narrow.png` | library-after-delete / narrow | fail | Retained image listed, selected and previewed without breakage; forbidden seed metadata visible: 005. |
| `.allforai/verify/screens/session-list-load-failed-wide.png` | session-list-load-failed / wide | pass | Readable list-load error with retry; disabled-looking generate and 会话还没加载好 status; no unexplained blank list. |
| `.allforai/verify/screens/session-list-load-failed-narrow.png` | session-list-load-failed / narrow | pass | Readable list-load error with retry; disabled-looking generate and 会话还没加载好 status; no unexplained blank list. |
| `.allforai/verify/screens/corrupt-session-wide.png` | corrupt-session / wide | pass | Highlighted corrupted row with file-damaged metadata and only trash control; explanatory timeline and disabled-looking generate with recovery direction. |
| `.allforai/verify/screens/corrupt-session-narrow.png` | corrupt-session / narrow | pass | Highlighted corrupted row with file-damaged metadata and only trash control; explanatory timeline and disabled-looking generate with recovery direction. |
| `.allforai/verify/screens/verify-four-attempts-wide.png` | verify-four-attempts / wide | pass | Sidebar reports four attempts; visible cards show 768×512 · 20步 and last attempt expanded. Earlier attempts outside viewport; narrow actions absent: 003. |
| `.allforai/verify/screens/verify-four-attempts-narrow.png` | verify-four-attempts / narrow | fail | Sidebar reports four attempts; visible cards show 768×512 · 20步 and last attempt expanded. Earlier attempts outside viewport; narrow actions absent: 003. |
| `.allforai/verify/screens/verify-switch-back-wide.png` | verify-switch-back / wide | pass | B highlighted, both visible attempts have B prompts; no A attempt shown. Narrow action labels below viewport: 003. |
| `.allforai/verify/screens/verify-switch-back-narrow.png` | verify-switch-back / narrow | fail | B highlighted, both visible attempts have B prompts; no A attempt shown. Narrow action labels below viewport: 003. |
| `.allforai/verify/screens/verify-after-delete-wide.png` | verify-after-delete / wide | pass | Only 留下来的会话 remains highlighted; its image and both actions fully visible. |
| `.allforai/verify/screens/verify-after-delete-narrow.png` | verify-after-delete / narrow | pass | Only 留下来的会话 remains highlighted; its image and both actions fully visible. |
| `.allforai/verify/screens/verify-failed-and-cancelled-wide.png` | verify-failed-and-cancelled / wide | pass | First card shows red failure / 内存不足，生成被中止; second gray cancelled card expanded with both actions; no broken/blank image. |
| `.allforai/verify/screens/verify-failed-and-cancelled-narrow.png` | verify-failed-and-cancelled / narrow | pass | First card shows red failure / 内存不足，生成被中止; second gray cancelled card expanded with both actions; no broken/blank image. |

---

<!-- verbatim: visual-review-2-batch-B-real-app.md -->
# Independent visual review 2 — batch-B-real-app

Inspected all 20 listed screenshots directly as images. failed_visual_review: 5 major issues, 1 minor and 2 notes; 7 screenshots fail and 13 pass their assigned visual checks (including warnings). No missing or unreadable screenshots. No evidence JSON or other reviewers’ reports were read.

Reviewer: reviewer-2 · codex exec · GPT-6. Every listed PNG was opened using the image-viewing tool. Judgments are based on visible pixels and the supplied criteria. No prohibited review/reconciliation/audit files were opened.

## Blockers

None.

## Majors

### R2-batch-B-real-app-001 — missing_required_element

Criteria: attempt-selected-actions / D-72, D-74, D-86; AC-7; batch visual question 2

Screenshots:

- `.allforai/verify/evidence/real/real-attempt-selected-actions-wide.png`
- `.allforai/verify/evidence/real/real-attempt-selected-actions-narrow.png`

Observation: Both screenshots show an expanded lighthouse image but neither action button. The attempt header is above the visible timeline area, so its number cannot be verified. In narrow, the image bottom is also cut off at the timeline/composer boundary. Wide shows the full large image, but still no actions.

Repair suggestion: Size the expanded image against the available timeline height and keep the actions visible; scroll the selected card into an appropriate position. Re-capture both widths showing the attempt identity, complete image and both complete action labels. This evidence does not establish whether the buttons exist farther down the scroll area.

### R2-batch-B-real-app-002 — missing_required_element

Criteria: timeline-three-rounds / D-71–D-74; AC-1, AC-2, AC-7

Screenshots:

- `.allforai/verify/evidence/real/real-timeline-three-rounds-wide.png`
- `.allforai/verify/evidence/real/real-timeline-three-rounds-narrow.png`

Observation: Attempt 1 is mostly above the timeline viewport: only the bottom of its thumbnail/card is visible. Attempts 2 and 3 have real lighthouse thumbnails and readable metadata, but attempt 3’s expanded image extends below the viewport, and its detailed prompt, advanced-parameter control and both actions are not visible. The required three-card sequence and expanded-card contents are not fully demonstrated.

Repair suggestion: Arrange or size the three-round state to show the required sequence and expanded controls at both widths; provide complementary scroll-position screenshots if the full state cannot fit. Do not use DOM records as a substitute for missing visual evidence.

### R2-batch-B-real-app-003 — missing_required_element

Criteria: attempt-cancelled / D-84, D-85; AC-7

Screenshots:

- `.allforai/verify/evidence/real/real-attempt-cancelled-narrow.png`

Observation: Attempt 5 visibly has an 已取消 badge and a grey X icon block, with no broken image or running indicator. Its lower text is cut at the timeline boundary and both required actions are outside the captured area. The wide counterpart does show both actions.

Repair suggestion: After resizing, bring the expanded cancelled card fully into view or reduce its vertical footprint; re-capture narrow with its explanatory text and both actions visible.

### R2-batch-B-real-app-004 — seed_word_in_main_flow

Criteria: Global rules: no visible 种子 except inside expanded 高级参数; batch visual question 4

Screenshots:

- `.allforai/verify/evidence/real/real-library-after-delete-wide.png`
- `.allforai/verify/evidence/real/real-library-after-delete-narrow.png`

Observation: Library metadata visibly includes 种子 889538739 for the bamboo image and 种子 1248066557 for the cancelled attempt; wide also shows another seed on a lower row. These are plain list metadata, not an expanded advanced-parameter block. The supplied global rule explicitly applies to every screenshot and gives no library exception.

Repair suggestion: Move seed metadata into expanded advanced parameters in the library as well, or obtain an explicit acceptance-standard scope revision before re-review. Under the current standard these screenshots fail.

### R2-batch-B-real-app-005 — missing_required_element

Criteria: library-after-delete / D-30; AC-5: 图片页会话列表里已无该会话

Screenshots:

- `.allforai/verify/evidence/real/real-library-after-delete-wide.png`
- `.allforai/verify/evidence/real/real-library-after-delete-narrow.png`

Observation: The bamboo image is visibly rendered and listed with its matching title, satisfying the preview portion. Neither library screenshot shows the image-page session list, so the required absence of the deleted session is not visually demonstrated. This is an evidence gap, not a claim that deletion failed.

Repair suggestion: Add paired post-deletion image-page screenshots showing the remaining session list, alongside the library preview, and include them in the acceptance batch for inspection.


## Minors

### R2-batch-B-real-app-006 — missing_required_element

Criteria: delete-confirm / D-90; required 取消 focus

Screenshots:

- `.allforai/verify/evidence/real/real-delete-confirm-wide.png`
- `.allforai/verify/evidence/real/real-delete-confirm-narrow.png`

Observation: The modal title, image-retention wording and red 删除 action are clear and fit both widths. However, 取消 has no distinct visible focus indicator; a strong blue outline remains visible around the background session item. Pixels alone cannot establish the actual focused DOM element.

Repair suggestion: Ensure initial focus moves to 取消 and give it a visible keyboard-focus indicator; capture that state. Verify focus behavior separately rather than infer it from these screenshots.


## Notes

### R2-batch-B-real-app-007 — evidence_limit

Criteria: refine-prefill; AC-3; global rules

Screenshots:

- `.allforai/verify/evidence/real/real-refine-prefill-wide.png`
- `.allforai/verify/evidence/real/real-refine-prefill-narrow.png`
- `.allforai/verify/evidence/real/real-after-restart-wide.png`
- `.allforai/verify/evidence/real/real-after-restart-narrow.png`

Observation: Refine screenshots show a focused, prefilled prompt matching attempt 2, an 沿用第 2 次的构图 chip with ×, and collapsed composer advanced parameters. Restart screenshots show both sessions, restored lighthouse thumbnails and cancelled attempt 5. These are visual observations; ARIA values, persistence causality, naturalWidth and exact scroll metrics cannot be proved from pixels. Normal clipping at a scroll-container boundary is not by itself evidence of overlapping DOM regions.

Repair suggestion: Retain these visual checks and verify semantic attributes and restart causality separately. Do not treat the known missing document scrollbar in WKWebView snapshots as a defect.

### R2-batch-B-real-app-008 — status_inconsistency

Criteria: running-other-session; global status consistency

Screenshots:

- `.allforai/verify/screens-recapture/running-other-session-wide.png`
- `.allforai/verify/screens-recapture/running-other-session-narrow.png`

Observation: Both harness screenshots correctly show A as generating, B selected with a completed gradient image, a named busy message, 回到该会话, enabled refine styling and disabled generate/recompose styling. The top global strip nevertheless says 媒体：空闲 and 可开工, contradicting the session-level busy state.

Repair suggestion: Make the harness supply consistent global busy status, then confirm the same consistency with real-app evidence; the screenshots alone do not show whether this discrepancy exists outside the harness.

## Per-screenshot inspection

Pass means the assigned visual state is supported, subject to the listed minor warnings and evidence limits. Fail includes missing required visual evidence; it does not assert an unobserved implementation defect.

- **PASS** `.allforai/verify/evidence/real/real-running-wide.png` — state `real-running`, wide. Running attempt 1, progress bar, cancel, collapsed log, session generating marker, disabled-looking generate and correct current-session status are visible; no image placeholder or attempt actions.
- **PASS** `.allforai/verify/evidence/real/real-running-narrow.png` — state `real-running`, narrow. Running attempt 1, progress bar, cancel, collapsed log, session generating marker, disabled-looking generate and correct current-session status are visible; no image placeholder or attempt actions.
- **PASS** `.allforai/verify/evidence/real/real-refine-prefill-wide.png` — state `real-refine-prefill`, wide. Attempt 2 prompt matches the focused composer; composition chip and × are visible; advanced parameters stay collapsed and there is no new running card. Expanded image continues within a scrollable timeline.
- **PASS** `.allforai/verify/evidence/real/real-refine-prefill-narrow.png` — state `real-refine-prefill`, narrow. Attempt 2 prompt matches the focused composer; composition chip and × are visible; advanced parameters stay collapsed and there is no new running card. Expanded image continues within a scrollable timeline.
- **FAIL** `.allforai/verify/evidence/real/real-timeline-three-rounds-wide.png` — state `real-timeline-three-rounds`, wide. FAIL: attempt 1 is mostly outside the viewport; attempt 3 details and both actions are not visible. Visible thumbnails render real lighthouse pictures.
- **FAIL** `.allforai/verify/evidence/real/real-timeline-three-rounds-narrow.png` — state `real-timeline-three-rounds`, narrow. FAIL: attempt 1 is mostly outside the viewport; attempt 3 details and both actions are not visible. Visible thumbnails render real lighthouse pictures.
- **FAIL** `.allforai/verify/evidence/real/real-attempt-selected-actions-wide.png` — state `real-attempt-selected-actions`, wide. FAIL: both actions and the attempt header are outside the captured area. Wide shows a full lighthouse image; narrow cuts off its bottom.
- **FAIL** `.allforai/verify/evidence/real/real-attempt-selected-actions-narrow.png` — state `real-attempt-selected-actions`, narrow. FAIL: both actions and the attempt header are outside the captured area. Wide shows a full lighthouse image; narrow cuts off its bottom.
- **PASS** `.allforai/verify/evidence/real/real-attempt-cancelled-wide.png` — state `real-attempt-cancelled`, wide. Cancelled badge and grey X block are visible, with no image placeholder or running state. Wide shows both actions; narrow hides the lower expanded contents and both actions.
- **FAIL** `.allforai/verify/evidence/real/real-attempt-cancelled-narrow.png` — state `real-attempt-cancelled`, narrow. Cancelled badge and grey X block are visible, with no image placeholder or running state. Wide shows both actions; narrow hides the lower expanded contents and both actions.
- **PASS** `.allforai/verify/evidence/real/real-after-restart-wide.png` — state `real-after-restart`, wide. Two sessions remain visible; the lighthouse session is selected with five attempts counted. Attempts 3 and 4 show real thumbnails; attempt 5 is cancelled. Earlier attempts are outside the scroll viewport. Narrow clips lower expanded contents, but the assigned AC-3 visual persistence check is supported.
- **PASS** `.allforai/verify/evidence/real/real-after-restart-narrow.png` — state `real-after-restart`, narrow. Two sessions remain visible; the lighthouse session is selected with five attempts counted. Attempts 3 and 4 show real thumbnails; attempt 5 is cancelled. Earlier attempts are outside the scroll viewport. Narrow clips lower expanded contents, but the assigned AC-3 visual persistence check is supported.
- **PASS** `.allforai/verify/evidence/real/real-delete-confirm-wide.png` — state `real-delete-confirm`, wide. Correct modal title and retention wording, fully visible buttons and danger styling. Cancel focus is not visually distinguishable; minor warning.
- **PASS** `.allforai/verify/evidence/real/real-delete-confirm-narrow.png` — state `real-delete-confirm`, narrow. Correct modal title and retention wording, fully visible buttons and danger styling. Cancel focus is not visually distinguishable; minor warning.
- **FAIL** `.allforai/verify/evidence/real/real-library-after-delete-wide.png` — state `real-library-after-delete`, wide. FAIL: real bamboo image and matching library row render, but seeds appear in plain metadata and post-deletion session-list absence is not shown.
- **FAIL** `.allforai/verify/evidence/real/real-library-after-delete-narrow.png` — state `real-library-after-delete`, narrow. FAIL: real bamboo image and matching library row render, but seeds appear in plain metadata and post-deletion session-list absence is not shown.
- **PASS** `.allforai/verify/screens-recapture/running-other-session-wide.png` — state `running-other-session`, wide. B selected with its finished gradient image; A has generating marker; named busy status and return action visible; generate/recompose look disabled and refine enabled. Top global status is inconsistent (note).
- **PASS** `.allforai/verify/screens-recapture/running-other-session-narrow.png` — state `running-other-session`, narrow. B selected with its finished gradient image; A has generating marker; named busy status and return action visible; generate/recompose look disabled and refine enabled. Top global status is inconsistent (note).
- **PASS** `.allforai/verify/screens-recapture/model-missing-wide.png` — state `model-missing`, wide. Missing-image-model message is visible in header and status line; generate looks disabled; selected empty session, composer and collapsed advanced parameters fit.
- **PASS** `.allforai/verify/screens-recapture/model-missing-narrow.png` — state `model-missing`, narrow. Missing-image-model message is visible in header and status line; generate looks disabled; selected empty session, composer and collapsed advanced parameters fit.
