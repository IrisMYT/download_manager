#!/bin/bash

# Installer for Download Manager from ZIP file
# This script should be placed in the extracted download_manager directory

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in the right directory
if [ ! -f "$SCRIPT_DIR/main.py" ]; then
    echo "Error: This script must be run from the download_manager directory"
    echo "Please extract the ZIP file and run this script from within the extracted folder"
    exit 1
fi

# Run the main setup script
if [ -f "$SCRIPT_DIR/setup.sh" ]; then
    chmod +x "$SCRIPT_DIR/setup.sh"
    "$SCRIPT_DIR/setup.sh"
else
    echo "Error: setup.sh not found!"
    exit 1
fi
