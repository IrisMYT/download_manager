import time
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class ProgressInfo:
    task_id: str
    downloaded: int
    total: int
    speed: float
    progress: float
    eta: int

class ProgressTracker:
    def __init__(self):
        self.progress_data: Dict[str, ProgressInfo] = {}
        self.last_update: Dict[str, float] = {}

    def update(self, task_id: str, downloaded: int, total: int, speed: float):
        """Update progress for a task"""
        progress = (downloaded / total * 100) if total > 0 else 0
        eta = int((total - downloaded) / speed) if speed > 0 else 0
        
        self.progress_data[task_id] = ProgressInfo(
            task_id=task_id,
            downloaded=downloaded,
            total=total,
            speed=speed,
            progress=progress,
            eta=eta
        )
        
        self.last_update[task_id] = time.time()

    def get(self, task_id: str) -> Optional[ProgressInfo]:
        """Get progress for a task"""
        return self.progress_data.get(task_id)

    def remove(self, task_id: str):
        """Remove progress data for a task"""
        if task_id in self.progress_data:
            del self.progress_data[task_id]
        if task_id in self.last_update:
            del self.last_update[task_id]

    def get_all(self) -> Dict[str, ProgressInfo]:
        """Get all progress data"""
        return self.progress_data.copy()
