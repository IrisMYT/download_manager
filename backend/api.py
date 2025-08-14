from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional
import os
import json

from .manager import DownloadManager
from .config import ConfigManager

app = FastAPI(title="Download Manager API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
download_manager = DownloadManager()
config_manager = ConfigManager()

# Pydantic models
class DownloadRequest(BaseModel):
    url: HttpUrl

class BatchDownloadRequest(BaseModel):
    urls: List[HttpUrl]

class ConfigUpdate(BaseModel):
    config: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None

@app.on_event("startup")
async def startup_event():
    """Start download manager on API startup"""
    download_manager.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop download manager on API shutdown"""
    download_manager.stop()

@app.post("/api/download")
async def add_download(request: DownloadRequest):
    """Add a new download"""
    try:
        task_id = download_manager.add_download(str(request.url))
        return {"task_id": task_id, "message": "Download added successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download/batch")
async def add_batch_downloads(request: BatchDownloadRequest):
    """Add multiple downloads"""
    try:
        urls = [str(url) for url in request.urls]
        task_ids = download_manager.add_downloads_batch(urls)
        return {"task_ids": task_ids, "message": f"Added {len(task_ids)} downloads"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/downloads")
async def get_all_downloads():
    """Get all downloads grouped by status"""
    try:
        downloads = download_manager.get_all_downloads()
        # Convert DownloadTask objects to dictionaries
        result = {}
        for status, tasks in downloads.items():
            result[status] = [
                {
                    "id": task.id,
                    "url": task.url,
                    "filename": task.filename,
                    "filepath": task.filepath,
                    "total_size": task.total_size,
                    "downloaded_size": task.downloaded_size,
                    "status": task.status,
                    "speed": task.speed,
                    "progress": task.progress,
                    "error": task.error,
                    "eta": task.eta
                }
                for task in tasks
            ]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{task_id}")
async def get_download_status(task_id: str):
    """Get status of a specific download"""
    task = download_manager.get_download_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Download not found")
    
    return {
        "id": task.id,
        "url": task.url,
        "filename": task.filename,
        "filepath": task.filepath,
        "total_size": task.total_size,
        "downloaded_size": task.downloaded_size,
        "status": task.status,
        "speed": task.speed,
        "progress": task.progress,
        "error": task.error,
        "eta": task.eta
    }

@app.post("/api/download/{task_id}/pause")
async def pause_download(task_id: str):
    """Pause a download"""
    try:
        download_manager.pause_download(task_id)
        return {"message": "Download paused"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download/{task_id}/resume")
async def resume_download(task_id: str):
    """Resume a download"""
    try:
        download_manager.resume_download(task_id)
        return {"message": "Download resumed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download/{task_id}/cancel")
async def cancel_download(task_id: str):
    """Cancel a download"""
    try:
        download_manager.cancel_download(task_id)
        return {"message": "Download cancelled"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/downloads/clear-completed")
async def clear_completed_downloads():
    """Clear all completed downloads"""
    try:
        download_manager.clear_completed()
        return {"message": "Completed downloads cleared"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/downloads/retry-failed")
async def retry_failed_downloads():
    """Retry all failed downloads"""
    try:
        download_manager.retry_failed()
        return {"message": "Failed downloads queued for retry"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "config": config_manager.get_config_dict(),
        "settings": config_manager.get_settings_dict()
    }

@app.put("/api/config")
async def update_config(update: ConfigUpdate):
    """Update configuration"""
    try:
        if update.config:
            config_manager.save_config(update.config)
        if update.settings:
            config_manager.save_settings(update.settings)
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/import/links")
async def import_links_file(file: UploadFile = File(...)):
    """Import links from a text file"""
    try:
        content = await file.read()
        urls = content.decode('utf-8').strip().split('
')
        urls = [url.strip() for url in urls if url.strip() and not url.startswith('#')]
        
        task_ids = download_manager.add_downloads_batch(urls)
        return {
            "message": f"Imported {len(task_ids)} downloads",
            "task_ids": task_ids
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
