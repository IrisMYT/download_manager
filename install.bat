@echo off
setlocal enabledelayedexpansion

echo ========================================
echo     Download Manager Installer
echo ========================================
echo.

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed!
    echo Please download and install Python from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

:: Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set INSTALL_DIR=%SCRIPT_DIR%
set PARENT_DIR=%SCRIPT_DIR%..

:: Create directories
echo Creating directory structure...
mkdir backend 2>nul
mkdir frontend\static\css 2>nul
mkdir frontend\static\js 2>nul
mkdir frontend\static\images 2>nul
mkdir frontend\templates 2>nul
mkdir config 2>nul
mkdir downloads 2>nul
mkdir logs 2>nul

:: Create virtual environment
echo Creating virtual environment...
if not exist venv (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install requirements
echo Installing dependencies...
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    :: Create requirements.txt if it doesn't exist
    (
        echo fastapi==0.104.1
        echo uvicorn[standard]==0.24.0
        echo requests==2.31.0
        echo python-multipart==0.0.6
        echo aiofiles==23.2.1
        echo tqdm==4.66.1
    ) > requirements.txt
    pip install -r requirements.txt
)

:: Create launcher batch file
echo Creating launcher...
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%"
    echo if not exist venv (
    echo     echo Virtual environment not found. Running setup...
    echo     call install.bat
    echo )
    echo call venv\Scripts\activate.bat
    echo python main.py
    echo pause
) > "%PARENT_DIR%\downloadmanager.bat"

:: Create default config files
if not exist config\config.json (
    echo Creating default configuration...
    (
        echo {
        echo     "links_file": "downloads/queue.txt",
        echo     "download_dir": "downloads",
        echo     "max_concurrent_downloads": 3,
        echo     "timeout": 300,
        echo     "retry_attempts": 5
        echo }
    ) > config\config.json
)

if not exist config\settings.json (
    (
        echo {
        echo     "global_chunk_size": 1048576,
        echo     "global_chunk_number": 8,
        echo     "max_speed_limit": 0,
        echo     "auto_start": true,
        echo     "resume_on_startup": true,
        echo     "min_split_size": 10485760,
        echo     "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        echo     "proxy": ""
        echo }
    ) > config\settings.json
)

echo.
echo ========================================
echo     Installation Complete!
echo ========================================
echo.
echo Launcher created at: %PARENT_DIR%\downloadmanager.bat
echo.
echo To start Download Manager:
echo   1. Double-click downloadmanager.bat in the parent directory
echo   2. Or run it from command prompt
echo.
echo The web interface will be available at: http://localhost:8000
echo.

set /p START_NOW=Do you want to start Download Manager now? (y/n): 
if /i "%START_NOW%"=="y" (
    cd /d "%PARENT_DIR%"
    call downloadmanager.bat
)
