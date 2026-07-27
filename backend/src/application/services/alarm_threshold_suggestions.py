"""Alarm geri bildirimlerinden kamera bazli threshold onerisi uretir."""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ThresholdSuggestion:
    camera_id: int
    sample_count: int
    false_positive_count: int
    false_positive_rate: float
    average_confidence: float | None
    suggested_confidence_threshold: float | None
    recommendation: str


def build_threshold_suggestions(alarms: Iterable[object], minimum_samples: int = 3) -> list[ThresholdSuggestion]:
    """Insan tespiti alarmlarindan kamera bazli confidence esigi onerileri uretir."""
    safe_minimum_samples = max(1, min(minimum_samples, 50))
    grouped: dict[int, list[object]] = {}
    for alarm in alarms:
        grouped.setdefault(alarm.camera_id, []).append(alarm)

    suggestions: list[ThresholdSuggestion] = []
    for camera_id, camera_alarms in grouped.items():
        sample_count = len(camera_alarms)
        if sample_count < safe_minimum_samples:
            continue

        false_positive_count = sum(1 for alarm in camera_alarms if alarm.false_positive)
        false_positive_rate = false_positive_count / sample_count
        confidence_values = [
            alarm.confidence
            for alarm in camera_alarms
            if alarm.confidence is not None
        ]
        average_confidence = (
            round(sum(confidence_values) / len(confidence_values), 3)
            if confidence_values
            else None
        )
        suggested_threshold = None
        if false_positive_count >= 2 and average_confidence is not None:
            if false_positive_rate >= 0.5:
                suggested_threshold = min(0.95, max(0.05, average_confidence + 0.1))
            elif false_positive_rate >= 0.3:
                suggested_threshold = min(0.95, max(0.05, average_confidence + 0.05))

        if suggested_threshold is not None:
            recommendation = (
                "Yanlis alarm orani yuksek; insan tespiti confidence esigini "
                f"{round(suggested_threshold * 100)}% seviyesine cikarmayi degerlendirin."
            )
        elif false_positive_count == 0 and sample_count >= 10:
            recommendation = "Yanlis alarm baskisi dusuk; mevcut esik korunabilir."
        else:
            recommendation = "Otomatik esik degisikligi icin daha fazla operator geri bildirimi toplayin."

        suggestions.append(
            ThresholdSuggestion(
                camera_id=camera_id,
                sample_count=sample_count,
                false_positive_count=false_positive_count,
                false_positive_rate=round(false_positive_rate, 3),
                average_confidence=average_confidence,
                suggested_confidence_threshold=(
                    round(suggested_threshold, 3)
                    if suggested_threshold is not None
                    else None
                ),
                recommendation=recommendation,
            )
        )

    return sorted(
        suggestions,
        key=lambda item: (item.false_positive_rate, item.false_positive_count, item.sample_count),
        reverse=True,
    )
