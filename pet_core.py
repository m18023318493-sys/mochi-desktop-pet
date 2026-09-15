"""Pure, display-independent helpers for Mochi Desktop Pet."""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any


WINDOW_WIDTH = 176
WINDOW_HEIGHT = 206
VERSION = "0.1.0"
WorkArea = tuple[int, int, int, int]

DEFAULT_SETTINGS: dict[str, Any] = {
    "x": None,
    "y": None,
    "auto_wander": True,
    "always_on_top": True,
}


def clamp(value: int | float, lower: int | float, upper: int | float) -> int | float:
    """Return *value* constrained to the inclusive range."""
    return max(lower, min(value, upper))


def settings_path() -> Path:
    """Return the per-user settings location without touching the file system."""
    if os.name == "nt" and os.environ.get("APPDATA"):
        base = Path(os.environ["APPDATA"])
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "MochiDesktopPet" / "settings.json"


def normalize_position(
    x: object,
    y: object,
    desktop_left: int,
    desktop_top: int,
    desktop_width: int,
    desktop_height: int,
) -> tuple[int, int]:
    """Turn persisted coordinates into a visible virtual-desktop position."""
    max_x = desktop_left + max(0, desktop_width - WINDOW_WIDTH)
    max_y = desktop_top + max(0, desktop_height - WINDOW_HEIGHT)
    default_x = max(desktop_left, max_x - 32)
    default_y = max(desktop_top, max_y - 72)

    try:
        parsed_x = int(x) if x is not None else default_x
        parsed_y = int(y) if y is not None else default_y
    except (TypeError, ValueError):
        parsed_x, parsed_y = default_x, default_y

    return (
        int(clamp(parsed_x, desktop_left, max_x)),
        int(clamp(parsed_y, desktop_top, max_y)),
    )


def geometry_at(x: int, y: int, width: int | None = None, height: int | None = None) -> str:
    """Build Tk geometry text that also works with negative monitor coordinates."""
    prefix = f"{width}x{height}" if width is not None and height is not None else ""
    x_part = f"+{x}"
    y_part = f"+{y}"
    return f"{prefix}{x_part}{y_part}"


def monitor_for_point(x: int, y: int, work_areas: list[WorkArea]) -> WorkArea:
    """Return the work area containing a point, or the nearest one."""
    if not work_areas:
        raise ValueError("at least one monitor work area is required")

    for left, top, width, height in work_areas:
        if left <= x < left + width and top <= y < top + height:
            return left, top, width, height

    def distance_squared(area: WorkArea) -> int:
        left, top, width, height = area
        nearest_x = int(clamp(x, left, left + max(0, width - 1)))
        nearest_y = int(clamp(y, top, top + max(0, height - 1)))
        return (x - nearest_x) ** 2 + (y - nearest_y) ** 2

    return min(work_areas, key=distance_squared)


def clamp_position_to_work_area(x: int, y: int, work_area: WorkArea) -> tuple[int, int]:
    """Keep the entire pet window inside one monitor's usable work area."""
    left, top, width, height = work_area
    max_x = left + max(0, width - WINDOW_WIDTH)
    max_y = top + max(0, height - WINDOW_HEIGHT)
    return int(clamp(x, left, max_x)), int(clamp(y, top, max_y))


def normalize_position_on_monitors(
    x: object,
    y: object,
    work_areas: list[WorkArea],
) -> tuple[int, int]:
    """Restore a saved position to the right monitor without using screen gaps."""
    if not work_areas:
        work_areas = [(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)]

    if type(x) is int and type(y) is int:
        area = monitor_for_point(x + WINDOW_WIDTH // 2, y + WINDOW_HEIGHT // 2, work_areas)
        return clamp_position_to_work_area(x, y, area)

    left, top, width, height = work_areas[0]
    return normalize_position(None, None, left, top, width, height)


def load_settings(path: Path | None = None) -> dict[str, Any]:
    """Load settings defensively, falling back to safe defaults."""
    result = dict(DEFAULT_SETTINGS)
    target = path or settings_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return result

    if not isinstance(data, dict):
        return result
    if type(data.get("x")) is int:
        result["x"] = data["x"]
    if type(data.get("y")) is int:
        result["y"] = data["y"]
    if isinstance(data.get("auto_wander"), bool):
        result["auto_wander"] = data["auto_wander"]
    if isinstance(data.get("always_on_top"), bool):
        result["always_on_top"] = data["always_on_top"]
    return result


def save_settings(settings: dict[str, Any], path: Path | None = None) -> None:
    """Persist the small preferences file atomically."""
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(settings, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def choose_wander_target(
    current_x: int,
    desktop_left: int,
    desktop_width: int,
    window_width: int = WINDOW_WIDTH,
    rng: Any = random,
) -> int:
    """Choose an on-screen horizontal destination that is visibly different."""
    max_x = desktop_left + max(0, desktop_width - window_width)
    if max_x == desktop_left:
        return desktop_left

    target = rng.randint(desktop_left, max_x)
    minimum_move = min(80, max_x - desktop_left)
    if abs(target - current_x) < minimum_move:
        midpoint = desktop_left + (max_x - desktop_left) / 2
        direction = 1 if current_x < midpoint else -1
        target = int(clamp(current_x + direction * minimum_move, desktop_left, max_x))
    return target
