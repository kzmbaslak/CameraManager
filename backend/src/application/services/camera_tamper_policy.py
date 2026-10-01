"""Kamera goruntusu sabotaj/karartma sinyallerini degerlendirir."""

from __future__ import annotations

import os
from dataclasses import dataclass

import cv2


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "evet"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)) or str(default))
    except ValueError:
        value = default
    return min(max(value, minimum), maximum)


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)) or str(default))
    except ValueError:
        value = default
    return min(max(value, minimum), maximum)


@dataclass(frozen=True)
class CameraTamperAnalysisResult:
    triggered: bool
    reason: str
    brightness_mean: float
    brightness_stddev: float
    blur_variance: float
    score: float


@dataclass(frozen=True)
class CameraTamperPolicy:
    enabled: bool = True
    frame_stride: int = 15
    consecutive_frames: int = 3
    dark_mean_threshold: float = 12.0
    flat_stddev_threshold: float = 4.0
    blur_variance_threshold: float = 15.0
    alarm_cooldown_seconds: int = 900

    @classmethod
    def from_environment(cls) -> "CameraTamperPolicy":
        return cls(
            enabled=_env_bool("CAMERA_TAMPER_DETECTION_ENABLED", True),
            frame_stride=_env_int("CAMERA_TAMPER_FRAME_STRIDE", 15, 1, 300),
            consecutive_frames=_env_int("CAMERA_TAMPER_CONSECUTIVE_FRAMES", 3, 1, 30),
            dark_mean_threshold=_env_float("CAMERA_TAMPER_DARK_MEAN_THRESHOLD", 12.0, 0.0, 255.0),
            flat_stddev_threshold=_env_float("CAMERA_TAMPER_FLAT_STDDEV_THRESHOLD", 4.0, 0.0, 128.0),
            blur_variance_threshold=_env_float("CAMERA_TAMPER_BLUR_VARIANCE_THRESHOLD", 15.0, 0.0, 10000.0),
            alarm_cooldown_seconds=_env_int("CAMERA_TAMPER_ALARM_COOLDOWN_SECONDS", 900, 30, 86400),
        )

    def analyze(self, frame: object) -> CameraTamperAnalysisResult:
        if not self.enabled or frame is None or not hasattr(frame, "shape"):
            return CameraTamperAnalysisResult(False, "disabled", 0.0, 0.0, 0.0, 0.0)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) >= 3 else frame
        mean, stddev = cv2.meanStdDev(gray)
        brightness_mean = float(mean[0][0])
        brightness_stddev = float(stddev[0][0])
        blur_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        if brightness_mean <= self.dark_mean_threshold:
            score = min(1.0, (self.dark_mean_threshold - brightness_mean + 1.0) / max(self.dark_mean_threshold, 1.0))
            return CameraTamperAnalysisResult(True, "dark_frame", brightness_mean, brightness_stddev, blur_variance, score)

        if brightness_stddev <= self.flat_stddev_threshold:
            score = min(1.0, (self.flat_stddev_threshold - brightness_stddev + 1.0) / max(self.flat_stddev_threshold, 1.0))
            return CameraTamperAnalysisResult(True, "flat_frame", brightness_mean, brightness_stddev, blur_variance, score)

        if blur_variance <= self.blur_variance_threshold:
            score = min(1.0, (self.blur_variance_threshold - blur_variance + 1.0) / max(self.blur_variance_threshold, 1.0))
            return CameraTamperAnalysisResult(True, "blurred_frame", brightness_mean, brightness_stddev, blur_variance, score)

        return CameraTamperAnalysisResult(False, "normal", brightness_mean, brightness_stddev, blur_variance, 0.0)
