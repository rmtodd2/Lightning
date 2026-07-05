# Project Status

## 🔴 User Action Required

No user action required right now.

---

## Current Goal

Improve Lightning's video detector beyond whole-frame brightness checks while avoiding crop or mask workflows.

---

## Current State

Lightning is a PySide6 desktop app that scans supported video files in a selected folder and saves likely lightning frames as `.jpg` files. The detector now combines whole-frame brightness deltas, localized 6x8 region activity, and temporal contrast against the frame-to-frame baseline.

---

## Recently Completed

- Migrated the GUI from Tkinter to PySide6.
- Confirmed supported video matching includes uppercase `.MOV` through case-insensitive extension checks.
- Added region-based flash scoring.
- Added temporal spike filtering to reduce gradual exposure-change false positives.
- Updated `README.md` and `requirements.txt`.

---

## Decisions Made

- Do not add sky cropping or masking at this stage.
- Keep the existing single threshold UI so the app stays simple.
- Preserve batch-folder processing and direct output into the selected output folder.

---

## Known Issues / Risks

- `.MOV` decoding still depends on the codecs available to OpenCV/FFmpeg on the user's machine.
- Threshold tuning may need real camera samples because region scoring changes score distribution.
- The app does not yet create a CSV report, so reviewing large batches depends on output filenames.

---

## 🤖 Codex Next Steps

- Add optional CSV detection reporting with video name, frame number, score, region activity, and temporal contrast.
- Add optional per-video output subfolders.
- Add a small automated test module for supported extension filtering and synthetic flash detection.
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
