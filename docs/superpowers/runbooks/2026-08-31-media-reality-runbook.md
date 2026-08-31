# Media real-generation acceptance

This is a human-only reality gate and uses the real H3/Music 3 weights and output directory.

1. Generate a five-second video. Confirm progress/log growth, a playable MP4 with sound, a complete history record, and an idle arbiter afterward.
2. While video generation is active, attempt chat-model loading and confirm rejection with `media_busy`.
3. Generate a 30-second song. Confirm a playable WAV and a complete music history record.
4. Start another video and cancel after logs begin. Confirm the process group exits, terminal state is `cancelled`, history records cancellation, and the arbiter becomes idle.
5. Record dates, output filenames, history ids, API responses, and observations in
   `docs/superpowers/runs/2026-08-31-localmodeldesk-app/signoffs/media-reality.md`.
6. Only when every check passes, add a standalone line: `VERDICT: PASS`.
