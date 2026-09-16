import json
import random
import tempfile
import unittest
from pathlib import Path

from avatar_core import AVATAR_MAX_HEIGHT
from pet_core import (
    AVATAR_BASE_Y,
    HYDRATION_BUBBLE_BOTTOM,
    HYDRATION_BUBBLE_FONT_SIZE,
    NORMAL_BUBBLE_FONT_SIZE,
    PET_Y_OFFSET,
    WALKING_BOB_AMPLITUDE,
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
    saved_y_from_window,
    window_y_from_saved,
)


class PetCoreTests(unittest.TestCase):
    def test_bubbles_clear_maximum_custom_avatar(self):
        highest_avatar_pixel = (
            AVATAR_BASE_Y - AVATAR_MAX_HEIGHT - WALKING_BOB_AMPLITUDE
        )
        self.assertGreaterEqual(highest_avatar_pixel - HYDRATION_BUBBLE_BOTTOM, 16)
        self.assertGreater(HYDRATION_BUBBLE_FONT_SIZE, NORMAL_BUBBLE_FONT_SIZE * 1.5)

    def test_saved_stage_y_round_trips_across_taller_layout(self):
        self.assertIsNone(window_y_from_saved(None))
        self.assertEqual(window_y_from_saved(800), 800 - PET_Y_OFFSET)
        self.assertEqual(saved_y_from_window(window_y_from_saved(800)), 800)

    def test_old_bottom_position_keeps_stage_in_place(self):
        old_window_height = 206
        work_area = (0, 0, 1920, 1040)
        old_root_y = work_area[3] - old_window_height
        new_root_y = window_y_from_saved(old_root_y)
        _x, normalized_y = normalize_position_on_monitors(100, new_root_y, [work_area])
        self.assertEqual(normalized_y + PET_Y_OFFSET, old_root_y)

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
        self.assertEqual(settings["appearance_mode"], "mochi")
        self.assertEqual(settings["avatar_scale_percent"], 90)

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
                "appearance_mode": "custom",
                "avatar_scale_percent": 75,
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
        self.assertEqual(loaded["appearance_mode"], "mochi")
        self.assertEqual(loaded["avatar_scale_percent"], 90)

    def test_invalid_appearance_preferences_fall_back_safely(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                '{"appearance_mode": "../../photo", "avatar_scale_percent": 999}',
                encoding="utf-8",
            )
            loaded = load_settings(path)
        self.assertEqual(loaded["appearance_mode"], "mochi")
        self.assertEqual(loaded["avatar_scale_percent"], 90)

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
