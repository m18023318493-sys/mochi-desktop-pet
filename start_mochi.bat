@echo off
cd /d "%~dp0"

py -3 -c "import sys, tkinter; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
  where pyw >nul 2>nul
  if not errorlevel 1 goto launch_with_pyw
)

python -c "import sys, tkinter; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
  where pythonw >nul 2>nul
  if not errorlevel 1 goto launch_with_pythonw
)

echo Mochi needs Python 3.10 or newer with Tkinter.
echo Install it from https://www.python.org/downloads/ and try again.
pause
exit /b 1

:launch_with_pyw
start "" pyw -3 "%~dp0mochi_pet.py"
exit /b 0

:launch_with_pythonw
start "" pythonw "%~dp0mochi_pet.py"
exit /b 0
