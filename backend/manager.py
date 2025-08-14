import os
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
from queue import Queue, Empty

from .config import ConfigManager
from .downloader import FileDownloader, DownloadTask

logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.downloader = FileDownloader(self.config_manager)
        self.download_queue = Queue()
        self.active_downloads = {}
        self.completed_downloads = []
        self.failed_downloads = []
        self.executor = None
        self.running = False
        self.state_file = "downloads/download_state.json"
        
        # Load previous state if resume is enabled
        if self.config_manager.settings.resume_on_startup:
            self.load_state()
    
    def start(self):
        """Start the download manager"""
        if not self.running:
            self.running = True
            max_concurrent = self.config_manager.config.max_concurrent_downloads
            self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
            
            # Start queue processor
            processor_thread = threading.Thread(target=self._process_queue)
            processor_thread.daemon = True
            processor_thread.start()
            
            logger.info(f"Download manager started with {max_concurrent} concurrent downloads")
    
    def stop(self):
        """Stop the download manager"""
        self.running = False
        if self.executor:
            self.executor.shutdown(wait=True)
        self.save_state()
        logger.info("Download manager stopped")
    
    def add_download(self, url: str) -> str:
        """Add a new download to the queue"""
        task = self.downloader.create_download_task(url)
        self.download_queue.put(task.id)
        
        if self.config_manager.settings.auto_start:
            self.start()
        
        logger.info(f"Added download: {task.filename} (ID: {task.id})")
        return task.id
    
    def add_downloads_batch(self, urls: List[str]) -> List[str]:
        """Add multiple downloads at once"""
        task_ids = []
        for url in urls:
            if url.strip():
                task_id = self.add_download(url.strip())
                task_ids.append(task_id)
        return task_ids
    
    def _process_queue(self):
        """Process downloads from the queue"""
        while self.running:
            try:
                # Check if we can start a new download
                if len(self.active_downloads) < self.config_manager.config.max_concurrent_downloads:
                    task_id = self.download_queue.get(timeout=1)
                    
                    # Submit download task
                    future = self.executor.submit(self._download_worker, task_id)
                    self.active_downloads[task_id] = future
                else:
                    # Clean up completed downloads
                    completed = []
                    for task_id, future in self.active_downloads.items():
                        if future.done():
                            completed.append(task_id)
                    
                    for task_id in completed:
                        del self.active_downloads[task_id]
                        task = self.downloader.get_task_status(task_id)
                        if task:
                            if task.status == 'completed':
                                self.completed_downloads.append(task_id)
                            else:
                                self.failed_downloads.append(task_id)
                    
                    # Save state periodically
                    self.save_state()
                    
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
    
    def _download_worker(self, task_id: str):
        """Worker function for downloading files"""
        def progress_callback(task: DownloadTask):
            # This callback can be used to update UI or log progress
            pass
        
        try:
            success = self.downloader.download(task_id, progress_callback)
            return success
        except Exception as e:
            logger.error(f"Download worker error for {task_id}: {e}")
            return False
    
    def pause_download(self, task_id: str):
        """Pause a specific download"""
        self.downloader.pause_download(task_id)
    
    def resume_download(self, task_id: str):
        """Resume a specific download"""
        self.downloader.resume_download(task_id)
    
    def cancel_download(self, task_id: str):
        """Cancel a specific download"""
        self.downloader.cancel_download(task_id)
        
        # Remove from active downloads
        if task_id in self.active_downloads:
            future = self.active_downloads[task_id]
            future.cancel()
            del self.active_downloads[task_id]
    
    def get_all_downloads(self) -> Dict[str, List[DownloadTask]]:
        """Get all downloads grouped by status"""
        all_tasks = list(self.downloader.active_downloads.values())
        
        result = {
            'active': [],
            'queued': [],
            'completed': [],
            'failed': [],
            'paused': []
        }
        
        for task in all_tasks:
            if task.status == 'downloading':
                result['active'].append(task)
            elif task.status == 'pending':
                result['queued'].append(task)
            elif task.status == 'completed':
                result['completed'].append(task)
            elif task.status == 'failed':
                result['failed'].append(task)
            elif task.status == 'paused':
                result['paused'].append(task)
        
        return result
    
    def get_download_status(self, task_id: str) -> Optional[DownloadTask]:
        """Get status of a specific download"""
        return self.downloader.get_task_status(task_id)
    
    def clear_completed(self):
        """Clear completed downloads from history"""
        completed_ids = [task_id for task_id, task in self.downloader.active_downloads.items() 
                        if task.status == 'completed']
        
        for task_id in completed_ids:
            del self.downloader.active_downloads[task_id]
        
        self.completed_downloads.clear()
    
    def retry_failed(self):
        """Retry all failed downloads"""
        failed_tasks = [task for task in self.downloader.active_downloads.values() 
                       if task.status == 'failed']
        
        for task in failed_tasks:
            task.status = 'pending'
            task.error = None
            self.download_queue.put(task.id)
    
    def save_state(self):
        """Save current download state to file"""
        try:
            state = {
                'active_downloads': {
                    task_id: {
                        'url': task.url,
                        'filepath': task.filepath,
                        'downloaded_size': task.downloaded_size,
                        'total_size': task.total_size,
                        'status': task.status
                    }
                    for task_id, task in self.downloader.active_downloads.items()
                    if task.status in ['downloading', 'paused', 'pending']
                }
            }
            
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def load_state(self):
        """Load previous download state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                for task_id, task_data in state.get('active_downloads', {}).items():
                    # Re-create download tasks
                    task = self.downloader.create_download_task(task_data['url'])
                    task.downloaded_size = task_data.get('downloaded_size', 0)
                    task.status = 'pending'  # Reset to pending
                    
                    # Add to queue
                    self.download_queue.put(task.id)
                
                logger.info(f"Loaded {len(state.get('active_downloads', {}))} downloads from previous session")
                
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
