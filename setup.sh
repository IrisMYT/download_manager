#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_DIR="$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    Download Manager Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Python
if ! command_exists python3; then
    echo -e "${RED}Python 3 not found!${NC}"
    echo "Please install Python 3.8 or later and try again."
    exit 1
else
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo -e "${GREEN}Python $PYTHON_VERSION found${NC}"
fi

# Check for pip
if ! command_exists pip3; then
    echo -e "${YELLOW}pip not found. Installing...${NC}"
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py
    rm get-pip.py
fi

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created${NC}"
else
    echo -e "${BLUE}Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install Python requirements
echo -e "${YELLOW}Installing Python dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${RED}requirements.txt not found!${NC}"
    exit 1
fi

# Create runtime directories (only the ones needed at runtime, not the source directories)
echo -e "${YELLOW}Creating runtime directories...${NC}"
mkdir -p logs
mkdir -p downloads

# Create launcher script
echo -e "${YELLOW}Creating launcher script...${NC}"
LAUNCHER_NAME="downloadmanager"
cat > "../$LAUNCHER_NAME" << 'EOL'
#!/bin/bash
# Download Manager Launcher

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$SCRIPT_DIR/download_manager"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to check if the app is already running
is_running() {
    pgrep -f "python.*main.py" > /dev/null 2>&1
    return $?
}

# Function to start the application
start_app() {
    echo -e "${GREEN}Starting Download Manager...${NC}"
    cd "$APP_DIR"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Virtual environment not found. Running setup...${NC}"
        ./setup.sh
    fi
    
    # Activate virtual environment and start the app
    source venv/bin/activate
    
    # Check if we should run in background
    if [ "$1" == "--background" ] || [ "$1" == "-b" ]; then
        nohup python main.py > logs/app.log 2>&1 &
        echo $! > .app.pid
        echo -e "${GREEN}Download Manager started in background (PID: $!)${NC}"
        echo -e "${GREEN}Access the web interface at: http://localhost:8000${NC}"
    else
        python main.py
    fi
}

# Function to stop the application
stop_app() {
    echo -e "${YELLOW}Stopping Download Manager...${NC}"
    
    if [ -f "$APP_DIR/.app.pid" ]; then
        PID=$(cat "$APP_DIR/.app.pid")
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            rm "$APP_DIR/.app.pid"
            echo -e "${GREEN}Download Manager stopped${NC}"
        else
            echo -e "${YELLOW}Process not found, cleaning up PID file${NC}"
            rm "$APP_DIR/.app.pid"
        fi
    else
        # Try to find and kill the process
        pkill -f "python.*main.py"
        echo -e "${GREEN}Download Manager stopped${NC}"
    fi
}

# Main script logic
case "$1" in
    start)
        if is_running; then
            echo -e "${YELLOW}Download Manager is already running${NC}"
        else
            start_app "$2"
        fi
        ;;
    stop)
        stop_app
        ;;
    restart)
        stop_app
        sleep 2
        start_app "$2"
        ;;
    status)
        if is_running; then
            echo -e "${GREEN}Download Manager is running${NC}"
            echo -e "Access the web interface at: ${GREEN}http://localhost:8000${NC}"
        else
            echo -e "${YELLOW}Download Manager is not running${NC}"
        fi
        ;;
    *)
        # If no argument provided, just start the app
        if is_running; then
            echo -e "${YELLOW}Download Manager is already running${NC}"
            echo -e "Access the web interface at: ${GREEN}http://localhost:8000${NC}"
        else
            start_app
        fi
        ;;
esac
EOL

chmod +x "../$LAUNCHER_NAME"
echo -e "${GREEN}Created launcher: $(dirname "$INSTALL_DIR")/$LAUNCHER_NAME${NC}"

# Create systemd service file (optional)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${YELLOW}Creating systemd service file...${NC}"
    
    SERVICE_FILE="downloadmanager.service"
    cat > "$SERVICE_FILE" << EOL
[Unit]
Description=Download Manager Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL
    
    echo -e "${GREEN}Systemd service file created: $SERVICE_FILE${NC}"
    echo -e "${YELLOW}To install as a system service, run:${NC}"
    echo -e "  sudo cp $SERVICE_FILE /etc/systemd/system/"
    echo -e "  sudo systemctl daemon-reload"
    echo -e "  sudo systemctl enable downloadmanager"
    echo -e "  sudo systemctl start downloadmanager"
fi

# Final setup summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Installation Directory:${NC} $INSTALL_DIR"
echo -e "${BLUE}Launcher Location:${NC} $(dirname "$INSTALL_DIR")/$LAUNCHER_NAME"
echo ""
echo -e "${YELLOW}To start the Download Manager:${NC}"
echo -e "  cd $(dirname "$INSTALL_DIR")"
echo -e "  ./$LAUNCHER_NAME"
echo ""
echo -e "${YELLOW}Or run with options:${NC}"
echo -e "  ./$LAUNCHER_NAME start --background   # Run in background"
echo -e "  ./$LAUNCHER_NAME stop                  # Stop the service"
echo -e "  ./$LAUNCHER_NAME status                # Check status"
echo ""
echo -e "${GREEN}The web interface will be available at:${NC} http://localhost:8000"
echo ""

# Ask if user wants to start now
read -p "Do you want to start Download Manager now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$(dirname "$INSTALL_DIR")"
    ./$LAUNCHER_NAME
fi
