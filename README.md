# Mochi Desktop Pet

[![CI](https://github.com/m18023318493-sys/mochi-desktop-pet/actions/workflows/ci.yml/badge.svg)](https://github.com/m18023318493-sys/mochi-desktop-pet/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A tiny animated cat that lives on your desktop. Mochi is drawn entirely with Tkinter, works offline, and has no third-party runtime dependencies.

![Mochi Desktop Pet preview](assets/preview.svg)

## Features

- Transparent, borderless, always-on-top window on Windows
- Gentle idle animation, blinking, tail swishes, and automatic wandering
- Drag Mochi anywhere; position and preferences are remembered
- Double-click for hearts and a happy message
- Right-click menu to pause wandering, change always-on-top, reset, or quit
- Handles multi-monitor desktop bounds on Windows
- No network requests, telemetry, ads, or external art assets

## Quick start

Requires Python 3.10 or newer with Tkinter (included in the standard Windows installer).

For the easiest Windows setup, download `mochi-desktop-pet-v0.1.1.zip` from the [latest release](https://github.com/m18023318493-sys/mochi-desktop-pet/releases/latest), extract the whole ZIP, then double-click `start_mochi.bat`.

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
| Right-click | Open settings and the Quit command |
| <kbd>Esc</kbd> | Quit while Mochi has keyboard focus |

Launch without automatic wandering:

```powershell
python mochi_pet.py --no-wander
```

Reset the saved position and preferences:

```powershell
python mochi_pet.py --reset-settings
```

## 简体中文

Mochi 是一个使用 Python 标准库制作的轻量桌面宠物。左键拖动，双击互动，右键可以暂停散步、切换置顶、重置位置或退出。程序完全离线运行，不收集任何数据。

Windows 用户安装 Python 3.10+ 后，可以从 [Releases](https://github.com/m18023318493-sys/mochi-desktop-pet/releases/latest) 下载 ZIP，先完整解压，再双击 `start_mochi.bat` 启动。

## Privacy and settings

Mochi never connects to the internet. It stores only window coordinates and two preferences:

- Windows: `%APPDATA%\MochiDesktopPet\settings.json`
- macOS/Linux: `~/.config/MochiDesktopPet/settings.json`

To uninstall, delete the cloned project (or run `python -m pip uninstall mochi-desktop-pet` if installed) and optionally delete that settings folder.

## Compatibility

Windows 10/11 is the primary target. macOS and Linux can run the basic Tkinter window, but transparent-window behavior depends on the desktop environment. Per-monitor scaling may make the pet appear slightly different on mixed-DPI setups.

## Development

```powershell
python -m unittest discover -s tests -v
python -m py_compile pet_core.py mochi_pet.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance and [SECURITY.md](SECURITY.md) for private vulnerability reporting guidance.

## License

MIT. The cat artwork is made from Canvas primitives in this repository and is covered by the same license.
