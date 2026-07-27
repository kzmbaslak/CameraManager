"""UTC zaman uretimi icin ortak yardimcilar."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp dondurur."""
    return datetime.now(timezone.utc)
