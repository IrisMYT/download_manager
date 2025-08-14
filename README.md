# Enhanced Download Manager

A powerful download manager with Web UI, drag-and-drop support, and advanced features.

## Features

- 🌐 **Web-based UI** with modern, responsive design
- 🎯 **Drag and Drop** support for URLs and text files
- ⚡ **Multi-threaded Downloads** with configurable chunks
- ⏸️ **Pause/Resume** functionality
- 🔄 **Auto-retry** failed downloads
- 📊 **Real-time Progress** tracking
- ⚙️ **Configurable Settings** via Web UI
- 💾 **Persistent State** - resume downloads after restart
- 🚀 **Speed Limiting** support
- 📋 **Batch Downloads** from text files
- 🔍 **Download History** with status tracking

## Installation

1. Clone the repository
2. Run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh

Usage

    Start the application:

            

    bash
    source venv/bin/activate
    python main.py

    Open your browser and navigate to http://localhost:8000

    Add downloads by:
        Typing/pasting URLs in the input field
        Dragging and dropping URLs from your browser
        Importing a text file with URLs
        Dragging text containing URLs to the drop zone

Configuration
config.json

    download_dir: Directory where files will be saved
    max_concurrent_downloads: Number of simultaneous downloads
    timeout: Request timeout in seconds
    retry_attempts: Number of retry attempts for failed downloads

settings.json

    global_chunk_size: Size of each download chunk in bytes
    global_chunk_number: Number of parallel connections per file
    max_speed_limit: Maximum download speed in KB/s (0 = unlimited)
    auto_start: Automatically start downloads when added
    resume_on_startup: Resume incomplete downloads on startup
    min_split_size: Minimum file size to use multi-threaded download

API Endpoints

    POST /api/download - Add single download
    POST /api/download/batch - Add multiple downloads
    GET /api/downloads - Get all downloads
    POST /api/download/{id}/pause - Pause download
    POST /api/download/{id}/resume - Resume download
    POST /api/download/{id}/cancel - Cancel download
    GET /api/config - Get configuration
    PUT /api/config - Update configuration

Keyboard Shortcuts

    Ctrl+V - Paste URL and start download
    Ctrl+S - Open settings

License

MIT License

        

text

## Key Improvements Made:

1. **Enhanced Download Handling**:
   - Multi-threaded downloads with configurable chunks
   - Proper pause/resume functionality
   - Speed limiting support
   - Better error handling and retry logic
   - Persistent state across restarts

2. **Web UI Features**:
   - Modern, responsive design with Bootstrap
   - Drag and drop support for URLs and files
   - Real-time progress updates
   - Tabbed interface for different download states
   - Settings editor for both config.json and settings.json

3. **API Backend**:
   - RESTful API with FastAPI
   - WebSocket support for real-time updates (can be added)
   - Proper error handling and validation

4. **Configuration**:
   - Separate config files for general and download settings
   - All settings editable through Web UI
   - Global chunk size and number configuration

5. **Additional Features**:
   - Download queue management
   - Batch import from text files
   - Download history tracking
   - Keyboard shortcuts
   - Toast notifications for user feedback

The application is now production-ready with proper error handling, logging, and a user-friendly interface. All the requested features have been implemented, including the IDM-like drag-and-drop functionality.




Usage Instructions
For Fresh Installation on Blank System:

    Using Git:

            

bash
git clone https://github.com/yourusername/download-manager
cd download_manager
chmod +x setup.sh
./setup.sh

Using ZIP download:

        

bash
# Download and extract the ZIP
wget https://github.com/yourusername/download-manager/archive/main.zip
unzip main.zip
cd download-manager-main
chmod +x setup.sh
./setup.sh

One-line installer:

        

    bash
    curl -sSL https://raw.githubusercontent.com/yourusername/download-manager/main/install.sh | bash

After Installation:

The setup script creates a launcher in the parent directory. To run the program:

        

bash
# From anywhere
cd /path/to/parent/directory
./downloadmanager

# With options
./downloadmanager start --background  # Run in background
./downloadmanager stop               # Stop the service
./downloadmanager status             # Check status
./downloadmanager logs               # View logs
./downloadmanager update             # Update the application

### Features of the Enhanced Setup:

1. **Complete Dependency Management:**
   - Automatically installs Python if not present
   - Installs all system dependencies
   - Creates and configures virtual environment
   - Installs all Python packages

2. **Smart Launcher Script:**
   - Single command to start the application
   - Background mode support
   - Service management (start/stop/restart)
   - Status checking
   - Log viewing
   - Auto-update functionality

3. **Cross-Platform Support:**
   - Works on Debian/Ubuntu, RedHat/CentOS, Arch Linux
   - Windows batch file for Windows users
   - Detects OS and installs appropriate packages

4. **Additional Features:**
   - Creates systemd service file for Linux
   - Desktop entry for GUI environments
   - Automatic configuration file creation
   - Handles both git clone and ZIP download scenarios

The launcher script (`downloadmanager`) in the parent directory provides a complete management interface for the application, making it easy to use even for non-technical users.