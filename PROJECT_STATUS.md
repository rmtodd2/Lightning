# Project Status

## 🔴 User Action Required

Run the app on real storm videos to confirm the new detector's accuracy on your footage. If anything is missed or falsely saved, the frame filename metrics (`flash`, `area`, `bolt`, `comps`) identify which detection path fired.

---

## Current Goal

Validate the rewritten detector on real slow-motion storm footage.

---

## Current State

Lightning is a PySide6 desktop app that scans supported video files in a selected folder and saves likely lightning frames as `.jpg` files.

The detection core was rewritten into `lightning_detector.py` around a slowly-adapting background model (frozen while lightning is visible), replacing the previous stack of frame-to-frame and texture heuristics. Two evidence paths:

- **Bolt structure**: thin/elongated/high-contrast bright channels with orientation-independent geometry (rotated-rect extent, distance-transform stroke width, thinness). Pixel-level novelty against the background model excludes static bright objects before component analysis, and a ridge test rejects bright edges of wide bands (rain shafts, cloud gaps, sky between power lines). Strong bolt structure is saved regardless of threshold.
- **Broad flash**: large one-sided brightening over the background with a required sudden onset, so gradual exposure changes and camera bumps never fire.

---

## Recently Completed

- Rewrote detection into `lightning_detector.py` (background model + bolt geometry + flash gates); `Lightning1_support.py` now only handles GUI wiring, validation, and I/O.
- Validated against the three real captures in the repo: all detected strongly (bolt scores 26–64), including at threshold 25; patched bolt-free versions of the same frames stay quiet.
- Built a synthetic test suite (16 scenarios): exposure ramps, camera bumps, brightening cloud patches, wide bright bands, static thin bright objects, night bolts, branched bolts, back-to-back flashes, saturated flashes — all pass.
- End-to-end test through `process_video` on a synthetic MP4: 16/16 truth frames saved, zero false positives.
- Throttled GUI progress updates to every 15 frames.
- Performance: ~9 ms/frame at 1080p, ~16 ms at 4K.

---

## Decisions Made

- Compare frames to a background model instead of the previous frame — in slow motion a flash persists across frames, so frame-to-frame differencing is structurally blind here.
- Apply the novelty gate per pixel *before* connected components, so static bright structures can neither match nor merge with a real bolt component.
- Never detect on frame 0 (it initializes the background model); the trade-off of missing a video that starts mid-strike was accepted to avoid saving static bright structures.
- Strong bolt structure bypasses the user threshold; the threshold tunes broad-flash and faint-bolt sensitivity.
- Keep the single-threshold UI, batch folder processing, exhaustive frame saving, and direct output into the selected folder.
- Assume a mostly stationary camera; one-sided-brightening gate deliberately suppresses detection during camera motion.

---

## Known Issues / Risks

- Constants were calibrated on three real frames plus synthetic scenes; real-video batches may still suggest tuning (all gates are named constants at the top of `lightning_detector.py`).
- `.MOV` decoding still depends on the codecs available to OpenCV/FFmpeg on the user's machine.
- Saving every detected frame can create adjacent near-duplicates from the same flash.
- No CSV report yet; reviewing large batches depends on output filenames.

---

## Next Steps

- Test on real storm videos (user).
- Optional CSV detection report (video, frame, score, path that fired).
- Optional per-video output subfolders.
- Consider a debug mode that logs near-miss frames (rejected but high score) for threshold tuning.

---

## Files / Areas To Know

- `Lightning1.py`: PySide6 window and thread-safe UI signal bridge.
- `Lightning1_support.py`: GUI wiring, validation, video loop, frame saving.
- `lightning_detector.py`: all detection logic and tunable constants.
- `README.md`: user-facing setup, usage, notes.
- `requirements.txt`: runtime Python dependencies.

---

## Last Updated

2026-07-05
