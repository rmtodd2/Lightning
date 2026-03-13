# Lightning

Lightning is a small Tkinter desktop utility for extracting bright frames from video files.

The application scans each video in an input folder, tracks the darkest frame seen so far, and saves frames whose brightness is greater than or equal to:

`darkest_frame_brightness * threshold`

Saved frames are written as `.jpg` files to the selected output folder, and the filename includes the source video name, frame number, and brightness metadata.

## Features

- Desktop GUI built with Tkinter
- Batch processes videos from a selected folder
- Supports `.MOV` and `.mp4` input files
- Adjustable brightness threshold
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
3. Enter a detection threshold.
4. Click `Start`.

Higher threshold values save fewer frames because a frame must be much brighter than the darkest frame observed so far to be written out.

## Project Structure

- `Lightning1.py`: PAGE-generated Tkinter GUI layout and startup entry point
- `Lightning1_support.py`: application logic for folder selection, processing, and frame extraction
- `Lightning.ico`: application icon asset

## Notes

- The UI was generated with PAGE and uses Tkinter widgets.
- The current file matching is case-sensitive and only processes files ending in `.MOV` or `.mp4`.
- Frames are saved directly into the selected output folder; they are not grouped into per-video subfolders.
