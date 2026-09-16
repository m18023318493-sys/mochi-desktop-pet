"""Safe, local-only image helpers for Mochi's custom appearance."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


AVATAR_SCALE_OPTIONS = (60, 75, 90, 100)
DEFAULT_AVATAR_SCALE = 90
MAX_IMPORT_PIXELS = 40_000_000
MAX_IMPORT_BYTES = 20 * 1024 * 1024
MAX_STORED_EDGE = 1600
AVATAR_MAX_WIDTH = 150
AVATAR_MAX_HEIGHT = 172


class AvatarImageError(ValueError):
    """Raised when a selected file cannot be used as a custom appearance."""


def avatar_path_for_settings(settings_file: Path) -> Path:
    """Keep the processed avatar beside Mochi's other per-user local data."""
    return settings_file.with_name("custom_avatar.png")


def validate_image_size(width: int, height: int) -> None:
    """Reject empty or unexpectedly large images before decoding all pixels."""
    if width <= 0 or height <= 0:
        raise AvatarImageError("所选图片的尺寸无效。")
    if width * height > MAX_IMPORT_PIXELS:
        raise AvatarImageError(
            "所选图片像素过大，请使用低于 4000 万像素的图片。"
        )


def _open_rgba(path: Path) -> Image.Image:
    try:
        if path.stat().st_size > MAX_IMPORT_BYTES:
            raise AvatarImageError(
                "所选图片文件过大，请使用小于 20 MB 的图片。"
            )
        with Image.open(path) as source:
            validate_image_size(*source.size)
            source.seek(0)
            image = ImageOps.exif_transpose(source).convert("RGBA")
            image.load()
    except AvatarImageError:
        raise
    except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError) as error:
        raise AvatarImageError(
            "无法读取该图片，请尝试 PNG、JPEG、WebP、GIF 或 BMP 文件。"
        ) from error

    content_box = image.getchannel("A").getbbox()
    if content_box is None:
        raise AvatarImageError("所选图片完全透明。")
    image = image.crop(content_box)
    image.info.clear()
    return image


def import_avatar(source_path: Path, destination_path: Path) -> tuple[int, int]:
    """Re-encode one local image as a bounded PNG without metadata."""
    image = _open_rgba(source_path)
    image.thumbnail((MAX_STORED_EDGE, MAX_STORED_EDGE), Image.Resampling.LANCZOS)

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination_path.with_name(f"{destination_path.stem}.tmp.png")
    try:
        image.save(temporary, format="PNG", optimize=True)
        temporary.replace(destination_path)
    except OSError as error:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise AvatarImageError("无法在本机保存自定义图片。") from error
    return image.size


def load_avatar_frames(
    path: Path,
    scale_percent: int,
) -> tuple[Image.Image, Image.Image]:
    """Return cached-ready left/right RGBA frames sized for the pet window."""
    if scale_percent not in AVATAR_SCALE_OPTIONS:
        scale_percent = DEFAULT_AVATAR_SCALE
    image = _open_rgba(path)
    max_width = max(1, AVATAR_MAX_WIDTH * scale_percent // 100)
    max_height = max(1, AVATAR_MAX_HEIGHT * scale_percent // 100)
    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    if image.width <= 0 or image.height <= 0:
        raise AvatarImageError("无法调整所选图片的大小。")
    return ImageOps.mirror(image), image.copy()
