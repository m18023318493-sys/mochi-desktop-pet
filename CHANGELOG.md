# Changelog

All notable changes to this project will be documented here.

## 0.3.2 - 2026-09-17

- Removed the floor shadow beneath custom images so no horizontal afterimage appears below the character.

## 0.3.1 - 2026-09-16

- Localized all pet messages, reminders, menus, and activity dialogs into Chinese.
- Reserved a dedicated transparent area above the character so speech bubbles never cover it.
- Added a larger 20-point blue hydration reminder while keeping normal messages compact.
- Preserved the character's screen position while expanding the window upward.

## 0.3.0 - 2026-09-16

- Added local custom appearances from PNG, JPEG, WebP, GIF, and BMP images.
- Added automatic left/right mirroring, walking motion, and image-size controls.
- Added safe local image normalization with EXIF removal, size limits, and atomic replacement.
- Added controls to switch back to Mochi or delete the processed custom image.
- Added custom-image privacy documentation and Pillow-based image tests.

## 0.2.0 - 2026-09-16

- Added configurable hydration reminders with quiet hours from 22:00 to 08:00.
- Added an opt-in, Windows-only active/idle time monitor using daily aggregates.
- Added water logging, today's summary, 30-day retention, and local history deletion.
- Added strict privacy-allowlist tests; no raw input, app, window, or screenshot data is stored.

## 0.1.1 - 2026-09-16

- Fixed the Windows launcher when system utilities such as `where.exe` are not on `PATH`.
- Resolve `pyw.exe` or `pythonw.exe` beside the validated Python interpreter.

## 0.1.0 - 2026-09-15

- First public release.
- Added animated Canvas-drawn cat, dragging, wandering, interactions, and speech bubbles.
- Added persistent position and preferences, a right-click menu, and multi-monitor bounds on Windows.
- Added dependency-free core tests and GitHub Actions CI.
