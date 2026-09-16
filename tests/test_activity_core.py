import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from activity_core import (
    DAY_FIELDS,
    MAX_SAMPLE_SECONDS,
    RETENTION_DAYS,
    ActivityTracker,
    DailyActivity,
    format_duration_zh,
    is_quiet_hour,
    load_activity,
    save_activity,
    wrapped_tick_elapsed_seconds,
)


TODAY = date(2026, 9, 16)


class ActivityCoreTests(unittest.TestCase):
    def test_chinese_duration_format(self):
        self.assertEqual(format_duration_zh(20), "不足 1 分钟")
        self.assertEqual(format_duration_zh(120), "2 分钟")
        self.assertEqual(format_duration_zh(3720), "1 小时 2 分钟")

    def test_samples_are_aggregated_and_sleep_gaps_are_capped(self):
        tracker = ActivityTracker(today=TODAY)
        tracker.record_sample(
            900,
            is_idle=False,
            count_activity=True,
            count_hydration=True,
        )
        tracker.record_sample(
            2,
            is_idle=True,
            count_activity=True,
            count_hydration=True,
        )
        self.assertEqual(tracker.today.active_seconds, MAX_SAMPLE_SECONDS)
        self.assertEqual(tracker.today.idle_seconds, 2)
        self.assertEqual(tracker.today.hydration_elapsed_seconds, MAX_SAMPLE_SECONDS)

    def test_activity_statistics_can_pause_without_stopping_hydration_clock(self):
        tracker = ActivityTracker(today=TODAY)
        tracker.record_sample(
            4,
            is_idle=False,
            count_activity=False,
            count_hydration=True,
        )
        self.assertEqual(tracker.today.active_seconds, 0)
        self.assertEqual(tracker.today.hydration_elapsed_seconds, 4)

    def test_idle_time_does_not_advance_hydration(self):
        tracker = ActivityTracker(today=TODAY)
        tracker.record_sample(
            5,
            is_idle=True,
            count_activity=True,
            count_hydration=True,
        )
        self.assertEqual(tracker.today.idle_seconds, 5)
        self.assertEqual(tracker.today.hydration_elapsed_seconds, 0)

    def test_reminder_threshold_snooze_and_water_reset(self):
        tracker = ActivityTracker(today=TODAY)
        tracker.today.hydration_elapsed_seconds = 60 * 60 - 1
        tracker.record_sample(
            1,
            is_idle=False,
            count_activity=True,
            count_hydration=True,
        )
        self.assertTrue(tracker.hydration_due(60, hour=9, user_is_idle=False))

        tracker.mark_reminded()
        self.assertFalse(tracker.hydration_due(60, hour=9, user_is_idle=False))
        for _ in range(120):
            tracker.record_sample(
                5,
                is_idle=False,
                count_activity=True,
                count_hydration=True,
            )
        self.assertTrue(tracker.hydration_due(60, hour=9, user_is_idle=False))

        tracker.mark_water()
        self.assertEqual(tracker.today.water_count, 1)
        self.assertEqual(tracker.today.hydration_elapsed_seconds, 0)
        self.assertFalse(tracker.hydration_due(60, hour=9, user_is_idle=False))

    def test_quiet_hours_and_idle_defer_reminders(self):
        tracker = ActivityTracker(today=TODAY)
        tracker.today.hydration_elapsed_seconds = 3600
        self.assertTrue(is_quiet_hour(22))
        self.assertTrue(is_quiet_hour(7))
        self.assertFalse(is_quiet_hour(8))
        self.assertFalse(is_quiet_hour(21))
        self.assertFalse(tracker.hydration_due(60, hour=22, user_is_idle=False))
        self.assertFalse(tracker.hydration_due(60, hour=8, user_is_idle=True))
        self.assertTrue(tracker.hydration_due(60, hour=8, user_is_idle=False))

    def test_midnight_creates_a_new_daily_bucket(self):
        tracker = ActivityTracker(today=TODAY)
        tracker.record_sample(
            3,
            is_idle=False,
            count_activity=True,
            count_hydration=True,
        )
        tomorrow = TODAY + timedelta(days=1)
        tracker.record_sample(
            2,
            is_idle=True,
            count_activity=True,
            count_hydration=True,
            today=tomorrow,
        )
        self.assertEqual(tracker.days[TODAY.isoformat()].active_seconds, 3)
        self.assertEqual(tracker.days[tomorrow.isoformat()].idle_seconds, 2)

    def test_history_is_limited_to_thirty_daily_totals(self):
        days = {
            (TODAY - timedelta(days=index)).isoformat(): DailyActivity(
                date=(TODAY - timedelta(days=index)).isoformat()
            )
            for index in range(40)
        }
        tracker = ActivityTracker(days, today=TODAY)
        self.assertLessEqual(len(tracker.days), RETENTION_DAYS)
        self.assertIn(TODAY.isoformat(), tracker.days)

    def test_serialization_uses_a_strict_privacy_allowlist(self):
        tracker = ActivityTracker(today=TODAY)
        payload = tracker.to_dict()
        self.assertEqual(set(payload), {"schema_version", "days"})
        for day in payload["days"].values():
            self.assertEqual(set(day), DAY_FIELDS)
        serialized = json.dumps(payload).lower()
        for forbidden in (
            "keystroke",
            "typed_text",
            "application",
            "process",
            "window_title",
            "screenshot",
            "clipboard",
            "raw_event",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_unknown_fields_and_corrupt_files_are_ignored(self):
        payload = {
            "schema_version": 99,
            "days": {
                TODAY.isoformat(): {
                    "active_seconds": 12,
                    "key": "secret",
                    "application": "private.exe",
                }
            },
        }
        tracker = ActivityTracker.from_dict(payload, today=TODAY)
        self.assertEqual(tracker.today.active_seconds, 12)
        self.assertNotIn("key", tracker.to_dict()["days"][TODAY.isoformat()])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "activity.json"
            path.write_text("not json", encoding="utf-8")
            loaded = load_activity(path, today=TODAY)
        self.assertEqual(loaded.today.active_seconds, 0)

    def test_activity_file_round_trip_is_atomic(self):
        tracker = ActivityTracker(today=TODAY)
        tracker.today.active_seconds = 42.5
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "activity.json"
            save_activity(tracker, path)
            loaded = load_activity(path, today=TODAY)
            self.assertFalse(path.with_suffix(".tmp").exists())
        self.assertEqual(loaded.today.active_seconds, 42.5)

    def test_windows_tick_wraparound_is_handled(self):
        self.assertEqual(wrapped_tick_elapsed_seconds(0x00000100, 0xFFFFFF00), 0.512)


if __name__ == "__main__":
    unittest.main()
