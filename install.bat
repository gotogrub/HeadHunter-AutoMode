@echo off
chcp 65001 >nul
echo ========================================
echo  HeadHunter Destroyer - Installation
echo ========================================
echo.

echo [1/3] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo [2/3] Installing Playwright browsers...
playwright install chromium msedge

echo.
echo [3/3] Installation complete!
echo.
echo ========================================
echo  IMPORTANT: Close Microsoft Edge before
echo  running the bot to use your session!
echo ========================================
echo.
echo Run 'start.bat' to launch the bot.
pause
