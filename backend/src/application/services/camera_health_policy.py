"""Camera health threshold policy loaded from runtime environment."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CameraHealthPolicy:
    """Thresholds used to classify camera reachability and latency."""

    critical_availability_percent: float = 90.0
    warning_availability_percent: float = 98.0
    max_latency_ms: float = 1000.0
    stale_sample_seconds: int = 120

    @classmethod
    def from_environment(cls) -> "CameraHealthPolicy":
        return cls(
            critical_availability_percent=_float_env("CAMERA_HEALTH_CRITICAL_AVAILABILITY_PERCENT", 90.0, 1.0, 100.0),
            warning_availability_percent=_float_env("CAMERA_HEALTH_WARNING_AVAILABILITY_PERCENT", 98.0, 1.0, 100.0),
            max_latency_ms=_float_env("CAMERA_HEALTH_MAX_LATENCY_MS", 1000.0, 50.0, 60000.0),
            stale_sample_seconds=int(_float_env("CAMERA_HEALTH_STALE_SAMPLE_SECONDS", 120.0, 10.0, 3600.0)),
        ).normalized()

    def normalized(self) -> "CameraHealthPolicy":
        critical = min(self.critical_availability_percent, self.warning_availability_percent)
        warning = max(self.critical_availability_percent, self.warning_availability_percent)
        return CameraHealthPolicy(
            critical_availability_percent=critical,
            warning_availability_percent=warning,
            max_latency_ms=self.max_latency_ms,
            stale_sample_seconds=self.stale_sample_seconds,
        )


def _float_env(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)) or str(default))
    except ValueError:
        value = default
    return min(max(value, minimum), maximum)
