# Project Status

## 🔴 User Action Required

Re-run the app on IMG_4818 (and other storm videos) to confirm today's fixes: frames 42-47 should no longer be saved at any threshold, and the real lightning frames (2397-2399) should still be saved. See "Tuning guide" below if you still see false positives or miss real strikes.

---

## Current Goal

Validate the straightness-filtered, threshold-linked detector on real handheld slow-motion storm footage.

---

## Current State

Lightning is a PySide6 desktop app that scans supported video files in a selected folder and saves likely lightning frames as `.jpg` files.

The detection core was rewritten into `lightning_detector.py` around a slowly-adapting background model (frozen while lightning is visible), replacing the previous stack of frame-to-frame and texture heuristics. Two evidence paths:

- **Bolt structure**: thin/elongated/high-contrast bright channels with orientation-independent geometry (rotated-rect extent, distance-transform stroke width, thinness, straightness). Pixel-level novelty against the background model excludes static bright objects before component analysis, a ridge test rejects bright edges of wide bands (rain shafts, cloud gaps, sky between power lines), and a straightness test rejects long dead-straight scene edges (power lines, rooflines) left over from imperfect motion compensation. A structurally strong bolt is saved on much weaker corroboration than a broad flash needs, but that "strong" bar now scales with the user's threshold rather than being fixed.
- **Broad flash**: large one-sided brightening over the background with a required sudden onset, so gradual exposure changes and camera bumps never fire.

---

## Recently Completed

- Diagnosed why frames 42-47 kept saving even at threshold 200 (`Images/` folder, saved by the user's own test run): `BOLT_STRONG_SCORE` was a hardcoded 20.0, completely bypassing `self.threshold` in `_decide()`. Those frames' bolt scores (83-146) came from a power-line-edge alignment artifact spanning ~75-95% of the frame width - a long, dead-straight sliver whose score is unbounded because the scoring formula rewards raw length with no cap. No threshold value could ever have filtered it out; this is why "the threshold setting doesn't seem to do anything" was a real bug, not user error.
- Fixed it two ways in `lightning_detector.py`:
  1. **Straightness/wander test** (new, in `_score_bolt_structure`): rejects a component when it both spans a large share of the frame (`BOLT_MAX_STRAIGHT_SPAN_FRACTION`, default 50%) and is essentially as wide as its own stroke (`bounding_short_side / channel_width < BOLT_MIN_WANDER`, default 2.0). Confirmed with synthetic tests: a full-width straight artifact measures wander ~0.4 and now scores 0; a dramatic zigzag bolt measures ~6.5 and a subtly-curving one ~2.8 - both still detected. This is a geometric fix, not a threshold change, so it also protects any future scene-edge artifact (rooflines, horizons) regardless of what threshold the user picks.
  2. **Threshold now actually reaches the bolt-structure path**: `BOLT_STRONG_SCORE` and `BOLT_SUPPORT_SCORE` are scaled by `self.threshold / DEFAULT_THRESHOLD` in `_decide()`, so raising the GUI threshold raises the bar for *every* detection path, not just broad-flash. `DEFAULT_THRESHOLD` now lives in `lightning_detector.py` as the single source of truth (GUI default in `Lightning1_support.py` imports it instead of duplicating `6.0`).
- Earlier handheld-camera-motion fixes (unchanged): per-frame background alignment via phase correlation, per-component counter-shadow test for moving dark edges, revealed-scenery test for sky exposed at dark boundaries.
- Found and worked around an OpenCV 5.0 bug/behavior: `cv2.phaseCorrelate` with a window argument mutates BOTH input arrays in-place - inputs must be copies.
- Removed the global darkened-area gate from the bolt path (the per-component tests are more precise; the global gate blocked real bolts filmed during a pan).
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
- Strong bolt structure needs much less flash corroboration than a broad flash does, but that bar scales with the user threshold (`sensitivity = threshold / DEFAULT_THRESHOLD` in `_decide()`) instead of being a fixed constant — a fixed bypass constant is what let the threshold field look like a no-op.
- A component is judged a straight scene-edge artifact, not a bolt, only when it's *both* long (spans a large share of the frame) and dead-straight (bounding box barely wider than its own stroke) — short straight segments are still allowed, since a real bolt stub can look nearly straight over a short span.
- Keep the single-threshold UI, batch folder processing, exhaustive frame saving, and direct output into the selected folder.
- Support handheld footage: compensate camera drift by aligning the background model with phase correlation, and reject residual motion artifacts per component (counter-shadow, revealed-scenery) instead of using a global motion gate, which would block real bolts filmed during a pan.

---

## Tuning Guide

The saved filename encodes `score`, `flash`, `area`, `bolt`, `comps`, and `thr` for every detection — that's the first thing to read off a false positive or a miss.

- **Still seeing false positives with a high bolt score:** raising the GUI threshold now helps (it scales the bolt-structure bar too, not just broad-flash), but for a *specific, recurring* false-positive shape it's more reliable to add a geometric rejection like the straightness test than to keep raising the global dial, since a high dial also suppresses real faint bolts. Compare the false positive's `_comps_` and `bolt_` values against real detections to see if it's an outlier shape.
- **A long, straight artifact still gets through:** raise `BOLT_MIN_WANDER` (default 2.0) to demand more visible bend/branching before accepting a component, or lower `BOLT_MAX_STRAIGHT_SPAN_FRACTION` (default 0.5) so shorter artifacts get straightness-checked too. There's headroom to do this: synthetic real-bolt shapes measured wander 2.8-6.5, a synthetic straight artifact measured 0.4.
- **Missing a real, fairly straight bolt:** raise `BOLT_MAX_STRAIGHT_SPAN_FRACTION` toward 1.0 (fewer components get straightness-checked at all) rather than lowering `BOLT_MIN_WANDER`, which would let artifacts back in.
- **Threshold feels too sensitive or not sensitive enough overall:** it now scales three things together (`BOLT_STRONG_SCORE`, `BOLT_SUPPORT_SCORE`, and the flash-support minimums in `_decide()`), so one number tunes both bolt and flash paths consistently. `DEFAULT_THRESHOLD` (6.0) is the reference point those constants were calibrated against — moving it isn't necessary, just move the GUI threshold.
- **False positives from something other than a straight edge** (e.g., a moving bright object, insect near lens, reflection): check `BOLT_NOVELTY_DELTA` (novelty required over background — raise to demand more contrast), `BOLT_MIN_THINNESS`/`BOLT_MAX_CHANNEL_WIDTH` (raise thinness / lower max width to demand a more channel-like shape), and `BOLT_COUNTER_SHADOW_RATIO` (lower to reject more residual-motion artifacts, at the risk of rejecting real bolts near a dark moving edge).
- **Missing real faint bolts generally:** lower the GUI threshold first; if that's not enough, lower `BOLT_SUPPORT_SCORE` or `BOLT_NOVELTY_DELTA` in `lightning_detector.py`.

## Known Issues / Risks

- Constants were calibrated on three real frames plus synthetic scenes; real-video batches may still suggest tuning (all gates are named constants at the top of `lightning_detector.py`, see Tuning Guide above).
- The straightness test only fires above `BOLT_MAX_STRAIGHT_SPAN_FRACTION` (50% of the frame's larger dimension); a shorter straight scene-edge artifact would not be caught by it and would rely on the ridge/revealed-scenery/counter-shadow tests instead.
- `.MOV` decoding still depends on the codecs available to OpenCV/FFmpeg on the user's machine.
- Saving every detected frame can create adjacent near-duplicates from the same flash.
- No CSV report yet; reviewing large batches depends on output filenames.

---

## Next Steps

- Re-test IMG_4818 and other storm videos (user) to confirm frames 42-47 are gone and 2397-2399 are still saved, at a normal threshold and not just 200.
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

2026-07-05 (threshold-linkage + straightness fix)
