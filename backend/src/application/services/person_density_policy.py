"""Saatlik insan yogunlugu verisinden anomali karari uretir."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

from src.domain.entities.person_analytics import CameraPersonHourlyStat


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
class PersonDensityAnomalyResult:
    triggered: bool
    reason: str
    baseline_peak_average: float | None = None
    score: float = 0.0


@dataclass(frozen=True)
class PersonDensityPolicy:
    enabled: bool = True
    baseline_window_hours: int = 24
    min_baseline_buckets: int = 6
    baseline_multiplier: float = 3.0
    absolute_peak_person_count: int = 6
    min_current_peak_person_count: int = 2
    alarm_cooldown_seconds: int = 900

    @classmethod
    def from_environment(cls) -> "PersonDensityPolicy":
        return cls(
            enabled=_env_bool("PERSON_DENSITY_ANOMALY_ENABLED", True),
            baseline_window_hours=_env_int("PERSON_DENSITY_BASELINE_WINDOW_HOURS", 24, 1, 168),
            min_baseline_buckets=_env_int("PERSON_DENSITY_MIN_BASELINE_BUCKETS", 6, 1, 168),
            baseline_multiplier=_env_float("PERSON_DENSITY_BASELINE_MULTIPLIER", 3.0, 1.1, 20.0),
            absolute_peak_person_count=_env_int("PERSON_DENSITY_ABSOLUTE_PEAK_PERSON_COUNT", 6, 1, 1000),
            min_current_peak_person_count=_env_int("PERSON_DENSITY_MIN_CURRENT_PEAK_PERSON_COUNT", 2, 1, 1000),
            alarm_cooldown_seconds=_env_int("PERSON_DENSITY_ALARM_COOLDOWN_SECONDS", 900, 30, 86400),
        )

    def evaluate(
        self,
        current: CameraPersonHourlyStat,
        previous: Sequence[CameraPersonHourlyStat],
    ) -> PersonDensityAnomalyResult:
        if not self.enabled:
            return PersonDensityAnomalyResult(False, "disabled")

        peak = max(0, current.max_person_count or 0)
        if peak >= self.absolute_peak_person_count:
            return PersonDensityAnomalyResult(
                triggered=True,
                reason="absolute_peak",
                score=min(1.0, peak / max(self.absolute_peak_person_count, 1)),
            )

        baseline_values = [max(0, item.max_person_count or 0) for item in previous if item.max_person_count is not None]
        if len(baseline_values) < self.min_baseline_buckets:
            return PersonDensityAnomalyResult(False, "insufficient_baseline")

        baseline_average = sum(baseline_values) / len(baseline_values)
        threshold = max(self.min_current_peak_person_count, baseline_average * self.baseline_multiplier)
        if peak >= threshold:
            score = 1.0 if threshold <= 0 else min(1.0, peak / threshold)
            return PersonDensityAnomalyResult(
                triggered=True,
                reason="baseline_multiplier",
                baseline_peak_average=baseline_average,
                score=score,
            )

        return PersonDensityAnomalyResult(
            triggered=False,
            reason="normal",
            baseline_peak_average=baseline_average,
            score=0.0,
        )
