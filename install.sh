#!/bin/bash

# One-line installer for Download Manager
# Usage: curl -sSL https://your-domain.com/install.sh | bash

set -e

REPO_URL="https://github.com/yourusername/download-manager"
INSTALL_DIR="download_manager"

echo "Download Manager Quick Installer"
echo "================================"
echo ""

# Check if git is installed
if ! command -v git >/dev/null 2>&1; then
    echo "Installing git..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y git
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y git
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm git
    else
        echo "Error: Could not install git. Please install it manually."
        exit 1
    fi
fi

# Clone or download the repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory $INSTALL_DIR already exists. Updating..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Downloading Download Manager..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Run the setup script
echo "Running setup..."
chmod +x setup.sh
./setup.sh

echo ""
echo "Installation complete!"
