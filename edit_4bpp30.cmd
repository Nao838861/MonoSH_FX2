@echo off
cd /d "%~dp0"
where code >nul 2>nul
if errorlevel 1 (
  start "" notepad.exe "%~dp0README_4BPP30.md"
) else (
  call code -n "%~dp0"
)
