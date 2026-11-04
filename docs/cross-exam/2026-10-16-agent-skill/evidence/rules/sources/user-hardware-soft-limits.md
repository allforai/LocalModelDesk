---
name: feedback-hardware-soft-limits
description: "Design for varied Mac RAM sizes, but memory checks are soft warnings (confirmable), never hard blocks — macOS virtual memory absorbs overshoot"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 800d7e09-a8ce-4998-bda6-2f47d3adbe63
  modified: 2026-09-24T16:26:31.138Z
---

New features must work across different hardware (36 GB → 512 GB Macs), but memory checks must stay lenient: estimate → "内存可能不足 / 仍要生成" confirm with force, never a new hard rejection, never hide features by hardware.

**Why:** user (2026-09-25) — "要考虑不同的硬件，但是不要太严格，因为有虚拟内存". Swap makes overshoot slow, not fatal.

**How to apply:** new job kinds plug into `memory_estimate.estimate_bytes` soft-warning path; ffmpeg-only jobs skip memory checks; don't cap chain lengths for memory reasons. Related: [[project-visual-baseline-direction]]
