@echo off
setlocal
where py >nul 2>nul
if errorlevel 1 (
  python -X utf8 "%~dp0scripts\setup_venv.py"
) else (
  py -3 -X utf8 "%~dp0scripts\setup_venv.py"
)
set "setup_exit=%errorlevel%"
pause
exit /b %setup_exit%
