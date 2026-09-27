@echo off
setlocal
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 "%~dp0launch.py"
) else (
  py -3 "%~dp0launch.py"
)
if errorlevel 1 pause
