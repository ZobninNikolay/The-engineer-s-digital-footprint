@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'"
if errorlevel 1 goto fail
py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto fail
.venv\Scripts\python.exe install.py
if errorlevel 1 goto fail
echo Setup complete. Open this folder in local Codex. Read START_HERE.md.
echo Hook trust must be granted through the app. Capture is not yet verified.
pause
exit /b 0
:fail
echo Setup failed. Preserve this output for diagnosis.
pause
exit /b 1
