@echo off
chcp 65001 >nul
echo ========================================
echo  HeadHunter Destroyer - Installation
echo ========================================
echo.

echo [1/3] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo [2/3] Installing Playwright browsers (Chrome, Edge, Firefox)...
playwright install chrome msedge firefox chromium

echo.
echo [3/3] Installation complete!
echo.
echo ========================================
echo  Browser selection (set HH_BROWSER):
echo    auto    - Auto-detect (default)
echo    chrome  - Google Chrome
echo    edge    - Microsoft Edge
echo    firefox - Mozilla Firefox
echo ========================================
echo.
echo Run 'start.bat' to launch the bot.
pause
