# Mochi Desktop Pet

[![CI](https://github.com/m18023318493-sys/mochi-desktop-pet/actions/workflows/ci.yml/badge.svg)](https://github.com/m18023318493-sys/mochi-desktop-pet/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A tiny animated cat that lives on your desktop. Mochi is drawn entirely with Tkinter, works offline, and has no third-party runtime dependencies. It can also nudge you to drink water and, when you opt in on Windows, show daily aggregate active/idle time.

![Mochi Desktop Pet preview](assets/preview.svg)

## Features

- Transparent, borderless, always-on-top window on Windows
- Gentle idle animation, blinking, tail swishes, and automatic wandering
- Drag Mochi anywhere; position and preferences are remembered
- Double-click for hearts and a happy message
- Hydration reminders every 30, 45, 60, 90, or 120 minutes (60 by default)
- Quiet hydration hours from 22:00 through 08:00
- Optional Windows activity totals and a daily water counter
- Right-click menu to view today's summary, pause features, reset, or quit
- Handles multi-monitor desktop bounds on Windows
- No network requests, telemetry, ads, or external art assets

## Quick start

Requires Python 3.10 or newer with Tkinter (included in the standard Windows installer).

For the easiest Windows setup, download `mochi-desktop-pet-v0.2.0.zip` from the [latest release](https://github.com/m18023318493-sys/mochi-desktop-pet/releases/latest), extract the whole ZIP, then double-click `start_mochi.bat`.

Or run it from source:

```powershell
git clone https://github.com/m18023318493-sys/mochi-desktop-pet.git
cd mochi-desktop-pet
python mochi_pet.py
```

On Windows, you can also double-click `start_mochi.bat` after cloning the repository.

### Optional command installation

```powershell
python -m pip install .
mochi-pet
```

## Controls

| Action | Result |
| --- | --- |
| Drag with the left mouse button | Move Mochi |
| Double-click | Pet Mochi and show hearts |
| Right-click | Log water, see today's totals, configure reminders, or quit |
| <kbd>Esc</kbd> | Quit while Mochi has keyboard focus |

Launch without automatic wandering:

```powershell
python mochi_pet.py --no-wander
```

Reset the saved position and preferences:

```powershell
python mochi_pet.py --reset-settings
```

Enable local aggregate activity statistics from the command line:

```powershell
python mochi_pet.py --enable-activity
```

Delete preferences and all locally stored activity/water history before starting:

```powershell
python mochi_pet.py --reset-all-data
```

## 简体中文

Mochi 是一个使用 Python 标准库制作的轻量桌面宠物。左键拖动，双击互动；右键可以记录喝水、查看今日汇总、调整提醒间隔、开启或暂停活跃度统计，以及退出程序。

Windows 用户安装 Python 3.10+ 后，可以从 [Releases](https://github.com/m18023318493-sys/mochi-desktop-pet/releases/latest) 下载 ZIP，先完整解压，再双击 `start_mochi.bat` 启动。

喝水提醒默认开启，每运行 60 分钟提醒一次，22:00–08:00 静默。活跃/空闲统计默认关闭；只有你主动开启后才会在 Windows 上读取“距离上次本机输入经过了多久”这一数值，并仅保存每天的汇总秒数。

## Privacy and local data

Mochi works entirely offline and never sends reminder or activity data over the network. Activity statistics are **off by default**. When enabled on Windows, Mochi asks the operating system once per second only for the elapsed time since the last local input. It does not install keyboard or mouse hooks and never logs or stores keystrokes, typed text, pointer trails, clipboard contents, application/process names, window titles, browser history, or screenshots. Dragging uses the current pointer position only to move the pet and does not record it.

Hydration reminders are on by default. With activity statistics off, their timer advances while Mochi is running. With activity statistics on, idle time pauses that timer. An ignored reminder is shown again after 10 active minutes; logging water resets the selected interval. Reminders are a general wellbeing aid, not medical advice.

Mochi stores no raw event sequence. It retains at most 30 daily aggregate records in these local files:

- Windows: `%APPDATA%\MochiDesktopPet\settings.json` and `activity.json`
- macOS/Linux: `~/.config/MochiDesktopPet/settings.json` and `activity.json`
- `settings.json`: window position, feature toggles, idle threshold, and reminder interval
- `activity.json`: date, aggregate active/idle seconds, water count, and aggregate reminder/snooze seconds

Statistics are collected only while Mochi is running. Long sleep/resume gaps are capped instead of being counted as hours of activity, and a new local-date bucket is created after midnight. Use **Delete activity history...** in the right-click menu to clear aggregates, or `--reset-all-data` to delete both files before launch.

To uninstall, delete the cloned project (or run `python -m pip uninstall mochi-desktop-pet` if installed) and optionally delete the `MochiDesktopPet` settings folder.

## Compatibility

Windows 10/11 is the primary target and the only platform with active/idle statistics. macOS and Linux can run the pet and hydration timer, but transparent-window behavior depends on the desktop environment. Per-monitor scaling may make the pet appear slightly different on mixed-DPI setups.

## Development

```powershell
python -m unittest discover -s tests -v
python -m py_compile activity_core.py pet_core.py mochi_pet.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance and [SECURITY.md](SECURITY.md) for private vulnerability reporting guidance.

## License

MIT. The cat artwork is made from Canvas primitives in this repository and is covered by the same license.
