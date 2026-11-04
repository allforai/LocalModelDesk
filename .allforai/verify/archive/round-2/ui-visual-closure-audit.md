# Image sessions — visual closure audit, round 2

Auditor: reviewer-1 (claude -p, fresh context) · Reconciliation: `.allforai/verify/ui-visual-reconciliation.json`

**Closure status: OPEN**. The union has one major (B-01).

## Checks

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Both independent reports exist and neither read the other before writing | **pass** | `visual-review-1.*` (claude -p) and `visual-review-2.*` (codex exec) both exist. `run_reviewer.sh` uses separate backends, and `reviewer-prompt.txt` forbids opening other visual-review-* files, reconciliations, audits and archive/. Batch files were written concurrently (A: 09:34–09:36; B: 09:46–09:47). Neither report cites the other, and their conclusions differ materially. Limit: independence rests on prompt compliance; tool-call logs were not audited. |
| 2 | Every required state × viewport in the manifest was inspected by both reviewers | **pass** | The manifest has 38 coverage entries (19 states × 2), all marked `inspected_by_both: true`. `missing_required` and `not_inspected_by_both` are both empty. Each reviewer lists all 76 PNGs (54 harness, 22 real) with a verdict for each. |
| 3 | Every issue cites screenshots that exist | **pass** | All 54 `screens/*.png` and 22 `evidence/real/real-*.png` files exist, and every cited path is among them. The reconciler opened 8 directly. |
| 4 | Every blocking issue is routed to a repair owner | **pass** | B-01: visual_quality_gaps, owned by image-session-repair (plus a contract follow-up). N-01…N-07 each carry a category and an owner. |
| 5 | Round-1 blocking items were repaired, re-captured and re-reviewed in this round | **pass** | U-01 through U-08 were all re-captured and passed by both reviewers (details below). |
| 6 | No blocker/major remains in the union this round | **fail** | B-01 (major) remains open. |

## Round-1 blocking items

| Item | Round-1 problem | Round 2 |
|---|---|---|
| U-01 | Timeline not scrolled to the expanded card's actions at 900×700 | Closed. Actions are visible on every expanded narrow card. |
| U-02 | Expanded card with a real-size image taller than the timeline | Closed, but the fix caused regression **B-01**. |
| U-03 | No capture of the whole three-round timeline | Closed. Top/bottom pairs are declared in both batches. |
| U-04 | Cancelled card had no explanation line | Closed. `real-attempt-cancelled-wide` shows 这次生成被手动停止. |
| U-05 | No image-page capture after delete in the real app | Closed. `real-after-delete-*` shows only the lighthouse session; the deleted session's GET returns 404. |
| U-06 | 种子 in 素材库 | Closed by contract: 素材库 metadata is exempt under D-50a. |
| U-07 / U-08 | Fixture preconditions | Re-captured and passed. |

## Open items

### B-01 — major — visual_quality_gaps → image-session-repair

At 900×700 the expanded card's 大图 is shrunk to fit the timeline:

- `busy-other-media-narrow`: 96px, the same size as the thumbnail directly above it.
- `verify-selected-full-size-narrow`: about 110px, for a 1024×1024 image.
- `real-attempt-selected-actions-narrow`: about 149 vs 96 CSS px.

The card also repeats the thumbnail and the full prompt. 10 narrow harness screenshots are affected, plus the real narrow ones.

**Disagreement:** reviewer 1 rated this major and reviewer 2 a note, since the criteria set a maximum but no minimum. It is kept at major under the union rule, and I agree after opening the screenshots.

**Exit condition:**
- When a card is expanded, hide the header thumbnail and the full header prompt.
- Give the large image a floor (≈240px, or at least 2× the thumbnail) at 900×700, with the actions still reachable.
- Add an e2e assertion for this.
- Re-capture the narrow states in both batches, then run a round-3 double review.

### B-01-contract — follow-up — contract_gaps → image-session-repair

Add a minimum rendered size for the expanded 大图 to `visual-acceptance-criteria.md/.json` (attempt-selected-actions, timeline-three-rounds).

## Non-blocking (tracked, not gating)

- **N-01 (minor)**: in the real app's delete dialog, 取消 has no visible focus ring. The harness (Chromium) shows one.
- **N-02 (minor)**: the session title is cut to 3–4 characters beside 生成中. Carried over from round 1.
- **N-03 (minor)**: 新会话 touches the first list item.
- **N-04 to N-07 (notes)**:
  - The composer draft is shared across sessions.
  - Copy nits.
  - The trash button is red at rest.
  - Evidence-framing gaps: library tab bar, single-session rename, and the journey probe not reading the cancelled reason.
