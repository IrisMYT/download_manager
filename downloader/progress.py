from tqdm import tqdm
import time

class DownloadProgress:
    def __init__(self, total_size, filename):
        self.start_time = time.time()
        try:
            # Limit filename display length
            display_name = filename[:50] + "..." if len(filename) > 50 else filename
            self.pbar = tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=display_name,
                ascii=True,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                miniters=1,
                mininterval=0.5  # Update less frequently for better performance
            )
        except Exception:
            self.pbar = None

    def update(self, size):
        try:
            if self.pbar:
                self.pbar.update(size)
        except:
            pass

    def close(self):
        try:
            if self.pbar:
                self.pbar.close()
        except:
            pass
