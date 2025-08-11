from downloader.manager import DownloadManager

if __name__ == "__main__":
    try:
        DownloadManager().run()
        except KeyboardInterrupt:
        print("
Stopped by user.")