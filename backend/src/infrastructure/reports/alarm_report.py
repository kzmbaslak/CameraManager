"""Generate scheduled alarm operation reports."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from src.infrastructure.database.models import AlarmModel, CameraModel


BACKEND_DIR = Path(__file__).resolve().parents[3]
DEFAULT_REPORT_DIR = BACKEND_DIR / "reports"
REPORT_FILE_PREFIX = "alarm-report-"


@dataclass(frozen=True)
class AlarmReportResult:
    csv_path: Path
    summary_path: Path
    total_count: int
    removed_files: list[Path]


@dataclass(frozen=True)
class AlarmReportDeliveryResult:
    delivered: bool
    url: str | None = None
    status_code: int | None = None
    message: str = ""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat(timespec="seconds")


def _duration_seconds(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    return max(0, int((end - start).total_seconds()))


def _file_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y%m%d-%H%M%S")


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _bbox(row: AlarmModel) -> str:
    if row.bbox_x is None or row.bbox_y is None or row.bbox_width is None or row.bbox_height is None:
        return ""
    return f"{row.bbox_x},{row.bbox_y},{row.bbox_width},{row.bbox_height}"


def cleanup_old_alarm_reports(
    output_dir: Path = DEFAULT_REPORT_DIR,
    retention_days: int = 180,
    keep_latest: int = 30,
) -> list[Path]:
    """Delete old generated alarm report files and return removed paths."""
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")
    if keep_latest < 1:
        raise ValueError("keep_latest must be at least 1")
    if not output_dir.exists():
        return []

    report_files = sorted(
        (
            path
            for path in output_dir.iterdir()
            if path.is_file() and path.name.startswith(REPORT_FILE_PREFIX) and path.suffix in {".csv", ".json"}
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    removed: list[Path] = []
    for report_path in report_files[keep_latest:]:
        modified_at = datetime.fromtimestamp(report_path.stat().st_mtime, UTC)
        if modified_at >= cutoff:
            continue
        report_path.unlink()
        removed.append(report_path)
    return removed


def _serialize_rows(rows: Iterable[tuple[AlarmModel, str | None]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for alarm, camera_name in rows:
        acknowledge_seconds = _duration_seconds(alarm.created_at, alarm.acknowledged_at)
        resolve_seconds = _duration_seconds(alarm.created_at, alarm.resolved_at)
        records.append(
            {
                "alarm_id": alarm.id,
                "camera_id": alarm.camera_id,
                "camera_name": camera_name or "",
                "alarm_type": getattr(alarm.alarm_type, "value", alarm.alarm_type),
                "status": getattr(alarm.status, "value", alarm.status),
                "severity": alarm.severity or "medium",
                "false_positive": bool(alarm.false_positive),
                "confidence": alarm.confidence,
                "created_at": _format_dt(alarm.created_at),
                "acknowledged_at": _format_dt(alarm.acknowledged_at),
                "resolved_at": _format_dt(alarm.resolved_at),
                "acknowledge_seconds": acknowledge_seconds,
                "resolve_seconds": resolve_seconds,
                "assigned_to": alarm.assigned_to or "",
                "resolution_reason": alarm.resolution_reason or "",
                "message": alarm.message or "",
                "snapshot_sha256": alarm.snapshot_sha256 or "",
                "snapshot_annotated_sha256": alarm.snapshot_annotated_sha256 or "",
                "bbox": _bbox(alarm),
            }
        )
    return records


def _summary(records: list[dict[str, object]], since: datetime, until: datetime) -> dict[str, object]:
    acknowledge_times = [record["acknowledge_seconds"] for record in records if record["acknowledge_seconds"] is not None]
    resolve_times = [record["resolve_seconds"] for record in records if record["resolve_seconds"] is not None]
    return {
        "generated_at": _format_dt(datetime.now(UTC)),
        "window": {"since": _format_dt(since), "until": _format_dt(until)},
        "total_count": len(records),
        "open_count": sum(1 for record in records if record["status"] in {"new", "acknowledged"}),
        "false_positive_count": sum(1 for record in records if record["false_positive"]),
        "by_status": dict(Counter(str(record["status"]) for record in records)),
        "by_type": dict(Counter(str(record["alarm_type"]) for record in records)),
        "by_severity": dict(Counter(str(record["severity"]) for record in records)),
        "average_acknowledge_seconds": round(sum(acknowledge_times) / len(acknowledge_times), 2)
        if acknowledge_times
        else None,
        "average_resolve_seconds": round(sum(resolve_times) / len(resolve_times), 2) if resolve_times else None,
    }


def generate_alarm_report(
    db: Session,
    output_dir: Path = DEFAULT_REPORT_DIR,
    since: datetime | None = None,
    until: datetime | None = None,
    hours: int = 24,
    limit: int = 10000,
    retention_days: int = 180,
    keep_latest: int = 30,
    cleanup: bool = True,
) -> AlarmReportResult:
    """Write a CSV alarm detail report and JSON management summary."""
    if hours < 1:
        raise ValueError("hours must be at least 1")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    effective_until = _naive_utc(until) if until else datetime.now(UTC).replace(tzinfo=None)
    effective_since = _naive_utc(since) if since else effective_until - timedelta(hours=hours)

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{REPORT_FILE_PREFIX}{_file_timestamp(effective_since)}-{_file_timestamp(effective_until)}"
    csv_path = output_dir / f"{stem}.csv"
    summary_path = output_dir / f"{stem}.json"

    rows = (
        db.query(AlarmModel, CameraModel.name)
        .outerjoin(CameraModel, AlarmModel.camera_id == CameraModel.id)
        .filter(AlarmModel.created_at >= effective_since, AlarmModel.created_at < effective_until)
        .order_by(AlarmModel.created_at.asc())
        .limit(limit)
        .all()
    )
    records = _serialize_rows(rows)
    fieldnames = [
        "alarm_id",
        "camera_id",
        "camera_name",
        "alarm_type",
        "status",
        "severity",
        "false_positive",
        "confidence",
        "created_at",
        "acknowledged_at",
        "resolved_at",
        "acknowledge_seconds",
        "resolve_seconds",
        "assigned_to",
        "resolution_reason",
        "message",
        "snapshot_sha256",
        "snapshot_annotated_sha256",
        "bbox",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(_summary(records, effective_since, effective_until), file, ensure_ascii=False, indent=2)

    removed_files = cleanup_old_alarm_reports(output_dir, retention_days, keep_latest) if cleanup else []
    return AlarmReportResult(
        csv_path=csv_path,
        summary_path=summary_path,
        total_count=len(records),
        removed_files=removed_files,
    )


def deliver_alarm_report_webhook(
    result: AlarmReportResult,
    webhook_url: str | None = None,
    token: str | None = None,
    timeout_seconds: int | None = None,
    opener=urlopen,
) -> AlarmReportDeliveryResult:
    """Send generated alarm report metadata to an HTTPS webhook/SIEM endpoint."""
    url = (webhook_url or os.environ.get("ALARM_REPORT_WEBHOOK_URL", "")).strip()
    if not url:
        return AlarmReportDeliveryResult(delivered=False, message="ALARM_REPORT_WEBHOOK_URL tanimli degil.")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return AlarmReportDeliveryResult(delivered=False, url=url, message="Webhook URL HTTPS ve gecerli host icermeli.")
    effective_token = (token if token is not None else os.environ.get("ALARM_REPORT_WEBHOOK_TOKEN", "")).strip()
    if timeout_seconds is None:
        try:
            timeout_seconds = int(os.environ.get("ALARM_REPORT_WEBHOOK_TIMEOUT_SECONDS", "5") or "5")
        except ValueError:
            timeout_seconds = 5
    timeout_seconds = min(max(timeout_seconds, 1), 60)
    with result.summary_path.open("r", encoding="utf-8") as file:
        summary = json.load(file)
    payload = json.dumps(
        {
            "event": "alarm_report.generated",
            "generated_at": _format_dt(datetime.now(UTC)),
            "total_count": result.total_count,
            "summary": summary,
            "artifacts": {
                "csv": {
                    "filename": result.csv_path.name,
                    "size_bytes": result.csv_path.stat().st_size,
                    "sha256": _file_sha256(result.csv_path),
                },
                "summary": {
                    "filename": result.summary_path.name,
                    "size_bytes": result.summary_path.stat().st_size,
                    "sha256": _file_sha256(result.summary_path),
                },
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "kamera-yonetimi-alarm-report/1.0"}
    if effective_token:
        headers["Authorization"] = f"Bearer {effective_token}"
    request = Request(url, data=payload, headers=headers, method="POST")
    with opener(request, timeout=timeout_seconds) as response:
        status_code = getattr(response, "status", None) or getattr(response, "code", None)
    return AlarmReportDeliveryResult(
        delivered=bool(status_code and 200 <= int(status_code) < 300),
        url=url,
        status_code=int(status_code) if status_code else None,
        message="delivered",
    )
