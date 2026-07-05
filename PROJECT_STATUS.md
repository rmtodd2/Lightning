# Project Status

## 🔴 User Action Required

No user action required right now.

---

## Current Goal

Improve accuracy after real output examples showed bright rain/cloud shafts could outscore true lightning under the static bolt detector.

---

## Current State

Lightning is a PySide6 desktop app that scans supported video files in a selected folder and saves likely lightning frames as `.jpg` files. The detector now combines whole-frame brightness deltas, localized 6x8 region activity, temporal contrast, and stricter visible bolt-channel scoring.

---

## Recently Completed

- Migrated the GUI from Tkinter to PySide6.
- Confirmed supported video matching includes uppercase `.MOV` through case-insensitive extension checks.
- Added region-based flash scoring.
- Added temporal spike filtering to reduce gradual exposure-change false positives.
- Added static bolt-structure detection after real screenshot examples showed visible bolts with saturated peak brightness and weak temporal gates.
- Tightened static bolt detection to require narrow high-contrast channel components, reducing false positives from bright cloud texture and rain shafts.
- Updated `README.md` and `requirements.txt`.

---

## Decisions Made

- Do not add sky cropping or masking at this stage.
- Keep the existing single threshold UI so the app stays simple.
- Keep a built-in minimum static-bolt score and high-contrast channel gate so very low user thresholds do not turn bright cloud texture into detections.
- Preserve batch-folder processing and direct output into the selected output folder.

---

## Known Issues / Risks

- `.MOV` decoding still depends on the codecs available to OpenCV/FFmpeg on the user's machine.
- Threshold tuning may need real video samples because region and bolt scoring change score distribution.
- Static bolt detection adds per-frame image analysis work and may be slower on long/high-resolution videos.
- Very high thresholds can still miss real lightning because the score is not a percentage; start near `6.0` and tune upward.
- The app does not yet create a CSV report, so reviewing large batches depends on output filenames.

---

## 🤖 Codex Next Steps

- Add optional CSV detection reporting with video name, frame number, score, region activity, and temporal contrast.
- Add optional per-video output subfolders.
- Add a small automated test module for supported extension filtering and synthetic flash detection.
- Add a lightweight debug report option that records rejected-frame max scores for threshold tuning.
- Consider showing the active detector settings in an About or details dialog.

---

## Files / Areas To Know

- `Lightning1.py`: PySide6 window and thread-safe UI signal bridge.
- `Lightning1_support.py`: video filtering, validation, detector scoring, and frame saving.
- `README.md`: user-facing setup, usage, notes, and suggested improvements.
- `requirements.txt`: runtime Python dependencies.

---

## Last Updated

2026-07-05
