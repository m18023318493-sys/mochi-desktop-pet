@echo off
setlocal
cd /d "%~dp0"

for %%I in (py.exe) do set "PY_EXE=%%~$PATH:I"
if not defined PY_EXE goto try_python
"%PY_EXE%" -3 -c "import sys, tkinter; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto try_python
for %%I in ("%PY_EXE%") do set "PYW_EXE=%%~dpIpyw.exe"
if exist "%PYW_EXE%" goto launch_with_pyw

:try_python
for %%I in (python.exe) do set "PYTHON_EXE=%%~$PATH:I"
if not defined PYTHON_EXE goto launch_error
"%PYTHON_EXE%" -c "import sys, tkinter; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto launch_error
for %%I in ("%PYTHON_EXE%") do set "PYTHONW_EXE=%%~dpIpythonw.exe"
if exist "%PYTHONW_EXE%" goto launch_with_pythonw

:launch_error
echo Mochi needs Python 3.10 or newer with Tkinter.
echo Install it from https://www.python.org/downloads/ and try again.
pause
exit /b 1

:launch_with_pyw
start "" "%PYW_EXE%" -3 "%~dp0mochi_pet.py"
exit /b 0

:launch_with_pythonw
start "" "%PYTHONW_EXE%" "%~dp0mochi_pet.py"
exit /b 0
