"""Privacy-preserving daily activity aggregates and hydration timing."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
RETENTION_DAYS = 30
MAX_SAMPLE_SECONDS = 5.0
SNOOZE_MINUTES = 10

DAY_FIELDS = {
    "date",
    "active_seconds",
    "idle_seconds",
    "water_count",
    "hydration_elapsed_seconds",
    "snooze_remaining_seconds",
}


@dataclass
class DailyActivity:
    """One day's aggregates. No raw input events are represented or stored."""

    date: str
    active_seconds: float = 0.0
    idle_seconds: float = 0.0
    water_count: int = 0
    hydration_elapsed_seconds: float = 0.0
    snooze_remaining_seconds: float = 0.0


def local_date(value: date | datetime | None = None) -> str:
    if value is None:
        return date.today().isoformat()
    return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()


def is_quiet_hour(hour: int, start: int = 22, end: int = 8) -> bool:
    """Return whether an hour falls inside a possibly overnight quiet period."""
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def format_duration(seconds: float) -> str:
    total_minutes = max(0, int(seconds // 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return "<1m"


def format_duration_zh(seconds: float) -> str:
    """Format a duration for the Chinese desktop interface."""
    total_minutes = max(0, int(seconds // 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours} 小时 {minutes} 分钟"
    if minutes:
        return f"{minutes} 分钟"
    return "不足 1 分钟"


def wrapped_tick_elapsed_seconds(current_tick: int, last_input_tick: int) -> float:
    """Calculate a DWORD millisecond delta across the Windows tick wraparound."""
    return ((current_tick - last_input_tick) & 0xFFFFFFFF) / 1000.0


def _nonnegative_number(value: object) -> float:
    if type(value) not in (int, float):
        return 0.0
    return max(0.0, min(float(value), 31_536_000.0))


def _nonnegative_int(value: object) -> int:
    if type(value) is not int:
        return 0
    return max(0, min(value, 10_000))


class ActivityTracker:
    """Aggregate activity samples without accepting input content or app data."""

    def __init__(
        self,
        days: dict[str, DailyActivity] | None = None,
        *,
        today: date | datetime | None = None,
    ) -> None:
        self.days = dict(days or {})
        self.current_date = local_date(today)
        self._ensure_today()
        self.prune()

    @property
    def today(self) -> DailyActivity:
        return self.days[self.current_date]

    def _ensure_today(self, value: date | datetime | None = None) -> DailyActivity:
        key = local_date(value) if value is not None else self.current_date
        self.current_date = key
        if key not in self.days:
            self.days[key] = DailyActivity(date=key)
        return self.days[key]

    def record_sample(
        self,
        elapsed_seconds: float,
        *,
        is_idle: bool,
        count_activity: bool,
        count_hydration: bool,
        today: date | datetime | None = None,
    ) -> None:
        """Record one bounded aggregate sample; large sleep/resume gaps are capped."""
        day = self._ensure_today(today)
        sample = max(0.0, min(float(elapsed_seconds), MAX_SAMPLE_SECONDS))
        if sample == 0:
            return

        if is_idle:
            if count_activity:
                day.idle_seconds += sample
            return

        if count_activity:
            day.active_seconds += sample
        if count_hydration:
            day.hydration_elapsed_seconds += sample
            day.snooze_remaining_seconds = max(
                0.0,
                day.snooze_remaining_seconds - sample,
            )

    def hydration_due(
        self,
        interval_minutes: int,
        *,
        hour: int,
        user_is_idle: bool,
    ) -> bool:
        day = self.today
        return (
            not user_is_idle
            and not is_quiet_hour(hour)
            and day.hydration_elapsed_seconds >= max(1, interval_minutes) * 60
            and day.snooze_remaining_seconds <= 0
        )

    def mark_reminded(self, now: datetime | None = None) -> None:
        moment = now or datetime.now().astimezone()
        self._ensure_today(moment)
        self.today.snooze_remaining_seconds = SNOOZE_MINUTES * 60

    def mark_water(self, now: datetime | None = None) -> None:
        moment = now or datetime.now().astimezone()
        self._ensure_today(moment)
        self.today.water_count += 1
        self.today.hydration_elapsed_seconds = 0.0
        self.today.snooze_remaining_seconds = 0.0

    def clear_history(self, *, today: date | datetime | None = None) -> None:
        self.days.clear()
        self.current_date = local_date(today)
        self._ensure_today()

    def prune(self) -> None:
        """Retain only the newest fixed number of daily aggregate records."""
        other_dates = [key for key in sorted(self.days) if key != self.current_date]
        keep = set(other_dates[-(RETENTION_DAYS - 1):])
        keep.add(self.current_date)
        self.days = {key: value for key, value in self.days.items() if key in keep}

    def to_dict(self) -> dict[str, Any]:
        """Serialize through an explicit field allowlist."""
        self.prune()
        serialized_days: dict[str, dict[str, Any]] = {}
        for key in sorted(self.days):
            raw = asdict(self.days[key])
            serialized_days[key] = {
                field: round(raw[field], 3) if isinstance(raw[field], float) else raw[field]
                for field in DAY_FIELDS
            }
        return {"schema_version": SCHEMA_VERSION, "days": serialized_days}

    @classmethod
    def from_dict(
        cls,
        payload: object,
        *,
        today: date | datetime | None = None,
    ) -> "ActivityTracker":
        parsed: dict[str, DailyActivity] = {}
        if isinstance(payload, dict) and isinstance(payload.get("days"), dict):
            for key, raw in payload["days"].items():
                if not isinstance(key, str) or not isinstance(raw, dict):
                    continue
                try:
                    date.fromisoformat(key)
                except ValueError:
                    continue
                parsed[key] = DailyActivity(
                    date=key,
                    active_seconds=_nonnegative_number(raw.get("active_seconds")),
                    idle_seconds=_nonnegative_number(raw.get("idle_seconds")),
                    water_count=_nonnegative_int(raw.get("water_count")),
                    hydration_elapsed_seconds=_nonnegative_number(
                        raw.get("hydration_elapsed_seconds")
                    ),
                    snooze_remaining_seconds=_nonnegative_number(
                        raw.get("snooze_remaining_seconds")
                    ),
                )
        return cls(parsed, today=today)


def load_activity(
    path: Path,
    *,
    today: date | datetime | None = None,
) -> ActivityTracker:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        payload = {}
    return ActivityTracker.from_dict(payload, today=today)


def save_activity(tracker: ActivityTracker, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(tracker.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
