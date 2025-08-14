import os
import json
import uuid
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue, Empty
import time

from .downloader import Downloader
from .config import ConfigManager
from .progress import ProgressTracker

@dataclass
class DownloadTask:
    id: str
    url: str
    filename: str = ""
    filepath: str = ""
    total_size: int = 0
    downloaded_size: int = 0
    status: str = "queued"  # queued, downloading, paused, completed, failed, cancelled
    speed: float = 0.0
    progress: float = 0.0
    error: Optional[str] = None
    eta: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    chunks: List[Dict] = field(default_factory=list)

class DownloadManager:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.tasks: Dict[str, DownloadTask] = {}
        self.download_queue = Queue()
        self.active_downloads: Dict[str, Downloader] = {}
        self.progress_tracker = ProgressTracker()
        self.running = False
        self.worker_threads = []
        self.lock = threading.Lock()
        
        # Load saved tasks
        self.load_tasks()

    def start(self):
        """Start the download manager"""
        self.running = True
        
        # Start worker threads
        for i in range(self.config_manager.config.max_concurrent_downloads):
            thread = threading.Thread(target=self._worker, daemon=True)
            thread.start()
            self.worker_threads.append(thread)
        
        # Resume downloads if configured
        if self.config_manager.settings.resume_on_startup:
            self.resume_all()

    def stop(self):
        """Stop the download manager"""
        self.running = False
        
        # Cancel all active downloads
        for task_id in list(self.active_downloads.keys()):
            self.cancel_download(task_id)
        
        # Save tasks
        self.save_tasks()

    def _worker(self):
        """Worker thread that processes downloads"""
        while self.running:
            try:
                task_id = self.download_queue.get(timeout=1)
                if task_id in self.tasks:
                    self._process_download(task_id)
            except Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")

    def _process_download(self, task_id: str):
        """Process a single download"""
        task = self.tasks[task_id]
        
        try:
            # Update status
            with self.lock:
                task.status = "downloading"
                task.start_time = datetime.now()
            
            # Create downloader
            downloader = Downloader(
                url=task.url,
                output_path=self.config_manager.config.download_dir,
                config=self.config_manager.settings
            )
            
            # Store in active downloads
            with self.lock:
                self.active_downloads[task_id] = downloader
            
            # Set progress callback
            def progress_callback(downloaded, total, speed):
                with self.lock:
                    task.downloaded_size = downloaded
                    task.total_size = total
                    task.speed = speed
                    task.progress = (downloaded / total * 100) if total > 0 else 0
                    task.eta = int((total - downloaded) / speed) if speed > 0 else 0
                    
                    # Update filename if not set
                    if not task.filename and downloader.filename:
                        task.filename = downloader.filename
                        task.filepath = os.path.join(
                            self.config_manager.config.download_dir,
                            task.filename
                        )
            
            downloader.progress_callback = progress_callback
            
            # Start download
            success = downloader.download()
            
            # Update task status
            with self.lock:
                if success:
                    task.status = "completed"
                    task.end_time = datetime.now()
                    task.progress = 100.0
                else:
                    if task.status != "cancelled":
                        task.status = "failed"
                        task.error = downloader.error or "Unknown error"
                
                # Remove from active downloads
                if task_id in self.active_downloads:
                    del self.active_downloads[task_id]
            
        except Exception as e:
            with self.lock:
                task.status = "failed"
                task.error = str(e)
                if task_id in self.active_downloads:
                    del self.active_downloads[task_id]

    def add_download(self, url: str) -> str:
        """Add a new download"""
        task_id = str(uuid.uuid4())
        
        task = DownloadTask(
            id=task_id,
            url=url
        )
        
        with self.lock:
            self.tasks[task_id] = task
        
        # Add to queue if auto-start is enabled
        if self.config_manager.settings.auto_start:
            self.download_queue.put(task_id)
        
        self.save_tasks()
        return task_id

    def add_downloads_batch(self, urls: List[str]) -> List[str]:
        """Add multiple downloads"""
        task_ids = []
        for url in urls:
            task_id = self.add_download(url)
            task_ids.append(task_id)
        return task_ids

    def pause_download(self, task_id: str):
        """Pause a download"""
        with self.lock:
            if task_id in self.active_downloads:
                self.active_downloads[task_id].pause()
                self.tasks[task_id].status = "paused"

    def resume_download(self, task_id: str):
        """Resume a download"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task and task.status in ["paused", "failed"]:
                task.status = "queued"
                task.error = None
                self.download_queue.put(task_id)

    def cancel_download(self, task_id: str):
        """Cancel a download"""
        with self.lock:
            if task_id in self.active_downloads:
                self.active_downloads[task_id].cancel()
            
            if task_id in self.tasks:
                self.tasks[task_id].status = "cancelled"
                
                # Remove file if partially downloaded
                task = self.tasks[task_id]
                if task.filepath and os.path.exists(task.filepath):
                    try:
                        os.remove(task.filepath)
                    except:
                        pass

    def get_download_status(self, task_id: str) -> Optional[DownloadTask]:
        """Get status of a download"""
        with self.lock:
            return self.tasks.get(task_id)

    def get_all_downloads(self) -> Dict[str, List[DownloadTask]]:
        """Get all downloads grouped by status"""
        with self.lock:
            result = {
                "active": [],
                "queued": [],
                "paused": [],
                "completed": [],
                "failed": []
            }
            
            for task in self.tasks.values():
                if task.status == "downloading":
                    result["active"].append(task)
                elif task.status == "queued":
                    result["queued"].append(task)
                elif task.status == "paused":
                    result["paused"].append(task)
                elif task.status == "completed":
                    result["completed"].append(task)
                elif task.status == "failed":
                    result["failed"].append(task)
            
            return result

    def clear_completed(self):
        """Clear completed downloads from the list"""
        with self.lock:
            completed_ids = [
                task_id for task_id, task in self.tasks.items()
                if task.status == "completed"
            ]
            
            for task_id in completed_ids:
                del self.tasks[task_id]
        
        self.save_tasks()

    def retry_failed(self):
        """Retry all failed downloads"""
        with self.lock:
            failed_tasks = [
                task for task in self.tasks.values()
                if task.status == "failed"
            ]
            
            for task in failed_tasks:
                task.status = "queued"
                task.error = None
                self.download_queue.put(task.id)

    def resume_all(self):
        """Resume all paused/incomplete downloads"""
        with self.lock:
            resumable_tasks = [
                task for task in self.tasks.values()
                if task.status in ["paused", "downloading"]
            ]
            
            for task in resumable_tasks:
                task.status = "queued"
                self.download_queue.put(task.id)

    def save_tasks(self):
        """Save tasks to file"""
        try:
            tasks_data = {}
            with self.lock:
                for task_id, task in self.tasks.items():
                    # Only save non-completed tasks
                    if task.status != "completed":
                        tasks_data[task_id] = {
                            "id": task.id,
                            "url": task.url,
                            "filename": task.filename,
                            "filepath": task.filepath,
                            "total_size": task.total_size,
                            "downloaded_size": task.downloaded_size,
                            "status": "paused" if task.status == "downloading" else task.status,
                            "chunks": task.chunks
                        }
            
            os.makedirs("config", exist_ok=True)
            with open("config/tasks.json", "w") as f:
                json.dump(tasks_data, f, indent=2)
        except Exception as e:
            print(f"Error saving tasks: {e}")

    def load_tasks(self):
        """Load tasks from file"""
        try:
            if os.path.exists("config/tasks.json"):
                with open("config/tasks.json", "r") as f:
                    tasks_data = json.load(f)
                
                for task_id, data in tasks_data.items():
                    task = DownloadTask(**data)
                    self.tasks[task_id] = task
        except Exception as e:
            print(f"Error loading tasks: {e}")
