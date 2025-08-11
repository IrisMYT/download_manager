#!/bin/bash
set -e

echo "[*] Updating system..."
apt update && apt upgrade -y

echo "[*] Installing dependencies..."
apt install -y python3 python3-pip git

echo "[*] Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

echo "[*] Setup complete!"
echo "Run: python3 main.py"
