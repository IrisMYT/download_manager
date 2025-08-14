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
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    Download Manager Installer${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            echo "debian"
        elif [ -f /etc/redhat-release ]; then
            echo "redhat"
        elif [ -f /etc/arch-release ]; then
            echo "arch"
        else
            echo "unknown"
        fi
    else
        echo "unsupported"
    fi
}

OS_TYPE=$(detect_os)

echo -e "${YELLOW}Detected OS: $OS_TYPE${NC}"
echo ""

# Function to install Python
install_python() {
    echo -e "${YELLOW}Installing Python...${NC}"
    
    case $OS_TYPE in
        debian)
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv python3-dev
            ;;
        redhat)
            sudo yum install -y python3 python3-pip python3-devel
            ;;
        arch)
            sudo pacman -S --noconfirm python python-pip
            ;;
        *)
            echo -e "${RED}Unsupported OS. Please install Python 3.8+ manually.${NC}"
            exit 1
            ;;
    esac
}

# Function to install system dependencies
install_system_deps() {
    echo -e "${YELLOW}Installing system dependencies...${NC}"
    
    case $OS_TYPE in
        debian)
            sudo apt update
            sudo apt install -y curl wget git build-essential
            ;;
        redhat)
            sudo yum install -y curl wget git gcc make
            ;;
        arch)
            sudo pacman -S --noconfirm curl wget git base-devel
            ;;
    esac
}

# Check for Python
if ! command_exists python3; then
    echo -e "${RED}Python 3 not found!${NC}"
    read -p "Do you want to install Python? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_python
    else
        echo -e "${RED}Python 3 is required. Exiting...${NC}"
        exit 1
    fi
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

# Install system dependencies if needed
if ! command_exists curl || ! command_exists wget; then
    install_system_deps
fi

# Create directory structure
echo -e "${YELLOW}Creating directory structure...${NC}"
cd "$INSTALL_DIR"

# Create all necessary directories
directories=(
    "backend"
    "frontend/static/css"
    "frontend/static/js"
    "frontend/static/images"
    "frontend/templates"
    "config"
    "downloads"
    "logs"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    echo -e "  Created: $dir"
done

# Download all Python files if they don't exist
echo -e "${YELLOW}Setting up application files...${NC}"

# Create __init__.py files
touch backend/__init__.py

# Function to create a file with content
create_file() {
    local filepath=$1
    local content=$2
    
    if [ ! -f "$filepath" ]; then
        echo "$content" > "$filepath"
        echo -e "  ${GREEN}Created: $filepath${NC}"
    else
        echo -e "  ${BLUE}Exists: $filepath${NC}"
    fi
}

# Check if we need to download files from GitHub
if [ ! -f "backend/config.py" ]; then
    echo -e "${YELLOW}Downloading application files...${NC}"
    
    # You can either include the files directly or download from a repository
    # For this example, I'll create placeholder files
    # In production, you'd download from your GitHub repo
    
    # Example of downloading from GitHub (replace with your repo):
    # REPO_URL="https://github.com/yourusername/download-manager"
    # git clone "$REPO_URL" temp_download
    # cp -r temp_download/* .
    # rm -rf temp_download
    
    echo -e "${YELLOW}Note: Please ensure all application files are in place${NC}"
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
    # If requirements.txt doesn't exist, create it and install
    cat > requirements.txt << EOL
fastapi==0.104.1
uvicorn[standard]==0.24.0
requests==2.31.0
python-multipart==0.0.6
aiofiles==23.2.1
tqdm==4.66.1
EOL
    pip install -r requirements.txt
fi

# Create launcher script in parent directory
echo -e "${YELLOW}Creating launcher script...${NC}"

# Determine the appropriate extension and shebang based on OS
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    LAUNCHER_NAME="downloadmanager.bat"
    cat > "$PARENT_DIR/$LAUNCHER_NAME" << EOL
@echo off
cd /d "$INSTALL_DIR"
if not exist venv (
    echo Virtual environment not found. Running setup...
    call setup.sh
)
call venv\Scripts\activate.bat
python main.py
pause
EOL
else
    LAUNCHER_NAME="downloadmanager"
    cat > "$PARENT_DIR/$LAUNCHER_NAME" << EOL
#!/bin/bash
# Download Manager Launcher

# Get the directory where this script is located
SCRIPT_DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="\$SCRIPT_DIR/download_manager"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to check if the app is already running
is_running() {
    pgrep -f "python.*main.py" > /dev/null 2>&1
    return \$?
}

# Function to start the application
start_app() {
    echo -e "\${GREEN}Starting Download Manager...\\${NC}"
    cd "\$APP_DIR"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "\${YELLOW}Virtual environment not found. Running setup...\\${NC}"
        ./setup.sh
    fi
    
    # Activate virtual environment and start the app
    source venv/bin/activate
    
    # Check if we should run in background
    if [ "\$1" == "--background" ] || [ "\$1" == "-b" ]; then
        nohup python main.py > logs/app.log 2>&1 &
        echo \$! > .app.pid
        echo -e "\${GREEN}Download Manager started in background (PID: \$!)\\${NC}"
        echo -e "\${GREEN}Access the web interface at: http://localhost:8000\\${NC}"
    else
        python main.py
    fi
}

# Function to stop the application
stop_app() {
    echo -e "\${YELLOW}Stopping Download Manager...\\${NC}"
    
    if [ -f "\$APP_DIR/.app.pid" ]; then
        PID=\$(cat "\$APP_DIR/.app.pid")
        if kill -0 \$PID 2>/dev/null; then
            kill \$PID
            rm "\$APP_DIR/.app.pid"
            echo -e "\${GREEN}Download Manager stopped\\${NC}"
        else
            echo -e "\${YELLOW}Process not found, cleaning up PID file\\${NC}"
            rm "\$APP_DIR/.app.pid"
        fi
    else
        # Try to find and kill the process
        pkill -f "python.*main.py"
        echo -e "\${GREEN}Download Manager stopped\\${NC}"
    fi
}

# Function to show status
show_status() {
    if is_running; then
        echo -e "\${GREEN}Download Manager is running\\${NC}"
        if [ -f "\$APP_DIR/.app.pid" ]; then
            echo -e "PID: \$(cat "\$APP_DIR/.app.pid")"
        fi
        echo -e "Access the web interface at: \${GREEN}http://localhost:8000\\${NC}"
    else
        echo -e "\${YELLOW}Download Manager is not running\\${NC}"
    fi
}

# Function to show logs
show_logs() {
    if [ -f "\$APP_DIR/logs/app.log" ]; then
        tail -f "\$APP_DIR/logs/app.log"
    else
        echo -e "\${RED}No log file found\\${NC}"
    fi
}

# Function to update the application
update_app() {
    echo -e "\${YELLOW}Updating Download Manager...\\${NC}"
    cd "\$APP_DIR"
    
    # Stop the app if running
    if is_running; then
        stop_app
        RESTART_AFTER_UPDATE=true
    fi
    
    # Update from git if it's a git repository
    if [ -d ".git" ]; then
        git pull origin main
    fi
    
    # Update dependencies
    source venv/bin/activate
    pip install -r requirements.txt --upgrade
    
    echo -e "\${GREEN}Update complete\\${NC}"
    
    # Restart if it was running before
    if [ "\$RESTART_AFTER_UPDATE" == "true" ]; then
        start_app --background
    fi
}

# Main script logic
case "\$1" in
    start)
        if is_running; then
            echo -e "\${YELLOW}Download Manager is already running\\${NC}"
        else
            start_app "\$2"
        fi
        ;;
    stop)
        stop_app
        ;;
    restart)
        stop_app
        sleep 2
        start_app "\$2"
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    update)
        update_app
        ;;
    help|--help|-h)
        echo "Download Manager Control Script"
        echo ""
        echo "Usage: \$0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  start [--background|-b]  Start the download manager"
        echo "  stop                     Stop the download manager"
        echo "  restart                  Restart the download manager"
        echo "  status                   Show current status"
        echo "  logs                     Show application logs"
        echo "  update                   Update the application"
        echo "  help                     Show this help message"
        echo ""
        echo "If no command is specified, the application will start in foreground mode."
        ;;
    *)
        # If no argument provided, just start the app
        if is_running; then
            echo -e "\${YELLOW}Download Manager is already running\\${NC}"
            show_status
        else
            start_app
        fi
        ;;
esac
EOL
    chmod +x "$PARENT_DIR/$LAUNCHER_NAME"
fi

echo -e "${GREEN}Created launcher: $PARENT_DIR/$LAUNCHER_NAME${NC}"

# Create systemd service file (for Linux only)
if [[ "$OS_TYPE" != "unsupported" ]] && [[ "$OSTYPE" != "msys" ]] && [[ "$OSTYPE" != "win32" ]]; then
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

# Create desktop entry (for Linux desktop environments)
if [[ "$OS_TYPE" != "unsupported" ]] && [[ -d "$HOME/.local/share/applications" ]]; then
    echo -e "${YELLOW}Creating desktop entry...${NC}"
    
    cat > "$HOME/.local/share/applications/downloadmanager.desktop" << EOL
[Desktop Entry]
Name=Download Manager
Comment=Advanced Download Manager with Web UI
Exec=$PARENT_DIR/$LAUNCHER_NAME
Icon=$INSTALL_DIR/frontend/static/images/icon.png
Terminal=true
Type=Application
Categories=Network;Utility;
EOL
    
    echo -e "${GREEN}Desktop entry created${NC}"
fi

# Create initial configuration files
if [ ! -f "config/config.json" ]; then
    echo -e "${YELLOW}Creating default configuration...${NC}"
    cat > "config/config.json" << EOL
{
    "links_file": "downloads/queue.txt",
    "download_dir": "downloads",
    "max_concurrent_downloads": 3,
    "timeout": 300,
    "retry_attempts": 5
}
EOL
fi

if [ ! -f "config/settings.json" ]; then
    cat > "config/settings.json" << EOL
{
    "global_chunk_size": 1048576,
    "global_chunk_number": 8,
    "max_speed_limit": 0,
    "auto_start": true,
    "resume_on_startup": true,
    "min_split_size": 10485760,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "proxy": ""
}
EOL
fi

# Final setup summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Installation Directory:${NC} $INSTALL_DIR"
echo -e "${BLUE}Launcher Location:${NC} $PARENT_DIR/$LAUNCHER_NAME"
echo ""
echo -e "${YELLOW}To start the Download Manager:${NC}"
echo -e "  cd $PARENT_DIR"
echo -e "  ./$LAUNCHER_NAME"
echo ""
echo -e "${YELLOW}Or run with options:${NC}"
echo -e "  ./$LAUNCHER_NAME start --background   # Run in background"
echo -e "  ./$LAUNCHER_NAME stop                  # Stop the service"
echo -e "  ./$LAUNCHER_NAME status                # Check status"
echo -e "  ./$LAUNCHER_NAME logs                  # View logs"
echo ""
echo -e "${GREEN}The web interface will be available at:${NC} http://localhost:8000"
echo ""

# Ask if user wants to start now
read -p "Do you want to start Download Manager now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$PARENT_DIR"
    ./$LAUNCHER_NAME
fi
