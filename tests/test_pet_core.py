import json
import random
import tempfile
import unittest
from pathlib import Path

from pet_core import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    VERSION,
    choose_wander_target,
    clamp,
    clamp_position_to_work_area,
    geometry_at,
    load_settings,
    monitor_for_point,
    normalize_position,
    normalize_position_on_monitors,
    save_settings,
)


class PetCoreTests(unittest.TestCase):
    def test_clamp_keeps_values_inside_range(self):
        self.assertEqual(clamp(-4, 0, 10), 0)
        self.assertEqual(clamp(7, 0, 10), 7)
        self.assertEqual(clamp(14, 0, 10), 10)

    def test_normalize_position_supports_virtual_desktop_bounds(self):
        left, top, width, height = -1920, -120, 3840, 1200
        self.assertEqual(
            normalize_position(-5000, 5000, left, top, width, height),
            (left, top + height - WINDOW_HEIGHT),
        )
        default_x, default_y = normalize_position(None, None, left, top, width, height)
        self.assertGreaterEqual(default_x, left)
        self.assertLessEqual(default_x, left + width - WINDOW_WIDTH)
        self.assertGreaterEqual(default_y, top)
        self.assertLessEqual(default_y, top + height - WINDOW_HEIGHT)

    def test_geometry_handles_negative_monitor_coordinates(self):
        self.assertEqual(geometry_at(-800, 24), "+-800+24")
        self.assertEqual(geometry_at(-800, -40, 176, 206), "176x206+-800+-40")

    def test_monitor_selection_avoids_gaps_between_uneven_screens(self):
        monitors = [(0, 0, 1920, 1040), (-1280, 200, 1280, 800)]
        self.assertEqual(monitor_for_point(300, 300, monitors), monitors[0])
        self.assertEqual(monitor_for_point(-600, 500, monitors), monitors[1])
        # This point is in the virtual bounding rectangle but not on a monitor.
        self.assertEqual(monitor_for_point(-600, 40, monitors), monitors[1])

    def test_saved_position_is_clamped_to_one_real_monitor(self):
        monitors = [(0, 0, 1920, 1040), (-1280, 200, 1280, 800)]
        x, y = normalize_position_on_monitors(-800, -300, monitors)
        selected = monitor_for_point(x + WINDOW_WIDTH // 2, y + WINDOW_HEIGHT // 2, monitors)
        self.assertEqual((x, y), clamp_position_to_work_area(x, y, selected))

    def test_corrupt_settings_fall_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("{not json", encoding="utf-8")
            settings = load_settings(path)
        self.assertIsNone(settings["x"])
        self.assertIsNone(settings["y"])
        self.assertTrue(settings["auto_wander"])
        self.assertTrue(settings["always_on_top"])

    def test_boolean_coordinates_are_not_accepted_as_integers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"x": true, "y": false}', encoding="utf-8")
            settings = load_settings(path)
        self.assertIsNone(settings["x"])
        self.assertIsNone(settings["y"])

    def test_settings_round_trip_and_ignore_unknown_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "settings.json"
            expected = {
                "x": -620,
                "y": 240,
                "auto_wander": False,
                "always_on_top": True,
            }
            save_settings(expected, path)
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["token"] = "must-not-be-loaded"
            path.write_text(json.dumps(raw), encoding="utf-8")
            loaded = load_settings(path)

            for key, value in expected.items():
                self.assertEqual(loaded[key], value)
            self.assertNotIn("token", loaded)
            self.assertFalse(loaded["activity_monitoring"])
            self.assertTrue(loaded["hydration_reminders"])
            self.assertFalse(path.with_suffix(".tmp").exists())

    def test_legacy_settings_keep_preferences_and_do_not_opt_in_to_tracking(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                '{"x": 120, "y": 240, "auto_wander": false, "always_on_top": false}',
                encoding="utf-8",
            )
            loaded = load_settings(path)
        self.assertEqual((loaded["x"], loaded["y"]), (120, 240))
        self.assertFalse(loaded["auto_wander"])
        self.assertFalse(loaded["always_on_top"])
        self.assertFalse(loaded["activity_monitoring"])
        self.assertTrue(loaded["hydration_reminders"])
        self.assertEqual(loaded["hydration_interval_minutes"], 60)

    def test_wander_target_stays_visible_and_moves(self):
        rng = random.Random(9)
        left, width = -1280, 3200
        current = 100
        target = choose_wander_target(current, left, width, rng=rng)
        self.assertGreaterEqual(target, left)
        self.assertLessEqual(target, left + width - WINDOW_WIDTH)
        self.assertGreaterEqual(abs(target - current), 80)

    def test_release_versions_stay_in_sync(self):
        project_root = Path(__file__).resolve().parents[1]
        pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
        changelog = (project_root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f'version = "{VERSION}"', pyproject)
        self.assertIn(f"## {VERSION} -", changelog)


if __name__ == "__main__":
    unittest.main()
