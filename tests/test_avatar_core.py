import tempfile
import unittest
from pathlib import Path

from PIL import Image

from avatar_core import (
    AVATAR_MAX_HEIGHT,
    AVATAR_MAX_WIDTH,
    AvatarImageError,
    avatar_path_for_settings,
    import_avatar,
    load_avatar_frames,
    validate_image_size,
)


class AvatarCoreTests(unittest.TestCase):
    def test_avatar_path_is_local_and_does_not_retain_original_path(self):
        settings = Path("profile") / "MochiDesktopPet" / "settings.json"
        self.assertEqual(
            avatar_path_for_settings(settings),
            settings.with_name("custom_avatar.png"),
        )

    def test_import_preserves_alpha_crops_padding_and_strips_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "人物 photo.png"
            destination = folder / "profile" / "custom_avatar.png"
            image = Image.new("RGBA", (30, 40), (0, 0, 0, 0))
            for x in range(8, 22):
                for y in range(5, 35):
                    image.putpixel((x, y), (220, 30, 40, 180 if x == 8 else 255))
            image.save(source, pnginfo=None)

            size = import_avatar(source, destination)

            self.assertEqual(size, (14, 30))
            with Image.open(destination) as imported:
                self.assertEqual(imported.mode, "RGBA")
                self.assertEqual(imported.size, (14, 30))
                self.assertEqual(imported.getpixel((0, 0))[3], 180)
                self.assertEqual(len(imported.getexif()), 0)
            self.assertFalse(destination.with_name("custom_avatar.tmp.png").exists())

    def test_load_frames_fit_bounds_and_mirror_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom_avatar.png"
            image = Image.new("RGBA", (20, 40), (0, 0, 255, 255))
            for x in range(10):
                for y in range(40):
                    image.putpixel((x, y), (255, 0, 0, 255))
            image.save(path)

            left, right = load_avatar_frames(path, 100)

            self.assertLessEqual(right.width, AVATAR_MAX_WIDTH)
            self.assertLessEqual(right.height, AVATAR_MAX_HEIGHT)
            self.assertEqual(left.getpixel((0, 0)), right.getpixel((right.width - 1, 0)))
            self.assertEqual(left.getpixel((left.width - 1, 0)), right.getpixel((0, 0)))
            self.assertEqual(left.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes(), right.tobytes())

    def test_invalid_scale_falls_back_to_safe_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom_avatar.png"
            Image.new("RGBA", (500, 1000), (255, 0, 0, 255)).save(path)
            _left, right = load_avatar_frames(path, 999)
        self.assertLessEqual(right.width, AVATAR_MAX_WIDTH)
        self.assertLessEqual(right.height, AVATAR_MAX_HEIGHT)

    def test_transparent_or_corrupt_image_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            destination = folder / "custom_avatar.png"
            destination.write_bytes(b"previous-valid-copy")
            before = destination.read_bytes()

            transparent = folder / "transparent.png"
            invisible = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
            invisible.putpixel((5, 5), (255, 0, 0, 0))
            invisible.save(transparent)
            with self.assertRaises(AvatarImageError):
                import_avatar(transparent, destination)
            self.assertEqual(destination.read_bytes(), before)

            corrupt = folder / "broken.jpg"
            corrupt.write_bytes(b"not an image")
            with self.assertRaises(AvatarImageError):
                import_avatar(corrupt, destination)
            self.assertEqual(destination.read_bytes(), before)

    def test_excessive_pixel_count_is_rejected(self):
        with self.assertRaises(AvatarImageError):
            validate_image_size(10_000, 10_000)


if __name__ == "__main__":
    unittest.main()
