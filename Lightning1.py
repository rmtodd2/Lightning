#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

import os
import sys

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class UiBridge(QObject):
    status_changed = Signal(str)
    counts_changed = Signal(int, int, int, int)
    progress_changed = Signal(float, float)
    controls_enabled_changed = Signal(bool)


class LightningWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bridge = UiBridge()
        self._build_ui()
        self._connect_bridge()

    def _build_ui(self):
        self.setWindowTitle("Lightning")
        self.setMinimumSize(620, 430)

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Lightning.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(24, 22, 24, 18)
        root_layout.setSpacing(18)

        title = QLabel("Lightning Frame Extractor")
        title.setObjectName("title")
        subtitle = QLabel("Scan video folders for sudden lightning flashes and save the strongest frames.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Input folder containing video files")
        self.input_path.setReadOnly(True)
        self.input_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_button = QPushButton("...")
        input_row = self._path_row(self.input_path, self.input_button)
        form.addRow("Input folder", input_row)

        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Folder where detected frames will be saved")
        self.output_path.setReadOnly(True)
        self.output_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.output_button = QPushButton("...")
        output_row = self._path_row(self.output_path, self.output_button)
        form.addRow("Output folder", output_row)

        self.threshold = QLineEdit()
        self.threshold.setToolTip(
            "Sensitivity threshold for lightning detection. Lower values catch more flashes; 6.0 is a good starting point."
        )
        self.threshold.setMaximumWidth(130)
        form.addRow("Lightning threshold", self.threshold)
        root_layout.addLayout(form)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.start_button = QPushButton("Start")
        self.cancel_button = QPushButton("Cancel")
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.cancel_button)
        action_row.addStretch(1)
        root_layout.addLayout(action_row)

        self.status_label = QLabel("Idle")
        self.status_label.setObjectName("status")
        root_layout.addWidget(self.status_label)

        progress_grid = QGridLayout()
        progress_grid.setHorizontalSpacing(12)
        progress_grid.setVerticalSpacing(8)

        self.video_progress = QProgressBar()
        self.frame_progress = QProgressBar()
        self.video_count = QLabel("0 / 0")
        self.frame_count = QLabel("0 / 0")
        self.video_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.frame_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        progress_grid.addWidget(QLabel("Videos"), 0, 0)
        progress_grid.addWidget(self.video_progress, 0, 1)
        progress_grid.addWidget(self.video_count, 0, 2)
        progress_grid.addWidget(QLabel("Frames"), 1, 0)
        progress_grid.addWidget(self.frame_progress, 1, 1)
        progress_grid.addWidget(self.frame_count, 1, 2)
        progress_grid.setColumnStretch(1, 1)
        root_layout.addLayout(progress_grid)
        root_layout.addStretch(1)

        self.setCentralWidget(central)
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f5f6f8;
            }
            QLabel {
                color: #1f2933;
                font-size: 14px;
            }
            QLabel#title {
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#subtitle {
                color: #52606d;
            }
            QLabel#status {
                font-weight: 700;
            }
            QLineEdit {
                background: white;
                border: 1px solid #cbd2d9;
                border-radius: 4px;
                padding: 7px 8px;
                selection-background-color: #2f80ed;
            }
            QPushButton {
                background: #ffffff;
                border: 1px solid #9aa5b1;
                border-radius: 4px;
                padding: 7px 14px;
                min-width: 72px;
            }
            QPushButton:hover {
                background: #eef2f7;
            }
            QPushButton:pressed {
                background: #d9e2ec;
            }
            QPushButton:disabled {
                color: #9aa5b1;
                background: #f0f2f5;
            }
            QProgressBar {
                border: 1px solid #cbd2d9;
                border-radius: 4px;
                height: 18px;
                text-align: center;
                background: #ffffff;
            }
            QProgressBar::chunk {
                background: #2f80ed;
                border-radius: 3px;
            }
            """
        )

    def _path_row(self, line_edit, button):
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(line_edit)
        row.addWidget(button)
        wrapper = QWidget()
        wrapper.setLayout(row)
        return wrapper

    def _connect_bridge(self):
        self.bridge.status_changed.connect(self._set_status)
        self.bridge.counts_changed.connect(self._set_counts)
        self.bridge.progress_changed.connect(self._set_progress)
        self.bridge.controls_enabled_changed.connect(self._set_controls_enabled)

    @Slot(str)
    def _set_status(self, text):
        self.status_label.setText(text)

    @Slot(int, int, int, int)
    def _set_counts(self, video_index, video_total, frame_index, frame_total):
        self.video_count.setText(f"{video_index} / {video_total}")
        self.frame_count.setText(f"{frame_index} / {frame_total}")

    @Slot(float, float)
    def _set_progress(self, video_progress, frame_progress):
        self.video_progress.setValue(round(video_progress))
        self.frame_progress.setValue(round(frame_progress))

    @Slot(bool)
    def _set_controls_enabled(self, enabled):
        self.input_button.setEnabled(enabled)
        self.output_button.setEnabled(enabled)
        self.start_button.setEnabled(enabled)

    def set_status(self, text):
        self.bridge.status_changed.emit(text)

    def set_counts(self, video_index, video_total, frame_index, frame_total):
        self.bridge.counts_changed.emit(video_index, video_total, frame_index, frame_total)

    def set_progress(self, video_progress, frame_progress):
        self.bridge.progress_changed.emit(video_progress, frame_progress)

    def set_controls_enabled(self, enabled):
        self.bridge.controls_enabled_changed.emit(enabled)


def start_up():
    import Lightning1_support

    Lightning1_support.main()


if __name__ == "__main__":
    start_up()
