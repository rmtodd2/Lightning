#! /usr/bin/env python3
#  -*- coding: utf-8 -*-
#

import os
import sys
import threading

import cv2
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

import Lightning1
from lightning_detector import LightningDetector


SUPPORTED_EXTENSIONS = {".mov", ".mp4", ".avi", ".m4v"}
DEFAULT_THRESHOLD = 6.0
UI_UPDATE_INTERVAL = 15  # frames between progress updates

running = False


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


def save_detected_frame(frame, output_path, video_name, frame_number, metrics, threshold):
    output_frame_path = os.path.join(
        output_path,
        (
            f"{video_name}_frame_{frame_number}"
            f"_score_{metrics.score:.2f}"
            f"_flash_{metrics.flash_delta:.1f}"
            f"_area_{metrics.flash_area_ratio:.3f}"
            f"_bolt_{metrics.bolt_score:.1f}"
            f"_comps_{metrics.bolt_component_count}"
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

    detector = LightningDetector(threshold)
    video_name = os.path.splitext(os.path.basename(input_path))[0]
    frame_number = 0
    saved_count = 0
    video_progress = (video_index - 1) / video_total * 100

    while running:
        ret, frame = cap.read()
        if not ret:
            break

        metrics = detector.process(frame)
        if metrics.detected:
            save_detected_frame(
                frame,
                output_path,
                video_name,
                frame_number,
                metrics,
                threshold,
            )
            saved_count += 1

        frame_number += 1
        if frame_number % UI_UPDATE_INTERVAL == 0:
            _w1.set_counts(video_index, video_total, frame_number, frame_total)
            _w1.set_progress(video_progress, frame_number / frame_total * 100)

    cap.release()
    _w1.set_counts(video_index, video_total, frame_number, frame_total)
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
            _w1.set_status(f"Done - saved {total_saved} frames")
            _w1.set_progress(100, 100)
        else:
            _w1.set_status(f"Cancelled - saved {total_saved} frames")
    finally:
        running = False
        _w1.set_controls_enabled(True)


if __name__ == "__main__":
    Lightning1.start_up()
