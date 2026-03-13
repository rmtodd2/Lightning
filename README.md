# Lightning

Lightning is a small Tkinter desktop utility for extracting likely lightning frames from slow-motion video files.

The application scans each video in an input folder and looks for sudden flash events between consecutive frames. Instead of using only absolute brightness, it scores each frame using:

- rapid increase in average brightness
- rapid increase in peak brightness
- ratio of pixels that brighten sharply from the previous frame
- ratio of very bright pixels

Nearby detections are grouped into a single event, and the strongest frame from each event is saved as a `.jpg` in the selected output folder.

## Features

- Desktop GUI built with Tkinter
- Batch processes videos from a selected folder
- Supports `.MOV` and `.mp4` input files
- Adjustable lightning sensitivity threshold
- Progress indicators for videos and frames
- Cancel button to stop processing

## Requirements

- Python 3.9+
- Tkinter support in your Python installation
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

Lower threshold values catch more flashes. `6.0` is a reasonable starting point for tuning.

## Project Structure

- `Lightning1.py`: PAGE-generated Tkinter GUI layout and startup entry point
- `Lightning1_support.py`: application logic for folder selection, processing, and frame extraction
- `Lightning.ico`: application icon asset

## Notes

- The UI was generated with PAGE and uses Tkinter widgets.
- Supported video extensions are `.mov`, `.mp4`, `.avi`, and `.m4v`.
- Frames are saved directly into the selected output folder; they are not grouped into per-video subfolders.
- Output filenames include the frame number and detection score metadata for quick review.
