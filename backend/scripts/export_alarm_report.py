"""Export scheduled alarm operation reports."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.infrastructure.database.database import SessionLocal
from src.infrastructure.reports.alarm_report import DEFAULT_REPORT_DIR, deliver_alarm_report_webhook, generate_alarm_report


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise SystemExit(f"{name} sayisal olmali: {raw_value}") from exc


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Tarih ISO formatinda olmali, orn: 2026-07-27T00:00:00") from exc
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Alarm operasyon raporu uretir.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR, help="Rapor klasoru.")
    parser.add_argument("--since", type=_parse_datetime, help="Baslangic zamani, ISO formatinda.")
    parser.add_argument("--until", type=_parse_datetime, help="Bitis zamani, ISO formatinda.")
    parser.add_argument(
        "--hours",
        type=int,
        default=_env_int("ALARM_REPORT_WINDOW_HOURS", 24),
        help="since verilmezse geriye donuk rapor penceresi.",
    )
    parser.add_argument("--limit", type=int, default=_env_int("ALARM_REPORT_LIMIT", 10000), help="Maksimum alarm satiri.")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=_env_int("ALARM_REPORT_RETENTION_DAYS", 180),
        help="Rapor dosyalarinin saklanacagi gun sayisi.",
    )
    parser.add_argument(
        "--keep-latest",
        type=int,
        default=_env_int("ALARM_REPORT_KEEP_LATEST", 30),
        help="Retention suresi dolsa bile tutulacak en yeni rapor dosyasi sayisi.",
    )
    parser.add_argument("--skip-cleanup", action="store_true", help="Eski rapor temizligini atla.")
    parser.add_argument("--skip-delivery", action="store_true", help="ALARM_REPORT_WEBHOOK_URL tanimli olsa bile rapor dagitimini atla.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = generate_alarm_report(
            db,
            output_dir=args.output_dir,
            since=args.since,
            until=args.until,
            hours=args.hours,
            limit=args.limit,
            retention_days=args.retention_days,
            keep_latest=args.keep_latest,
            cleanup=not args.skip_cleanup,
        )
    finally:
        db.close()

    print(f"Alarm raporu olusturuldu: {result.csv_path}")
    print(f"Ozet olusturuldu: {result.summary_path}")
    print(f"Alarm sayisi: {result.total_count}")
    if result.removed_files:
        print(f"Eski rapor temizlendi: {len(result.removed_files)} dosya")
        for path in result.removed_files:
            print(path)
    if not args.skip_delivery:
        delivery = deliver_alarm_report_webhook(result)
        if delivery.url:
            print(
                "Rapor dagitimi: "
                f"{'basarili' if delivery.delivered else 'basarisiz'} "
                f"status={delivery.status_code or '-'} url={delivery.url}"
            )


if __name__ == "__main__":
    main()
