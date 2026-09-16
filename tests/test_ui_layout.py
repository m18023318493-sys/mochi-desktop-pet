import math
import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from PIL import Image

from mochi_pet import HYDRATION_REMINDER_TEXT, MochiPet
from pet_core import (
    DEFAULT_SETTINGS,
    HYDRATION_BUBBLE_FONT_SIZE,
    NORMAL_BUBBLE_FONT_SIZE,
    save_settings,
)


class UiLayoutTests(unittest.TestCase):
    def test_custom_avatar_draws_no_floor_shadow_without_a_display(self):
        class FakeFrame:
            def width(self):
                return 100

        class FakeCanvas:
            def __init__(self):
                self.image_calls = []

            def create_image(self, *args, **kwargs):
                self.image_calls.append((args, kwargs))

            def create_oval(self, *args, **kwargs):
                raise AssertionError("custom avatars must not draw a floor shadow")

        pet = object.__new__(MochiPet)
        pet.direction = -1
        pet.custom_avatar_frames = {-1: FakeFrame()}
        pet.canvas = FakeCanvas()

        pet._draw_custom_avatar(now=0.0, walking=False, bob=0.0)

        self.assertEqual(len(pet.canvas.image_calls), 1)

    def test_bubbles_stay_above_maximum_custom_avatar(self):
        try:
            root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk display is unavailable: {error}")
        root.withdraw()

        try:
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                config_path = folder / "settings.json"
                activity_path = folder / "activity.json"
                settings = dict(DEFAULT_SETTINGS)
                settings.update(
                    {
                        "appearance_mode": "custom",
                        "avatar_scale_percent": 100,
                        "auto_wander": False,
                        "always_on_top": False,
                    }
                )
                save_settings(settings, config_path)
                Image.new("RGBA", (500, 1000), (32, 64, 96, 255)).save(
                    folder / "custom_avatar.png"
                )

                pet = MochiPet(
                    root,
                    auto_wander_override=False,
                    config_path=config_path,
                    activity_path=activity_path,
                )
                if pet.after_id is not None:
                    root.after_cancel(pet.after_id)
                    pet.after_id = None

                worst_upward_bob_time = (3 * math.pi / 2) / 9
                cases = (
                    ("普通中文提示", False),
                    (HYDRATION_REMINDER_TEXT, True),
                )
                for message, emphasized in cases:
                    pet._set_message(
                        message,
                        12.0,
                        emphasized=emphasized,
                        now=worst_upward_bob_time,
                    )
                    pet._draw(worst_upward_bob_time, walking=True)
                    root.update_idletasks()

                    bubble = pet.canvas.bbox("message-bubble")
                    avatar = pet.canvas.bbox("pet-avatar")
                    self.assertIsNotNone(bubble)
                    self.assertIsNotNone(avatar)
                    self.assertFalse(pet.canvas.find_withtag("pet-shadow"))
                    self.assertLess(
                        bubble[3],
                        avatar[1],
                        f"bubble {bubble} overlaps avatar {avatar}",
                    )

                self.assertGreater(
                    HYDRATION_BUBBLE_FONT_SIZE,
                    NORMAL_BUBBLE_FONT_SIZE * 1.5,
                )
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
