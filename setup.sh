#!/bin/bash

# Fix PATH
echo 'export PATH="$PATH:/usr/local/bin"' >> ~/.bashrc
source ~/.bashrc

# Update package list
apt update

# Install pip3 if not available
if ! command -v pip3 &> /dev/null; then
    apt install -y python3-pip
fi

# Install/upgrade required packages
pip3 install --upgrade pip
pip3 install -r requirements.txt

echo "Setup completed successfully!"

