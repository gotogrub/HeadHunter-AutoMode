#!/bin/bash

echo "========================================"
echo " HeadHunter Destroyer - Installation"
echo "========================================"
echo

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    PIP="pip3"
    PLAYWRIGHT="playwright"
else
    PIP="pip3"
    PLAYWRIGHT="playwright"
fi

echo "[1/3] Installing Python dependencies..."
$PIP install -r requirements.txt

echo
echo "[2/3] Installing Playwright browsers..."
$PLAYWRIGHT install chromium

# Install system dependencies for Playwright on Linux
echo "[*] Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
        libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
fi

echo
echo "[3/3] Installation complete!"
echo
echo "========================================"
echo " USAGE:"
echo "========================================"
echo
echo " Desktop mode (with GUI):"
echo "   ./start.sh"
echo
echo " Server mode (headless, for SSH):"
echo "   HH_SERVER_MODE=true ./start.sh"
echo "   or just run on headless system"
echo
echo " First-time login:"
echo "   1. Run on desktop with GUI first"
echo "   2. Login to HH.ru in the browser"
echo "   3. Copy ./browser_data/ to server"
echo "========================================"
