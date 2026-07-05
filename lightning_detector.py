#! /usr/bin/env python3
#  -*- coding: utf-8 -*-
"""Lightning frame detection for slow-motion video.

Slow motion means a single flash persists across many consecutive frames, so
frame-to-frame differencing sees almost nothing.  Instead the detector keeps a
slowly-adapting background model of the scene (frozen while lightning is
visible) and looks for two kinds of evidence against it:

1. Bolt structure: thin, elongated, high-contrast bright channels measured
   with orientation-independent geometry (rotated-rect extent, stroke width
   from a distance transform).  Every accepted component must also be *novel*
   - much brighter than the background model - which rejects static bright
   objects such as fence posts, antennas, and building trim.

2. Broad flash: a large share of the frame suddenly brightens well above the
   background.  Entry into a flash event requires a fast onset (mean rise
   within a few frames), which gradual exposure changes never produce, and
   brightening must not be matched by darkening (which indicates camera
   motion, not lightning).
"""

from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np


# --- Analysis resolutions -------------------------------------------------
FLASH_WIDTH = 320          # coarse scale used for whole-frame flash metrics
BOLT_MAX_WIDTH = 960       # fine scale used for bolt geometry

# --- Background model -----------------------------------------------------
BACKGROUND_ALPHA = 0.02    # EMA update rate while no lightning is detected
MAX_DETECTION_STREAK = 240 # resume background updates after this many
                           # consecutive detections (scene-change safety)

# --- Broad flash gates (measured against the background model) -------------
BRIGHTEN_DELTA = 20.0      # gray levels above background = flash-lit pixel
MIN_FLASH_MEAN_DELTA = 2.5 # minimum whole-frame mean rise over background
MIN_FLASH_AREA_RATIO = 0.04  # minimum share of flash-lit pixels
ONSET_MIN_RISE = 4.0       # mean must rise this much within ONSET_WINDOW
ONSET_WINDOW = 4           # frames of history used for onset detection
ONE_SIDED_FACTOR = 3.0     # brightened area must dominate darkened area

# --- Bolt structure gates ---------------------------------------------------
# Novelty is applied per PIXEL before anything else: a bolt pixel must be
# much brighter than the background model.  This removes static bright
# structures (fence posts, house trim, sky gaps between power lines) from
# the mask entirely, so they can neither match nor merge with a real bolt.
BOLT_NOVELTY_DELTA = 30.0  # gray levels above the background model
BOLT_CORE_BRIGHTNESS = 180 # minimum pixel value inside a bolt channel
BOLT_CORE_CONTRAST = 12    # minimum rise above the local neighborhood
BOLT_MIN_AREA = 20         # ignore tiny specks outright
BOLT_MIN_EXTENT = 40       # minimum rotated-rect length in pixels at 960w
BOLT_MAX_CHANNEL_WIDTH = 12.0  # bolts are thin; wide bands are clouds/gaps
BOLT_MIN_THINNESS = 6.0    # total channel length / channel width
BOLT_RIDGE_MARGIN = 15.0   # channel must outshine its surroundings, so the
                           # bright edge strip of a wide band cannot qualify
BOLT_STRONG_SCORE = 20.0   # structure alone is proof at or above this score
BOLT_SUPPORT_SCORE = 6.0   # weaker structure still counts with flash support


@dataclass
class FrameMetrics:
    mean_brightness: float
    flash_delta: float          # mean brightness rise over background
    flash_area_ratio: float     # share of pixels brightened >= BRIGHTEN_DELTA
    darkened_area_ratio: float  # share of pixels darkened >= BRIGHTEN_DELTA
    bolt_score: float
    bolt_component_count: int
    score: float
    detected: bool


def _resize_to_width(gray, target_width):
    height, width = gray.shape
    if width <= target_width:
        return gray
    scale = target_width / width
    return cv2.resize(
        gray,
        (target_width, max(1, int(round(height * scale)))),
        interpolation=cv2.INTER_AREA,
    )


class LightningDetector:
    """Stateful per-video detector.  Feed frames in order via process()."""

    def __init__(self, threshold):
        self.threshold = threshold
        self.flash_background = None
        self.bolt_background = None
        self.recent_means = deque(maxlen=ONSET_WINDOW)
        self.in_flash = False
        self.detection_streak = 0

    def process(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        flash_gray = cv2.GaussianBlur(
            _resize_to_width(gray, FLASH_WIDTH), (5, 5), 0
        ).astype(np.float32)
        bolt_gray = _resize_to_width(gray, BOLT_MAX_WIDTH)

        first_frame = self.flash_background is None
        if first_frame:
            self.flash_background = flash_gray.copy()
            self.bolt_background = bolt_gray.astype(np.float32)

        diff = flash_gray - self.flash_background
        mean_brightness = float(np.mean(flash_gray))
        flash_delta = float(np.mean(diff))
        flash_area_ratio = float(np.mean(diff >= BRIGHTEN_DELTA))
        darkened_area_ratio = float(np.mean(diff <= -BRIGHTEN_DELTA))

        if first_frame:
            # No background to verify against yet: never detect on frame 0.
            bolt_score, bolt_components = 0.0, 0
            detected = False
        else:
            bolt_score, bolt_components = self._score_bolt_structure(bolt_gray)
            detected = self._decide(
                mean_brightness, flash_delta, flash_area_ratio,
                darkened_area_ratio, bolt_score,
            )

        self.recent_means.append(mean_brightness)
        if detected:
            self.detection_streak += 1
        else:
            self.detection_streak = 0
        if not detected or self.detection_streak > MAX_DETECTION_STREAK:
            cv2.accumulateWeighted(
                flash_gray, self.flash_background, BACKGROUND_ALPHA
            )
            cv2.accumulateWeighted(
                bolt_gray.astype(np.float32),
                self.bolt_background,
                BACKGROUND_ALPHA,
            )

        score = (
            max(0.0, flash_delta) * 0.5
            + flash_area_ratio * 40.0
            + bolt_score
        )
        return FrameMetrics(
            mean_brightness=mean_brightness,
            flash_delta=flash_delta,
            flash_area_ratio=flash_area_ratio,
            darkened_area_ratio=darkened_area_ratio,
            bolt_score=bolt_score,
            bolt_component_count=bolt_components,
            score=score,
            detected=detected,
        )

    def _decide(self, mean_brightness, flash_delta, flash_area_ratio,
                darkened_area_ratio, bolt_score):
        score = (
            max(0.0, flash_delta) * 0.5
            + flash_area_ratio * 40.0
            + bolt_score
        )

        # A clearly-shaped novel bolt channel is proof by itself, and a high
        # user threshold must not suppress it.
        strong_bolt = bolt_score >= BOLT_STRONG_SCORE

        # Weaker structure still counts when the sky brightened with it.
        supported_bolt = (
            bolt_score >= BOLT_SUPPORT_SCORE
            and flash_delta >= 1.0
            and flash_area_ratio >= 0.01
        )

        # Broad flash: sudden, one-sided brightening of a large area.
        onset = (
            len(self.recent_means) == ONSET_WINDOW
            and mean_brightness - min(self.recent_means) >= ONSET_MIN_RISE
        )
        one_sided = flash_area_ratio >= ONE_SIDED_FACTOR * max(
            darkened_area_ratio, 0.002
        )
        broad_level = (
            flash_delta >= MIN_FLASH_MEAN_DELTA
            and flash_area_ratio >= MIN_FLASH_AREA_RATIO
            and one_sided
        )
        broad_flash = broad_level and (onset or self.in_flash)
        self.in_flash = broad_flash

        return strong_bolt or (
            score >= self.threshold and (supported_bolt or broad_flash)
        )

    def _score_bolt_structure(self, bolt_gray):
        """Score thin, elongated, novel bright channels in the frame."""
        local_average = cv2.GaussianBlur(bolt_gray, (31, 31), 0)
        local_contrast = cv2.subtract(bolt_gray, local_average)
        novelty = bolt_gray.astype(np.float32) - self.bolt_background
        core_mask = (
            (bolt_gray >= BOLT_CORE_BRIGHTNESS)
            & (local_contrast >= BOLT_CORE_CONTRAST)
            & (novelty >= BOLT_NOVELTY_DELTA)
        ).astype(np.uint8) * 255
        # Bridge small gaps so a zigzag channel stays one component.
        core_mask = cv2.morphologyEx(
            core_mask,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
        )

        component_count, labels, stats, _ = cv2.connectedComponentsWithStats(
            core_mask, 8
        )
        mask_bool = core_mask > 0
        frame_h, frame_w = bolt_gray.shape

        total_score = 0.0
        matching_components = 0
        for index in range(1, component_count):
            x, y, w, h, area = stats[index]
            if area < BOLT_MIN_AREA or max(w, h) < BOLT_MIN_EXTENT:
                continue

            component = (labels[y:y + h, x:x + w] == index)

            # Orientation-independent extent from the rotated bounding rect.
            ys, xs = np.nonzero(component)
            points = np.column_stack((xs, ys)).astype(np.float32)
            (_, _), (rect_w, rect_h), _ = cv2.minAreaRect(points)
            extent = max(rect_w, rect_h)
            if extent < BOLT_MIN_EXTENT:
                continue

            # Stroke width from the distance transform: for a channel of
            # width W the interior distances average about W/4.  Thinness
            # (skeleton length over width) separates channels from blobs
            # regardless of orientation or branching.
            padded = np.pad(component, 1).astype(np.uint8)
            distances = cv2.distanceTransform(padded, cv2.DIST_L2, 3)
            channel_width = max(1.0, 4.0 * float(np.mean(distances[padded > 0])))
            total_length = area / channel_width
            thinness = total_length / channel_width

            if channel_width > BOLT_MAX_CHANNEL_WIDTH:
                continue
            if thinness < BOLT_MIN_THINNESS:
                continue

            # Ridge test: a bolt channel outshines BOTH of its sides, while
            # the bright edge strip of a wide band or cloud gap has an even
            # brighter interior right next to it.  Compare the component's
            # novelty to the novelty of the surrounding ring (mask pixels
            # excluded so neighboring fragments do not skew the ring).
            wx0, wy0 = max(0, x - 8), max(0, y - 8)
            wx1, wy1 = min(frame_w, x + w + 8), min(frame_h, y + h + 8)
            window = (labels[wy0:wy1, wx0:wx1] == index)
            ring = cv2.dilate(
                window.astype(np.uint8),
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)),
            ).astype(bool) & ~mask_bool[wy0:wy1, wx0:wx1]
            window_novelty = novelty[wy0:wy1, wx0:wx1]
            component_novelty = float(np.mean(window_novelty[window]))
            ring_novelty = (
                float(np.mean(window_novelty[ring])) if ring.any() else 0.0
            )
            if component_novelty < ring_novelty + BOLT_RIDGE_MARGIN:
                continue

            matching_components += 1
            total_score += total_length * min(thinness, 20.0) / 100.0

        return total_score, matching_components
