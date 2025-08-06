# download_manager
# Multi-Threaded Download Manager 🚀

A powerful Python-based download manager that automatically optimizes download settings by testing server capabilities and using multi-threaded downloads for maximum speed.

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-green.svg)
[![Requests](https://img.shields.io/badge/requests-2.31.0-orange.svg)

## ✨ Features

- **🔍 Automatic Server Testing**: Probes servers to determine optimal settings
- **⚡ Multi-threaded Downloads**: Downloads files using multiple connections for faster speeds
- **🔄 Concurrent Downloads**: Download multiple files simultaneously
- **📊 Speed Testing**: Tests server speed and detects throttling
- **🔁 Smart Retry Logic**: Automatic retry with exponential backoff
- **📝 Batch Downloads**: Load multiple URLs from a text file
- **🎯 Range Request Support**: Automatically detects and uses partial content when available
- **📈 Progress Tracking**: Real-time download progress and status updates

## 📋 Requirements

- Python 3.7 or higher
- Dependencies listed in `requirements.txt`

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/download-manager.git
cd download-manager

2. Install dependencies:
bash
pip install -r requirements.txt

## 🚀 Usage

### Basic Usage

1. Create a `download_links.txt` file in the same directory as the script:
txt
# Add your download links here, one per line
https://example.com/file1.zip
https://example.com/file2.pdf
https://example.com/file3.mp4

2. Run the script:
bash
python script.py

3. Follow the prompts:
   - Enter the maximum number of concurrent downloads
   - Specify the download directory (or press Enter for current directory)

### Advanced Configuration

The script will automatically:
1. Test the first URL for server capabilities
2. Determine the maximum number of threads the server allows
3. Measure download speed
4. Optimize settings for best performance
5. Download all files using the optimal configuration

## 🔧 How It Works

### Server Testing Phase

1. Range Request Support ─→ Checks if server supports partial downloads
2. Thread Limit Test ─────→ Tests how many concurrent connections are allowed
3. Speed Test ────────────→ Measures download speed and detects throttling

### Download Phase

1. Single-threaded ───→ For servers without range support
2. Multi-threaded ────→ Splits file into chunks for parallel downloading
3. Concurrent ────────→ Downloads multiple files simultaneously

## 📊 Example Output


==================================================
    MULTI-THREADED DOWNLOAD MANAGER
==================================================
14:23:45 - INFO - Loaded 3 links from download_links.txt

Max concurrent downloads (default 3): 2
Save location (press Enter for current directory): ./downloads

14:23:50 - INFO - Analyzing server capabilities...
14:23:51 - INFO - Testing concurrent connection limit...
14:23:52 - INFO - Server allows 8 concurrent connections
14:23:52 - INFO - Testing download speed...
14:23:54 - INFO - Average speed: 12.45 MB/s

14:23:54 - INFO - Optimized settings:
14:23:54 - INFO -   • Threads per download: 8
14:23:54 - INFO -   • Concurrent downloads: 2

14:23:54 - INFO - Starting 3 downloads...

14:23:54 - INFO - Downloading file1.zip (245.3 MB) with 8 threads...
14:23:54 - INFO - Downloading file2.pdf (12.7 MB) with 8 threads...
14:24:12 - INFO - ✓ Completed: file2.pdf
14:24:12 - INFO - Progress: 1/3 files
14:24:35 - INFO - ✓ Completed: file1.zip
14:24:35 - INFO - Progress: 2/3 files
14:24:35 - INFO - Downloading file3.mp4 (520.1 MB) with 8 threads...
14:25:55 - INFO - ✓ Completed: file3.mp4
14:25:55 - INFO - Progress: 3/3 files
14:25:55 - INFO - ✓ All downloads completed!

## 🏗️ Architecture


DownloadManager
├── NetworkTester
│   ├── test_server()
│   ├── _test_range_support()
│   ├── _test_thread_limit()
│   └── _test_speed()
├── FileDownloader
│   ├── download()
│   ├── _single_threaded_download()
│   ├── _multi_threaded_download()
│   └── get_file_info()
└── Main Orchestrator
    ├── run()
    ├── _load_links()
    ├── _optimize_settings()
    └── _execute_downloads()

## ⚙️ Configuration Options

The `DownloadConfig` class contains all configurable parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_concurrent_downloads` | 3 | Number of files to download simultaneously |
| `threads_per_download` | 4 | Initial threads per file (auto-optimized) |
| `chunk_size` | 1MB | Size of each download chunk |
| `timeout` | 30s | Request timeout |
| `retry_attempts` | 3 | Number of retry attempts on failure |
| `links_file` | download_links.txt | Input file containing URLs |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Known Issues

- Some servers may have aggressive rate limiting that isn't detected in the initial test
- Very large files (>4GB) might need additional handling on 32-bit systems
- Servers that don't properly implement HTTP range requests may cause issues

## 🚧 Roadmap

- [ ] GUI interface using Tkinter/PyQt
- [ ] Resume capability for interrupted downloads
- [ ] Download queue management
- [ ] Bandwidth limiting options
- [ ] Proxy support
- [ ] Authentication support (Basic, OAuth)
- [ ] Download scheduling
- [ ] Chrome/Firefox extension for capturing downloads
- [ ] Configuration file support (YAML/JSON)
- [ ] Download history and statistics

## 💡 Tips

- For best performance, ensure your internet connection isn't the bottleneck
- Some servers limit connections per IP - the tool automatically detects this
- Use fewer concurrent downloads for servers with strict rate limiting
- The tool works best with servers that support HTTP range requests

## 🙏 Acknowledgments

[- Built with [Requests](https://docs.python-requests.org/) library
- Inspired by popular download managers like IDM and aria2

---

**⭐ Star this repository if you find it helpful!**


This README provides:

1. **Clear project description** with badges
2. **Comprehensive feature list** 
3. **Installation and usage instructions**
4. **Visual workflow explanation**
5. **Example output** to show what users can expect
6. **Architecture overview** for developers
7. **Configuration options** table
8. **Contributing guidelines**
9. **Roadmap** for future features
10. **Professional formatting** with emojis and sections

The `requirements.txt` includes the essential dependencies with specific versions for reproducibility.
