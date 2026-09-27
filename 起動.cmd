@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Project .venv was not found. Run: py -3 scripts\setup_venv.py
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -X utf8 "%~dp0launch.py" %*
set "app_exit=%errorlevel%"
if not "%app_exit%"=="0" pause
exit /b %app_exit%
