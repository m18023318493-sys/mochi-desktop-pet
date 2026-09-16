"""Mochi Desktop Pet — a tiny, dependency-free Tkinter companion."""

from __future__ import annotations

import argparse
import ctypes
import math
import os
import platform
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from ctypes import wintypes

import tkinter as tk

from activity_core import (
    ActivityTracker,
    format_duration,
    load_activity,
    save_activity,
    wrapped_tick_elapsed_seconds,
)

from pet_core import (
    HYDRATION_INTERVAL_OPTIONS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    VERSION,
    choose_wander_target,
    clamp_position_to_work_area,
    geometry_at,
    load_settings,
    monitor_for_point,
    normalize_position_on_monitors,
    save_settings,
    settings_path,
)


APP_NAME = "Mochi Desktop Pet"
CHROMA_KEY = "#010203"
FALLBACK_BACKGROUND = "#fff7ed"


def windows_idle_seconds() -> float | None:
    """Read only the elapsed idle time; never install input hooks or read events."""
    if os.name != "nt":
        return None
    try:
        class LastInputInfo(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("dwTime", wintypes.DWORD),
            ]

        info = LastInputInfo()
        info.cbSize = ctypes.sizeof(LastInputInfo)
        get_last_input = ctypes.windll.user32.GetLastInputInfo
        get_last_input.argtypes = [ctypes.POINTER(LastInputInfo)]
        get_last_input.restype = wintypes.BOOL
        get_tick_count = ctypes.windll.kernel32.GetTickCount
        get_tick_count.argtypes = []
        get_tick_count.restype = wintypes.DWORD
        if not get_last_input(ctypes.byref(info)):
            return None
        return wrapped_tick_elapsed_seconds(get_tick_count(), info.dwTime)
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def monitor_work_areas(root: tk.Tk) -> list[tuple[int, int, int, int]]:
    """Return real monitor work areas with the Windows primary monitor first."""
    if os.name == "nt":
        try:
            class Rect(ctypes.Structure):
                _fields_ = [
                    ("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG),
                ]

            class MonitorInfo(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", Rect),
                    ("rcWork", Rect),
                    ("dwFlags", wintypes.DWORD),
                ]

            callback_type = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HMONITOR,
                wintypes.HDC,
                ctypes.POINTER(Rect),
                wintypes.LPARAM,
            )
            get_monitor_info = ctypes.windll.user32.GetMonitorInfoW
            get_monitor_info.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MonitorInfo)]
            get_monitor_info.restype = wintypes.BOOL
            enum_monitors = ctypes.windll.user32.EnumDisplayMonitors
            enum_monitors.argtypes = [
                wintypes.HDC,
                ctypes.POINTER(Rect),
                callback_type,
                wintypes.LPARAM,
            ]
            enum_monitors.restype = wintypes.BOOL
            collected: list[tuple[bool, tuple[int, int, int, int]]] = []

            def collect(monitor: int, _dc: int, _rect: object, _data: int) -> bool:
                info = MonitorInfo()
                info.cbSize = ctypes.sizeof(MonitorInfo)
                if get_monitor_info(monitor, ctypes.byref(info)):
                    rect = info.rcWork
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top
                    if width > 0 and height > 0:
                        collected.append((bool(info.dwFlags & 1), (rect.left, rect.top, width, height)))
                return True

            callback = callback_type(collect)
            enum_monitors(None, None, callback, 0)
            if collected:
                collected.sort(key=lambda item: not item[0])
                return [area for _primary, area in collected]
        except (AttributeError, OSError, TypeError, ValueError):
            pass
    return [(0, 0, root.winfo_screenwidth(), root.winfo_screenheight())]


class MochiPet:
    """The borderless pet window and its animation loop."""

    messages = (
        "Need a tiny break?",
        "You're doing great!",
        "Mochi believes in you.",
        "Time to stretch?",
        "Hello from your desktop!",
    )
    happy_messages = (
        "Purr... thank you!",
        "That tickles!",
        "Best human ever!",
        "Mochi is happy!",
    )

    def __init__(
        self,
        root: tk.Tk,
        *,
        auto_wander_override: bool | None = None,
        activity_monitoring_override: bool | None = None,
        hydration_reminders_override: bool | None = None,
        config_path: Path | None = None,
        activity_path: Path | None = None,
    ) -> None:
        self.root = root
        self.config_path = config_path
        self.rng = random.Random()
        self.settings = load_settings(config_path)
        if auto_wander_override is not None:
            self.settings["auto_wander"] = auto_wander_override
        if activity_monitoring_override is not None:
            self.settings["activity_monitoring"] = activity_monitoring_override
        if hydration_reminders_override is not None:
            self.settings["hydration_reminders"] = hydration_reminders_override
        self.activity_path = activity_path or (config_path or settings_path()).with_name(
            "activity.json"
        )
        self.activity_tracker: ActivityTracker = load_activity(self.activity_path)

        self.work_areas = monitor_work_areas(root)
        x, y = normalize_position_on_monitors(
            self.settings["x"],
            self.settings["y"],
            self.work_areas,
        )

        root.title(APP_NAME)
        root.overrideredirect(True)
        root.geometry(geometry_at(x, y, WINDOW_WIDTH, WINDOW_HEIGHT))
        root.resizable(False, False)

        self.window_background = CHROMA_KEY
        root.configure(background=self.window_background)
        if platform.system() == "Windows":
            try:
                root.wm_attributes("-transparentcolor", CHROMA_KEY)
            except tk.TclError:
                self.window_background = FALLBACK_BACKGROUND
                root.configure(background=self.window_background)
        else:
            self.window_background = FALLBACK_BACKGROUND
            root.configure(background=self.window_background)
            try:
                root.wm_attributes("-alpha", 0.98)
            except tk.TclError:
                pass

        self.auto_wander = tk.BooleanVar(value=self.settings["auto_wander"])
        self.always_on_top = tk.BooleanVar(value=self.settings["always_on_top"])
        self.activity_monitoring = tk.BooleanVar(
            value=self.settings["activity_monitoring"]
        )
        self.hydration_reminders = tk.BooleanVar(
            value=self.settings["hydration_reminders"]
        )
        self.hydration_interval = tk.IntVar(
            value=self.settings["hydration_interval_minutes"]
        )
        root.wm_attributes("-topmost", self.always_on_top.get())

        self.canvas = tk.Canvas(
            root,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            background=self.window_background,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
        )
        self.canvas.pack(fill="both", expand=True)

        self.menu = tk.Menu(root, tearoff=False)
        self.menu.add_command(label="I drank water", command=self._log_water)
        self.menu.add_command(label="Today's activity", command=self._show_today_stats)
        self.menu.add_separator()
        self.menu.add_checkbutton(
            label="Track active / idle time",
            variable=self.activity_monitoring,
            command=self._toggle_activity_monitoring,
        )
        self.menu.add_checkbutton(
            label="Hydration reminders",
            variable=self.hydration_reminders,
            command=self._toggle_hydration_reminders,
        )
        interval_menu = tk.Menu(self.menu, tearoff=False)
        for minutes in HYDRATION_INTERVAL_OPTIONS:
            interval_menu.add_radiobutton(
                label=f"Every {minutes} minutes",
                variable=self.hydration_interval,
                value=minutes,
                command=self._set_hydration_interval,
            )
        self.menu.add_cascade(label="Reminder interval", menu=interval_menu)
        self.menu.add_command(
            label="Delete activity history...",
            command=self._delete_activity_history,
        )
        self.menu.add_separator()
        self.menu.add_checkbutton(
            label="Auto-wander",
            variable=self.auto_wander,
            command=self._toggle_wander,
        )
        self.menu.add_checkbutton(
            label="Always on top",
            variable=self.always_on_top,
            command=self._toggle_topmost,
        )
        self.menu.add_command(label="Reset position", command=self._reset_position)
        self.menu.add_separator()
        self.menu.add_command(label="Quit Mochi", command=self.close)

        self.dragging = False
        self.closing = False
        self.after_id: str | None = None
        self.drag_offset = (0, 0)
        self.direction = -1
        self.walk_target_x: int | None = None
        now = time.monotonic()
        self.next_walk_at = now + self.rng.uniform(3.0, 6.0)
        self.next_monitor_refresh_at = now + 2.0
        self.next_blink_at = now + self.rng.uniform(2.0, 4.0)
        self.blink_until = 0.0
        self.happy_until = 0.0
        self.message = "Hi! I'm Mochi."
        self.message_until = now + 3.5
        self.next_message_at = now + self.rng.uniform(18.0, 30.0)
        self.hearts: list[tuple[float, float, float]] = []
        self.water_effect_started = 0.0
        self.water_effect_until = 0.0
        self.last_activity_sample_at = now
        self.next_activity_save_at = now + 60.0
        self.user_is_idle = False

        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._stop_drag)
        self.canvas.bind("<Double-Button-1>", self._interact)
        self.canvas.bind("<Button-3>", self._show_menu)
        self.canvas.bind("<Button-2>", self._show_menu)
        root.bind("<Escape>", lambda _event: self.close())
        root.protocol("WM_DELETE_WINDOW", self.close)

        if activity_monitoring_override is not None or hydration_reminders_override is not None:
            self._persist()
        self._tick()

    def _start_drag(self, event: tk.Event) -> None:
        self.dragging = True
        self.walk_target_x = None
        self.drag_offset = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )

    def _drag(self, event: tk.Event) -> None:
        area = monitor_for_point(event.x_root, event.y_root, self.work_areas)
        x, y = clamp_position_to_work_area(
            event.x_root - self.drag_offset[0],
            event.y_root - self.drag_offset[1],
            area,
        )
        self.root.geometry(geometry_at(x, y))

    def _stop_drag(self, _event: tk.Event) -> None:
        self.dragging = False
        self._remember_position()
        self.next_walk_at = time.monotonic() + self.rng.uniform(4.0, 8.0)

    def _interact(self, _event: tk.Event) -> None:
        now = time.monotonic()
        self.happy_until = now + 2.2
        self.message = self.rng.choice(self.happy_messages)
        self.message_until = now + 2.8
        self.next_message_at = now + self.rng.uniform(20.0, 35.0)
        for offset_x, delay in ((-19, 0.0), (2, 0.12), (22, 0.24)):
            self.hearts.append((88 + offset_x, 102.0, now + delay))

    def _show_menu(self, event: tk.Event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _toggle_activity_monitoring(self) -> None:
        state = self.activity_monitoring.get()
        self.message = "Activity totals on." if state else "Activity totals paused."
        self.message_until = time.monotonic() + 3.0
        self._persist()

    def _toggle_hydration_reminders(self) -> None:
        state = self.hydration_reminders.get()
        self.message = "Water reminders on." if state else "Water reminders paused."
        self.message_until = time.monotonic() + 3.0
        self._persist()

    def _set_hydration_interval(self) -> None:
        self.activity_tracker.record_sample(
            0,
            is_idle=self.user_is_idle,
            count_activity=False,
            count_hydration=False,
            today=datetime.now().astimezone(),
        )
        self.activity_tracker.today.hydration_elapsed_seconds = 0.0
        self.activity_tracker.today.snooze_remaining_seconds = 0.0
        self.message = f"Water reminder: {self.hydration_interval.get()} min."
        self.message_until = time.monotonic() + 3.2
        self._persist()
        self._save_activity()

    def _log_water(self) -> None:
        now = time.monotonic()
        self.activity_tracker.mark_water()
        self.message = f"Nice! Water #{self.activity_tracker.today.water_count} today."
        self.message_until = now + 4.5
        self.happy_until = now + 2.5
        self.water_effect_started = now
        self.water_effect_until = now + 2.6
        self._save_activity()

    def _show_today_stats(self) -> None:
        from tkinter import messagebox

        self.activity_tracker.record_sample(
            0,
            is_idle=self.user_is_idle,
            count_activity=False,
            count_hydration=False,
            today=datetime.now().astimezone(),
        )
        stats = self.activity_tracker.today
        tracking = "On" if self.activity_monitoring.get() else "Paused"
        messagebox.showinfo(
            "Mochi - Today's activity",
            "\n".join(
                (
                    f"Activity totals: {tracking}",
                    f"Active time: {format_duration(stats.active_seconds)}",
                    f"Idle time: {format_duration(stats.idle_seconds)}",
                    f"Water logged: {stats.water_count}",
                    "",
                    "Only daily totals are stored locally.",
                    "No input content, apps, titles, or screenshots are logged.",
                )
            ),
            parent=self.root,
        )

    def _delete_activity_history(self) -> None:
        from tkinter import messagebox

        confirmed = messagebox.askyesno(
            "Delete activity history?",
            "Delete all locally stored activity totals and water counts?\n\n"
            "This cannot be undone.",
            parent=self.root,
        )
        if not confirmed:
            return
        self.activity_tracker.clear_history(today=datetime.now().astimezone())
        self._save_activity()
        self.message = "Local activity history deleted."
        self.message_until = time.monotonic() + 4.0

    def _save_activity(self) -> None:
        try:
            save_activity(self.activity_tracker, self.activity_path)
        except OSError:
            pass

    def _show_hydration_reminder(self, now: float) -> None:
        self.activity_tracker.mark_reminded()
        self.message = "Water break! Take a sip."
        self.message_until = now + 12.0
        self.water_effect_started = now
        self.water_effect_until = now + 4.0
        self._save_activity()
        try:
            self.root.lift()
        except tk.TclError:
            pass

    def _update_activity(self, now: float) -> None:
        elapsed = now - self.last_activity_sample_at
        if elapsed < 1.0:
            return
        self.last_activity_sample_at = now

        tracking = self.activity_monitoring.get()
        reminders = self.hydration_reminders.get()
        idle_value = windows_idle_seconds() if tracking else None
        idle_known = idle_value is not None
        threshold_seconds = self.settings["idle_threshold_minutes"] * 60
        self.user_is_idle = bool(idle_known and idle_value >= threshold_seconds)

        self.activity_tracker.record_sample(
            elapsed,
            is_idle=self.user_is_idle,
            count_activity=tracking and idle_known,
            count_hydration=reminders,
            today=datetime.now().astimezone(),
        )

        wall_now = datetime.now().astimezone()
        if reminders and self.activity_tracker.hydration_due(
            self.hydration_interval.get(),
            hour=wall_now.hour,
            user_is_idle=self.user_is_idle,
        ):
            self._show_hydration_reminder(now)

        if now >= self.next_activity_save_at:
            if tracking or reminders:
                self._save_activity()
            self.next_activity_save_at = now + 60.0

    def _toggle_wander(self) -> None:
        if not self.auto_wander.get():
            self.walk_target_x = None
        else:
            self.next_walk_at = time.monotonic() + 1.0
        self._persist()

    def _toggle_topmost(self) -> None:
        self.root.wm_attributes("-topmost", self.always_on_top.get())
        self._persist()

    def _reset_position(self) -> None:
        self._refresh_monitors(force_visible=False)
        x, y = normalize_position_on_monitors(None, None, self.work_areas)
        self.root.geometry(geometry_at(x, y))
        self.walk_target_x = None
        self.settings["x"] = x
        self.settings["y"] = y
        self._persist()

    def _remember_position(self) -> None:
        self.settings["x"] = self.root.winfo_x()
        self.settings["y"] = self.root.winfo_y()
        self._persist()

    def _persist(self) -> None:
        self.settings["auto_wander"] = self.auto_wander.get()
        self.settings["always_on_top"] = self.always_on_top.get()
        self.settings["activity_monitoring"] = self.activity_monitoring.get()
        self.settings["hydration_reminders"] = self.hydration_reminders.get()
        self.settings["hydration_interval_minutes"] = self.hydration_interval.get()
        try:
            save_settings(self.settings, self.config_path)
        except OSError:
            # A read-only profile should not stop the pet from running.
            pass

    def close(self) -> None:
        if self.closing:
            return
        self.closing = True
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        self.settings["x"] = self.root.winfo_x()
        self.settings["y"] = self.root.winfo_y()
        self._persist()
        self._save_activity()
        self.root.destroy()

    def _move_toward_target(self) -> bool:
        if self.walk_target_x is None:
            return False
        current_x = self.root.winfo_x()
        difference = self.walk_target_x - current_x
        if abs(difference) <= 3:
            self.root.geometry(geometry_at(self.walk_target_x, self.root.winfo_y()))
            self.walk_target_x = None
            self.next_walk_at = time.monotonic() + self.rng.uniform(5.0, 10.0)
            self._remember_position()
            return False

        self.direction = 1 if difference > 0 else -1
        step = self.direction * min(3, abs(difference))
        area = monitor_for_point(
            current_x + WINDOW_WIDTH // 2,
            self.root.winfo_y() + WINDOW_HEIGHT // 2,
            self.work_areas,
        )
        new_x, new_y = clamp_position_to_work_area(
            current_x + step,
            self.root.winfo_y(),
            area,
        )
        self.root.geometry(geometry_at(new_x, new_y))
        return True

    def _refresh_monitors(self, *, force_visible: bool = True) -> None:
        """Pick up display changes and recover the pet onto a real monitor."""
        self.work_areas = monitor_work_areas(self.root)
        if force_visible:
            x, y = normalize_position_on_monitors(
                self.root.winfo_x(),
                self.root.winfo_y(),
                self.work_areas,
            )
            if (x, y) != (self.root.winfo_x(), self.root.winfo_y()):
                self.root.geometry(geometry_at(x, y))
        if self.walk_target_x is not None:
            area = monitor_for_point(
                self.root.winfo_x() + WINDOW_WIDTH // 2,
                self.root.winfo_y() + WINDOW_HEIGHT // 2,
                self.work_areas,
            )
            left, _top, width, _height = area
            if not left <= self.walk_target_x <= left + max(0, width - WINDOW_WIDTH):
                self.walk_target_x = None
                self.next_walk_at = time.monotonic() + 1.0

    def _tick(self) -> None:
        now = time.monotonic()

        self._update_activity(now)

        if now >= self.next_monitor_refresh_at:
            self._refresh_monitors()
            self.next_monitor_refresh_at = now + 2.0

        if now >= self.next_blink_at:
            self.blink_until = now + 0.15
            self.next_blink_at = now + self.rng.uniform(2.2, 5.0)

        walking = False
        if self.auto_wander.get() and not self.dragging:
            if self.walk_target_x is None and now >= self.next_walk_at:
                area = monitor_for_point(
                    self.root.winfo_x() + WINDOW_WIDTH // 2,
                    self.root.winfo_y() + WINDOW_HEIGHT // 2,
                    self.work_areas,
                )
                self.walk_target_x = choose_wander_target(
                    self.root.winfo_x(),
                    area[0],
                    area[2],
                    rng=self.rng,
                )
            walking = self._move_toward_target()

        if self.message and now >= self.message_until:
            self.message = ""
        if not self.message and now >= self.next_message_at:
            self.message = self.rng.choice(self.messages)
            self.message_until = now + 3.2
            self.next_message_at = now + self.rng.uniform(22.0, 42.0)

        self.hearts = [heart for heart in self.hearts if now - heart[2] < 1.55]
        self._draw(now, walking)
        if not self.closing:
            self.after_id = self.root.after(80, self._tick)

    def _draw(self, now: float, walking: bool) -> None:
        canvas = self.canvas
        canvas.delete("all")
        center_x = WINDOW_WIDTH / 2
        bob = math.sin(now * (9.0 if walking else 3.2)) * (2.4 if walking else 1.2)
        happy = now < self.happy_until
        blinking = now < self.blink_until

        def mirror_x(x: float) -> float:
            return center_x + (x - center_x) * self.direction

        def oval(x1: float, y1: float, x2: float, y2: float, **kwargs: Any) -> int:
            left, right = sorted((mirror_x(x1), mirror_x(x2)))
            return canvas.create_oval(left, y1 + bob, right, y2 + bob, **kwargs)

        def line(points: list[float], **kwargs: Any) -> int:
            mirrored: list[float] = []
            for index in range(0, len(points), 2):
                mirrored.extend((mirror_x(points[index]), points[index + 1] + bob))
            return canvas.create_line(*mirrored, **kwargs)

        def polygon(points: list[float], **kwargs: Any) -> int:
            mirrored: list[float] = []
            for index in range(0, len(points), 2):
                mirrored.extend((mirror_x(points[index]), points[index + 1] + bob))
            return canvas.create_polygon(*mirrored, **kwargs)

        # Soft floor shadow.
        canvas.create_oval(42, 181, 136, 198, fill="#cbd5e1", outline="")

        # Tail sits behind the body and swishes independently.
        tail_lift = math.sin(now * 4.2) * 8
        line(
            [124, 151, 146, 151 - tail_lift / 3, 157, 130 - tail_lift, 143, 116],
            fill="#d97745",
            width=17,
            smooth=True,
            splinesteps=18,
            capstyle=tk.ROUND,
        )
        line(
            [127, 149, 146, 149 - tail_lift / 3, 154, 131 - tail_lift],
            fill="#f6b26b",
            width=9,
            smooth=True,
            splinesteps=18,
            capstyle=tk.ROUND,
        )

        # Body, feet, head and ears.
        oval(48, 116, 132, 181, fill="#f8c985", outline="#8f5535", width=3)
        paw_shift = 3 if walking and math.sin(now * 9) > 0 else 0
        oval(51, 158 - paw_shift, 82, 185 - paw_shift, fill="#fff4dc", outline="#8f5535", width=3)
        oval(96, 158 + paw_shift, 127, 185 + paw_shift, fill="#fff4dc", outline="#8f5535", width=3)

        polygon([48, 96, 51, 62, 77, 83], fill="#f6b26b", outline="#8f5535", width=3)
        polygon([101, 83, 125, 61, 130, 99], fill="#f6b26b", outline="#8f5535", width=3)
        polygon([54, 88, 56, 70, 70, 83], fill="#f9a8a8", outline="")
        polygon([108, 83, 122, 70, 126, 91], fill="#f9a8a8", outline="")
        oval(42, 78, 134, 151, fill="#f8c985", outline="#8f5535", width=3)

        # Cream muzzle and a small forehead patch.
        oval(61, 113, 116, 148, fill="#fff4dc", outline="")
        polygon([76, 80, 89, 95, 102, 80, 100, 101, 78, 101], fill="#fff4dc", outline="")

        eye_y = 112
        if blinking:
            line([64, eye_y, 76, eye_y], fill="#4b342c", width=3, capstyle=tk.ROUND)
            line([101, eye_y, 113, eye_y], fill="#4b342c", width=3, capstyle=tk.ROUND)
        elif happy:
            line([63, 114, 69, 108, 76, 114], fill="#4b342c", width=3, smooth=True)
            line([101, 114, 107, 108, 114, 114], fill="#4b342c", width=3, smooth=True)
        else:
            oval(66, 106, 74, 116, fill="#4b342c", outline="")
            oval(103, 106, 111, 116, fill="#4b342c", outline="")
            oval(68, 107, 70, 110, fill="#ffffff", outline="")
            oval(105, 107, 107, 110, fill="#ffffff", outline="")

        oval(58, 121, 70, 128, fill="#f6a6a6", outline="")
        oval(108, 121, 120, 128, fill="#f6a6a6", outline="")
        polygon([84, 119, 94, 119, 89, 125], fill="#b65b5b", outline="")
        line([89, 125, 89, 130], fill="#4b342c", width=2)
        line([89, 130, 83, 133], fill="#4b342c", width=2, smooth=True)
        line([89, 130, 95, 133], fill="#4b342c", width=2, smooth=True)

        # Whiskers.
        line([62, 126, 43, 122], fill="#8f5535", width=2)
        line([62, 132, 40, 134], fill="#8f5535", width=2)
        line([116, 126, 135, 122], fill="#8f5535", width=2)
        line([116, 132, 138, 134], fill="#8f5535", width=2)

        # Rising hearts from a double-click.
        for heart_x, heart_y, born_at in self.hearts:
            age = now - born_at
            if 0.0 <= age <= 1.55:
                canvas.create_text(
                    heart_x,
                    heart_y - age * 34,
                    text="♥",
                    fill="#ef476f",
                    font=("Segoe UI Symbol", max(8, int(18 - age * 4)), "bold"),
                )

        # Blue droplets make hydration reminders recognizable without sound.
        if now < self.water_effect_until:
            effect_age = max(0.0, now - self.water_effect_started)
            for index, base_x in enumerate((56, 88, 120)):
                phase = max(0.0, effect_age - index * 0.16)
                drop_y = 104 - phase * 25
                size = max(3.0, 7.0 - phase)
                canvas.create_polygon(
                    base_x,
                    drop_y - size,
                    base_x - size,
                    drop_y + size,
                    base_x + size,
                    drop_y + size,
                    fill="#38bdf8",
                    outline="#0369a1",
                    width=1,
                )
                canvas.create_oval(
                    base_x - size,
                    drop_y,
                    base_x + size,
                    drop_y + size * 2,
                    fill="#38bdf8",
                    outline="#0369a1",
                    width=1,
                )

        if self.message:
            self._draw_bubble(self.message)

    def _draw_bubble(self, message: str) -> None:
        points = [
            13, 10, 163, 10, 168, 15, 168, 57, 163, 62,
            101, 62, 88, 72, 82, 62, 13, 62, 8, 57, 8, 15,
        ]
        self.canvas.create_polygon(
            *points,
            fill="#ffffff",
            outline="#8f5535",
            width=2,
            smooth=True,
            splinesteps=18,
        )
        self.canvas.create_text(
            88,
            36,
            text=message,
            fill="#4b342c",
            font=("Segoe UI", 9, "bold"),
            width=142,
            justify="center",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mochi-pet",
        description="Launch a tiny animated desktop companion.",
    )
    parser.add_argument(
        "--no-wander",
        action="store_true",
        help="start with automatic wandering disabled",
    )
    parser.add_argument(
        "--reset-settings",
        action="store_true",
        help="remove preferences but keep activity history before starting",
    )
    parser.add_argument(
        "--reset-all-data",
        action="store_true",
        help="remove preferences and local aggregate activity history before starting",
    )
    parser.add_argument(
        "--enable-activity",
        action="store_true",
        help="enable local active/idle aggregate statistics",
    )
    parser.add_argument(
        "--no-hydration",
        action="store_true",
        help="start with hydration reminders disabled",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = settings_path()
    activity_file = config.with_name("activity.json")
    reset_targets = (config, activity_file) if args.reset_all_data else (config,)
    if args.reset_settings or args.reset_all_data:
        for target in reset_targets:
            try:
                target.unlink()
            except OSError:
                pass

    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f"Could not open the desktop window: {error}")
        return 1

    try:
        MochiPet(
            root,
            auto_wander_override=False if args.no_wander else None,
            activity_monitoring_override=True if args.enable_activity else None,
            hydration_reminders_override=False if args.no_hydration else None,
            config_path=config,
            activity_path=activity_file,
        )
        root.mainloop()
    except Exception as error:  # Keep pythonw failures visible to Windows users.
        try:
            from tkinter import messagebox

            messagebox.showerror(APP_NAME, f"Mochi could not start:\n\n{error}")
        except (tk.TclError, ImportError):
            print(f"Mochi could not start: {error}")
        try:
            root.destroy()
        except tk.TclError:
            pass
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
