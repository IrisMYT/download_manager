import uvicorn
import logging
import sys
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.api import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/download_manager.log'),
        logging.StreamHandler()
    ]
)

# Create necessary directories
os.makedirs('logs', exist_ok=True)
os.makedirs('downloads', exist_ok=True)
os.makedirs('config', exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Serve index.html
@app.get("/")
async def read_index():
    return FileResponse('frontend/templates/index.html')

if __name__ == "__main__":
    print("Starting Download Manager...")
    print("Open http://localhost:8000 in your browser")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )
