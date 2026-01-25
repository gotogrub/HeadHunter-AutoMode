@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting HeadHunter Destroyer...
echo.
echo IMPORTANT: Make sure Edge browser is CLOSED!
echo.
python main.py
pause
