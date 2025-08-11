#!/bin/bash
set -e

PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/venv"

echo "[*] Updating system..."
apt update && apt upgrade -y

echo "[*] Installing system dependencies..."
apt install -y python3 python3-venv git

echo "[*] Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"

echo "[*] Activating virtual environment..."
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

echo "[*] Upgrading pip..."
pip install --upgrade pip

echo "[*] Installing Python requirements..."
pip install -r requirements.txt

# Ensure /usr/local/bin is in PATH before venv usage (safety net)
if ! grep -q "/usr/local/bin" ~/.bashrc; then
    echo 'export PATH="$PATH:/usr/local/bin"' >> ~/.bashrc
    echo "[*] Added /usr/local/bin to PATH in ~/.bashrc"
fi

echo
echo "[✔] Setup complete!"
echo "To start using the program, run:"
echo "source "$VENV_DIR/bin/activate" && python main.py"
