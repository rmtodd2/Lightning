# Lightning

Lightning is a small PySide6 desktop utility for extracting likely lightning frames from slow-motion video files.

In slow-motion footage a single flash persists across many consecutive frames, so simple frame-to-frame differencing sees almost nothing. Instead, the detector maintains a slowly-adapting background model of the scene (frozen while lightning is visible) and looks for two kinds of evidence against it:

- **Bolt structure**: thin, elongated, high-contrast bright channels, measured with orientation-independent geometry (rotated-rect extent, stroke width, thinness) so vertical, diagonal, and branched bolts all qualify. Every bolt pixel must also be *novel* — much brighter than the background model — which rejects static bright objects such as fence posts, antennas, building trim, and bright sky gaps between power lines. A ridge test rejects the bright edges of wide bands (rain shafts, cloud gaps), which are steps rather than thin channels.
- **Broad flash**: a large share of the frame suddenly brightening well above the background. Entering a flash event requires a fast onset (a mean-brightness jump within a few frames), which gradual exposure changes never produce, and the brightening must not be matched by darkening (which would indicate camera motion instead of lightning).

Handheld footage is supported: the background model tracks camera drift each frame using phase correlation, and two per-component tests reject the motion artifacts that remain — a *counter-shadow* test (a dark edge that moved leaves a bright sliver with a matching dark sliver beside it; lightning darkens nothing) and a *revealed-scenery* test (sky exposed by camera tilt at a treeline is never brighter than the sky beside it, while a bolt over dark background always is).

Every detected lightning frame is saved as a `.jpg` in the selected output folder. This is intentionally exhaustive, so a single flash may produce multiple adjacent saved frames if the lightning remains visible across frames.

## Features

- Desktop GUI built with PySide6
- Batch processes videos from a selected folder
- Supports `.MOV`, `.mov`, `.mp4`, `.avi`, and `.m4v` input files
- Adjustable lightning sensitivity threshold
- Background-model detection built for slow-motion footage (a flash is compared to the pre-flash scene, not the previous frame)
- Orientation-independent bolt-channel detection that handles vertical, diagonal, and branched bolts
- Pixel-level novelty check so static bright objects can never register as bolts
- Sudden-onset and one-sided-brightening gates that reject gradual exposure changes and camera bumps
- Saves every detected lightning frame instead of only the strongest frame in an event
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

Lower threshold values catch more flash events. `6.0` is a reasonable starting point. A clearly-shaped bolt channel is treated as proof by itself and is saved even when the threshold is set high; the threshold mainly tunes how much broad-flash and faint-bolt evidence is required.

## Project Structure

- `Lightning1.py`: PySide6 GUI layout and startup entry point
- `Lightning1_support.py`: application logic for folder selection, processing, and frame extraction
- `lightning_detector.py`: the detection algorithm (background model, bolt geometry, flash gates)
- `Lightning.ico`: application icon asset

## Notes

- Supported video extensions are matched case-insensitively, so `.MOV` files are included.
- `.MOV` decoding depends on the codecs available through OpenCV/FFmpeg on your platform.
- The threshold is a detector score, not a percentage. It mainly tunes broad-flash and faint-bolt sensitivity; strong visible bolt-channel detections are saved even when the threshold is set high.
- Handheld videos with slow pans and drift are handled by motion compensation; very fast whips or large rotations may still reduce accuracy while they last.
- The very first frame of each video is used to initialize the background model and is never saved.
- Frames are saved directly into the selected output folder; they are not grouped into per-video subfolders.
- Output filenames include the frame number, total score, flash rise over background (`flash`), share of flash-lit pixels (`area`), bolt-structure score (`bolt`), and bolt component count (`comps`) for quick review.

## Suggested Improvements

- Add a dry-run preview mode that lists detected events without saving frames.
- Add optional per-video output subfolders to keep large batches easier to review.
- Save a CSV detection report with video name, frame number, score, and brightness metrics.
- Add a recursive input-folder option for cameras that create dated subfolders.
- Add a small sample-video test set for tuning thresholds across different cameras.
