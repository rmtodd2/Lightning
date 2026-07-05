#! /usr/bin/env python3
#  -*- coding: utf-8 -*-
#

import os
import sys
import threading
from dataclasses import dataclass

import cv2
import numpy as np
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

import Lightning1


SUPPORTED_EXTENSIONS = {".mov", ".mp4", ".avi", ".m4v"}
DEFAULT_THRESHOLD = 6.0
BRIGHT_PIXEL_VALUE = 240
EVENT_GAP_FRAMES = 2
REGION_ROWS = 6
REGION_COLS = 8
MIN_REGION_DIFF_RATIO = 0.025
BOLT_SCORE_NORMALIZER = 500.0
BOLT_TILE_SCORE_NORMALIZER = 80.0
BOLT_MIN_SCORE = 30.0

running = False


@dataclass
class FrameMetrics:
    mean_brightness: float
    peak_brightness: float
    diff_ratio: float
    bright_ratio: float
    region_diff_ratio: float
    active_region_ratio: float
    temporal_contrast: float
    bolt_score: float
    bolt_component_count: int
    bolt_pixel_ratio: float
    score: float


def main(*args):
    """Main entry point for the application."""
    app = QApplication.instance() or QApplication(sys.argv)

    global _top1, _w1
    _w1 = Lightning1.LightningWindow()
    _top1 = _w1
    _w1.input_button.clicked.connect(open_folder_i)
    _w1.output_button.clicked.connect(open_folder_o)
    _w1.start_button.clicked.connect(start_button)
    _w1.cancel_button.clicked.connect(cancel)
    _w1.set_counts(0, 0, 0, 0)
    _w1.set_progress(0, 0)
    _w1.set_status("Idle")
    _w1.threshold.setText(str(DEFAULT_THRESHOLD))
    _w1.show()

    return app.exec()


def cancel():
    global running
    running = False
    _w1.set_status("Cancelling...")


def quit(*args):
    print("Lightning1_support.quit")
    for arg in args:
        print("another arg:", arg)
    sys.stdout.flush()
    sys.exit()


def open_folder_i():
    folder_path = QFileDialog.getExistingDirectory(_w1, "Choose input folder")
    if folder_path:
        _w1.input_path.setText(folder_path)


def open_folder_o():
    folder_path = QFileDialog.getExistingDirectory(_w1, "Choose output folder")
    if folder_path:
        _w1.output_path.setText(folder_path)


def start_button():
    if running:
        return
    validated = validate_inputs()
    if validated is None:
        return
    worker = threading.Thread(target=start_processing, args=(validated,), daemon=True)
    worker.start()


def supported_video_files(folder_path):
    return sorted(
        filename
        for filename in os.listdir(folder_path)
        if os.path.splitext(filename)[1].lower() in SUPPORTED_EXTENSIONS
    )


def validate_inputs():
    input_folder_path = _w1.input_path.text().strip()
    output_folder_path = _w1.output_path.text().strip()
    threshold_text = _w1.threshold.text().strip()

    if not input_folder_path or not os.path.isdir(input_folder_path):
        QMessageBox.critical(_w1, "Lightning", "Choose a valid input folder.")
        return None

    if not output_folder_path or not os.path.isdir(output_folder_path):
        QMessageBox.critical(_w1, "Lightning", "Choose a valid output folder.")
        return None

    try:
        threshold = float(threshold_text)
    except ValueError:
        QMessageBox.critical(_w1, "Lightning", "Threshold must be a number.")
        return None

    if threshold <= 0:
        QMessageBox.critical(_w1, "Lightning", "Threshold must be greater than 0.")
        return None

    video_files = supported_video_files(input_folder_path)
    if not video_files:
        QMessageBox.critical(
            _w1,
            "Lightning",
            "No supported video files were found in the input folder.",
        )
        return None

    return input_folder_path, output_folder_path, threshold, video_files


def preprocess_frame(frame):
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small_frame = cv2.resize(gray_frame, (0, 0), fx=0.25, fy=0.25)
    return cv2.GaussianBlur(small_frame, (5, 5), 0)


def calculate_bolt_features(frame):
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    height, width = gray_frame.shape
    scale = min(1.0, 960 / width)

    if scale < 1.0:
        gray_frame = cv2.resize(
            gray_frame,
            (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_AREA,
        )

    local_average = cv2.GaussianBlur(gray_frame, (31, 31), 0)
    local_contrast = cv2.subtract(gray_frame, local_average)
    bolt_mask = np.where((gray_frame >= 185) & (local_contrast >= 22), 255, 0).astype(
        np.uint8
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 3))
    bolt_mask = cv2.morphologyEx(bolt_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    component_count, _, stats, _ = cv2.connectedComponentsWithStats(bolt_mask, 8)
    raw_score = 0.0
    matching_components = 0

    for component_index in range(1, component_count):
        _, _, component_width, component_height, area = stats[component_index]

        if area < 8 or area > 8000:
            continue

        aspect_ratio = component_height / max(1, component_width)
        fill_ratio = area / max(1, component_width * component_height)

        if component_height >= 18 and aspect_ratio >= 1.2 and fill_ratio <= 0.45:
            matching_components += 1
            raw_score += area * (component_height / 20) * min(aspect_ratio, 8) * (
                1 - fill_ratio
            )

    tile_score = 0.0
    tile_matches = 0

    for y_start in range(0, bolt_mask.shape[0], 40):
        for x_start in range(0, bolt_mask.shape[1], 40):
            tile = bolt_mask[y_start : y_start + 80, x_start : x_start + 80]
            if tile.size == 0:
                continue

            y_pixels, x_pixels = np.where(tile > 0)
            pixel_count = len(x_pixels)
            if pixel_count < 8:
                continue

            tile_width = int(x_pixels.max() - x_pixels.min() + 1)
            tile_height = int(y_pixels.max() - y_pixels.min() + 1)
            density = pixel_count / max(1, tile_width * tile_height)
            aspect_ratio = tile_height / max(1, tile_width)

            if tile_height >= 18 and aspect_ratio >= 1.0 and density <= 0.35:
                tile_matches += 1
                tile_score += pixel_count * (tile_height / 20) * min(aspect_ratio, 8) * (
                    1 - density
                )

    bolt_score = max(
        raw_score / BOLT_SCORE_NORMALIZER,
        tile_score / BOLT_TILE_SCORE_NORMALIZER,
    )
    bolt_pixel_ratio = float(np.mean(bolt_mask > 0))

    return bolt_score, matching_components + tile_matches, bolt_pixel_ratio


def calculate_region_activity(positive_diff, processed_frame, noise_floor):
    diff_mask = positive_diff >= noise_floor
    bright_mask = processed_frame >= BRIGHT_PIXEL_VALUE
    region_diff_ratios = []
    active_regions = 0

    for diff_region_rows, bright_region_rows in zip(
        np.array_split(diff_mask, REGION_ROWS, axis=0),
        np.array_split(bright_mask, REGION_ROWS, axis=0),
    ):
        for diff_region, bright_region in zip(
            np.array_split(diff_region_rows, REGION_COLS, axis=1),
            np.array_split(bright_region_rows, REGION_COLS, axis=1),
        ):
            diff_ratio = float(np.mean(diff_region))
            bright_ratio = float(np.mean(bright_region))
            region_diff_ratios.append(diff_ratio)
            if diff_ratio >= MIN_REGION_DIFF_RATIO or bright_ratio >= 0.01:
                active_regions += 1

    strongest_region = max(region_diff_ratios, default=0.0)
    active_region_ratio = active_regions / (REGION_ROWS * REGION_COLS)

    return strongest_region, active_region_ratio


def calculate_frame_metrics(processed_frame, previous_frame, baseline_noise):
    mean_brightness = float(np.mean(processed_frame))
    peak_brightness = float(np.percentile(processed_frame, 99.7))

    positive_diff = cv2.subtract(processed_frame, previous_frame)
    noise_floor = max(12.0, baseline_noise * 2.5)
    diff_ratio = float(np.mean(positive_diff >= noise_floor))
    bright_ratio = float(np.mean(processed_frame >= BRIGHT_PIXEL_VALUE))
    region_diff_ratio, active_region_ratio = calculate_region_activity(
        positive_diff,
        processed_frame,
        noise_floor,
    )

    return (
        mean_brightness,
        peak_brightness,
        diff_ratio,
        bright_ratio,
        region_diff_ratio,
        active_region_ratio,
    )


def compute_lightning_score(
    current_metrics,
    previous_metrics,
    baseline_delta,
    baseline_peak_delta,
    bolt_features=None,
):
    mean_delta = max(0.0, current_metrics[0] - previous_metrics[0])
    peak_delta = max(0.0, current_metrics[1] - previous_metrics[1])
    bolt_score, bolt_component_count, bolt_pixel_ratio = bolt_features or (0.0, 0, 0.0)

    mean_component = mean_delta / max(1.5, baseline_delta)
    peak_component = peak_delta / max(3.0, baseline_peak_delta)
    temporal_contrast = mean_component * 0.65 + peak_component * 0.35

    score = (
        mean_component * 2.0
        + peak_component * 1.4
        + current_metrics[2] * 22.0
        + current_metrics[3] * 18.0
        + current_metrics[4] * 32.0
        + current_metrics[5] * 10.0
        + bolt_score
    )

    return FrameMetrics(
        mean_brightness=current_metrics[0],
        peak_brightness=current_metrics[1],
        diff_ratio=current_metrics[2],
        bright_ratio=current_metrics[3],
        region_diff_ratio=current_metrics[4],
        active_region_ratio=current_metrics[5],
        temporal_contrast=temporal_contrast,
        bolt_score=bolt_score,
        bolt_component_count=bolt_component_count,
        bolt_pixel_ratio=bolt_pixel_ratio,
        score=score,
    )


def is_lightning_candidate(frame_metrics, previous_metrics, threshold):
    mean_delta = frame_metrics.mean_brightness - previous_metrics[0]
    peak_delta = frame_metrics.peak_brightness - previous_metrics[1]
    broad_flash = frame_metrics.diff_ratio >= 0.01
    regional_flash = (
        frame_metrics.region_diff_ratio >= MIN_REGION_DIFF_RATIO
        and frame_metrics.active_region_ratio >= 1 / (REGION_ROWS * REGION_COLS)
    )
    static_bolt = (
        frame_metrics.bolt_score >= max(BOLT_MIN_SCORE, threshold)
        and frame_metrics.bolt_component_count > 0
    )
    temporal_flash = (
        mean_delta >= 3.0
        and peak_delta >= 8.0
        and frame_metrics.temporal_contrast >= 1.2
        and (broad_flash or regional_flash)
    )

    return frame_metrics.score >= threshold and (static_bolt or temporal_flash)


def save_detected_frame(frame, output_path, video_name, frame_number, frame_metrics, threshold):
    output_frame_path = os.path.join(
        output_path,
        (
            f"{video_name}_frame_{frame_number}"
            f"_score_{frame_metrics.score:.2f}"
            f"_mean_{frame_metrics.mean_brightness:.1f}"
            f"_peak_{frame_metrics.peak_brightness:.1f}"
            f"_diff_{frame_metrics.diff_ratio:.3f}"
            f"_region_{frame_metrics.region_diff_ratio:.3f}"
            f"_temp_{frame_metrics.temporal_contrast:.2f}"
            f"_bolt_{frame_metrics.bolt_score:.2f}"
            f"_thr_{threshold:.2f}.jpg"
        ),
    )
    cv2.imwrite(output_frame_path, frame)


def process_video(input_path, output_path, threshold, video_index, video_total):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return 0

    frame_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    _w1.set_status(f"Processing {os.path.basename(input_path)}")

    ret, previous_frame = cap.read()
    if not ret:
        cap.release()
        return 0

    previous_processed = preprocess_frame(previous_frame)
    previous_metrics = (
        float(np.mean(previous_processed)),
        float(np.percentile(previous_processed, 99.7)),
    )
    baseline_noise = 5.0
    baseline_delta = 3.0
    baseline_peak_delta = 6.0
    frame_count = 0
    saved_count = 0
    event_candidate = None
    event_gap = 0
    video_name = os.path.splitext(os.path.basename(input_path))[0]
    first_metrics = calculate_frame_metrics(
        previous_processed,
        previous_processed,
        baseline_noise,
    )
    first_frame_metrics = compute_lightning_score(
        first_metrics,
        previous_metrics,
        baseline_delta,
        baseline_peak_delta,
        calculate_bolt_features(previous_frame),
    )

    if is_lightning_candidate(first_frame_metrics, previous_metrics, threshold):
        event_candidate = {
            "frame": previous_frame.copy(),
            "frame_number": frame_count,
            "metrics": first_frame_metrics,
        }

    while running:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        processed_frame = preprocess_frame(frame)
        current_metrics = calculate_frame_metrics(
            processed_frame,
            previous_processed,
            baseline_noise,
        )
        frame_metrics = compute_lightning_score(
            current_metrics,
            previous_metrics,
            baseline_delta,
            baseline_peak_delta,
            calculate_bolt_features(frame),
        )
        detected = is_lightning_candidate(frame_metrics, previous_metrics, threshold)

        if detected:
            if event_candidate is None or frame_metrics.score > event_candidate["metrics"].score:
                event_candidate = {
                    "frame": frame.copy(),
                    "frame_number": frame_count,
                    "metrics": frame_metrics,
                }
            event_gap = 0
        elif event_candidate is not None:
            event_gap += 1
            if event_gap > EVENT_GAP_FRAMES:
                save_detected_frame(
                    event_candidate["frame"],
                    output_path,
                    video_name,
                    event_candidate["frame_number"],
                    event_candidate["metrics"],
                    threshold,
                )
                saved_count += 1
                event_candidate = None
                event_gap = 0

        if not detected:
            mean_delta = abs(current_metrics[0] - previous_metrics[0])
            peak_delta = abs(current_metrics[1] - previous_metrics[1])
            baseline_delta = baseline_delta * 0.92 + max(0.5, mean_delta) * 0.08
            baseline_peak_delta = baseline_peak_delta * 0.92 + max(1.0, peak_delta) * 0.08
            baseline_noise = baseline_noise * 0.9 + float(np.std(processed_frame)) * 0.1

        previous_processed = processed_frame
        previous_metrics = (current_metrics[0], current_metrics[1])

        frame_progress = frame_count / frame_total * 100
        video_progress = video_index / video_total * 100
        _w1.set_counts(video_index, video_total, frame_count, frame_total)
        _w1.set_progress(video_progress, frame_progress)

    if event_candidate is not None and running:
        save_detected_frame(
            event_candidate["frame"],
            output_path,
            video_name,
            event_candidate["frame_number"],
            event_candidate["metrics"],
            threshold,
        )
        saved_count += 1

    cap.release()
    _w1.set_progress(video_index / video_total * 100, 100)
    return saved_count


def start_processing(validated):
    global running
    input_folder_path, output_folder_path, threshold, video_files = validated
    running = True
    total_saved = 0
    video_total = len(video_files)
    _w1.set_controls_enabled(False)
    _w1.set_counts(0, video_total, 0, 0)
    _w1.set_progress(0, 0)

    try:
        for video_index, filename in enumerate(video_files, start=1):
            if not running:
                break
            input_video_path = os.path.join(input_folder_path, filename)
            total_saved += process_video(
                input_video_path,
                output_folder_path,
                threshold,
                video_index,
                video_total,
            )

        if running:
            _w1.set_status(f"Done - saved {total_saved} events")
            _w1.set_progress(100, 100)
        else:
            _w1.set_status(f"Cancelled - saved {total_saved} events")
    finally:
        running = False
        _w1.set_controls_enabled(True)


if __name__ == "__main__":
    Lightning1.start_up()
