#!/bin/bash

echo "========================================"
echo " HeadHunter Destroyer - Installation"
echo "========================================"
echo

echo "[1/3] Installing Python dependencies..."
pip3 install -r requirements.txt

echo
echo "[2/3] Installing Playwright browsers..."
playwright install chromium
# Install dependencies for Playwright on Linux
playwright install-deps chromium 2>/dev/null || sudo playwright install-deps chromium

echo
echo "[3/3] Installation complete!"
echo
echo "========================================"
echo " Run './start.sh' to launch the bot"
echo "========================================"
