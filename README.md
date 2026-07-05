# Lightning

Lightning is a small PySide6 desktop utility for extracting likely lightning frames from slow-motion video files.

The application scans each video in an input folder and looks for sudden flash events between consecutive frames. Instead of using only absolute brightness, it scores each frame using:

- rapid increase in average brightness
- rapid increase in peak brightness
- ratio of pixels that brighten sharply from the previous frame
- ratio of very bright pixels
- strongest localized flash activity across a 6x8 region grid
- temporal contrast against the recent frame-to-frame baseline
- visible thin bolt structure inside a single frame

Nearby detections are grouped into a single event, and the strongest frame from each event is saved as a `.jpg` in the selected output folder.

## Features

- Desktop GUI built with PySide6
- Batch processes videos from a selected folder
- Supports `.MOV`, `.mov`, `.mp4`, `.avi`, and `.m4v` input files
- Adjustable lightning sensitivity threshold
- Region-based scoring for localized flashes
- Temporal spike filtering to reduce false positives from gradual exposure changes
- Static bolt-structure detection for visible lightning channels
- Progress indicators for videos and frames
- Cancel button to stop processing

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python Lightning1.py
```

Then:

1. Choose the input folder containing video files.
2. Choose the output folder for extracted frames.
3. Enter a lightning sensitivity threshold.
4. Click `Start`.

Lower threshold values catch more temporal flash events. `6.0` is a reasonable starting point for tuning. Visible bolt detection uses a stricter high-contrast channel score so cloud texture, rain shafts, and bright gaps are less likely to trigger even when the threshold is very low.

## Project Structure

- `Lightning1.py`: PySide6 GUI layout and startup entry point
- `Lightning1_support.py`: application logic for folder selection, processing, and frame extraction
- `Lightning.ico`: application icon asset

## Notes

- Supported video extensions are matched case-insensitively, so `.MOV` files are included.
- `.MOV` decoding depends on the codecs available through OpenCV/FFmpeg on your platform.
- The threshold is a detector score, not a percentage. Very high values can miss real bolts; start near `6.0` and increase only if too many false positives are saved.
- Frames are saved directly into the selected output folder; they are not grouped into per-video subfolders.
- Output filenames include the frame number, detection score, region activity, temporal contrast, and brightness metadata for quick review.

## Suggested Improvements

- Add a dry-run preview mode that lists detected events without saving frames.
- Add optional per-video output subfolders to keep large batches easier to review.
- Save a CSV detection report with video name, frame number, score, and brightness metrics.
- Add a recursive input-folder option for cameras that create dated subfolders.
- Add a small sample-video test set for tuning thresholds across different cameras.
