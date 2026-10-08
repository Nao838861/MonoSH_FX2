@echo off
cd /d "%~dp0"
python -X utf8 tools\play_4bpp.py %*
if errorlevel 1 pause
