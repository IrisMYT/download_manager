import uvicorn
import logging
import sys
import os

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.api import app
    print("Successfully imported API")
except Exception as e:
    print(f"Failed to import API: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
    
    # Serve index.html
    @app.get("/")
    async def read_index():
        return FileResponse('frontend/index.html')
    
    print("Successfully configured routes")
except Exception as e:
    print(f"Failed to configure routes: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    print("Starting Download Manager in debug mode...")
    print("Open http://localhost:8000 in your browser")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        reload=False
    )
