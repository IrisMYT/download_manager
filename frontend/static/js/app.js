const API_BASE = 'http://localhost:8000/api';
let updateInterval;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeDragDrop();
    startUpdating();
    loadSettings();
});

// Drag and Drop functionality
function initializeDragDrop() {
    const dropZone = document.getElementById('dropZone');
    const urlInput = document.getElementById('urlInput');
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);
    
    // Handle text drag
    dropZone.addEventListener('dragover', (e) => {
        e.dataTransfer.dropEffect = 'copy';
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight(e) {
        dropZone.classList.add('drag-over');
    }
    
    function unhighlight(e) {
        dropZone.classList.remove('drag-over');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        
        // Check for dragged text/URL
        const text = dt.getData('text/plain');
        if (text) {
            // Check if it's a URL
            if (isValidUrl(text)) {
                urlInput.value = text;
                addDownload();
            } else {
                // Try to extract URLs from text
                const urls = extractUrls(text);
                if (urls.length > 0) {
                    addBatchDownloads(urls);
                }
            }
            return;
        }
        
        // Handle files
        const files = dt.files;
        handleFiles(files);
    }
    
    function handleFiles(files) {
        ([...files]).forEach(processFile);
    }
    
    function processFile(file) {
        if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const urls = extractUrls(e.target.result);
                if (urls.length > 0) {
                    addBatchDownloads(urls);
                }
            };
            reader.readAsText(file);
        }
    }
}

// URL validation and extraction
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

function extractUrls(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const matches = text.match(urlRegex) || [];
    return matches.filter(url => isValidUrl(url));
}

// Download management
async function addDownload() {
    const urlInput = document.getElementById('urlInput');
    const url = urlInput.value.trim();
    
    if (!url) {
        showToast('Please enter a URL', 'warning');
        return;
    }
    
    if (!isValidUrl(url)) {
        showToast('Please enter a valid URL', 'danger');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/download`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url })
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast('Download added successfully', 'success');
            urlInput.value = '';
            updateDownloads();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to add download', 'danger');
        }
    } catch (error) {
        showToast('Failed to add download: ' + error.message, 'danger');
    }
}

async function addBatchDownloads(urls) {
    try {
        const response = await fetch(`${API_BASE}/download/batch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ urls })
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast(`Added ${urls.length} downloads`, 'success');
            updateDownloads();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to add downloads', 'danger');
        }
    } catch (error) {
        showToast('Failed to add downloads: ' + error.message, 'danger');
    }
}

// Import links from file
async function importLinks(input) {
    const file = input.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE}/import/links`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast(data.message, 'success');
            updateDownloads();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to import links', 'danger');
        }
    } catch (error) {
        showToast('Failed to import links: ' + error.message, 'danger');
    }
    
    input.value = '';
}

// Download controls
async function pauseDownload(taskId) {
    try {
        await fetch(`${API_BASE}/download/${taskId}/pause`, { method: 'POST' });
        updateDownloads();
    } catch (error) {
        showToast('Failed to pause download', 'danger');
    }
}

async function resumeDownload(taskId) {
    try {
        await fetch(`${API_BASE}/download/${taskId}/resume`, { method: 'POST' });
        updateDownloads();
    } catch (error) {
        showToast('Failed to resume download', 'danger');
    }
}

async function cancelDownload(taskId) {
    if (!confirm('Are you sure you want to cancel this download?')) return;
    
    try {
        await fetch(`${API_BASE}/download/${taskId}/cancel`, { method: 'POST' });
        updateDownloads();
    } catch (error) {
        showToast('Failed to cancel download', 'danger');
    }
}

// Bulk actions
async function pauseAll() {
    const downloads = await getDownloads();
    const activeTasks = downloads.active || [];
    
    for (const task of activeTasks) {
        await pauseDownload(task.id);
    }
}

async function resumeAll() {
    const downloads = await getDownloads();
    const pausedTasks = downloads.paused || [];
    
    for (const task of pausedTasks) {
        await resumeDownload(task.id);
    }
}

async function cancelAll() {
    if (!confirm('Are you sure you want to cancel all downloads?')) return;
    
    const downloads = await getDownloads();
    const allTasks = [...(downloads.active || []), ...(downloads.queued || []), ...(downloads.paused || [])];
    
    for (const task of allTasks) {
        await cancelDownload(task.id);
    }
}

async function retryFailed() {
    try {
        await fetch(`${API_BASE}/downloads/retry-failed`, { method: 'POST' });
        showToast('Failed downloads queued for retry', 'success');
        updateDownloads();
    } catch (error) {
        showToast('Failed to retry downloads', 'danger');
    }
}

async function clearCompleted() {
    try {
        await fetch(`${API_BASE}/downloads/clear-completed`, { method: 'POST' });
        showToast('Completed downloads cleared', 'success');
        updateDownloads();
    } catch (error) {
        showToast('Failed to clear completed downloads', 'danger');
    }
}

// Get downloads from API
async function getDownloads() {
    try {
        const response = await fetch(`${API_BASE}/downloads`);
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch downloads:', error);
        return {};
    }
}

// Update UI
async function updateDownloads() {
    const downloads = await getDownloads();
    
    // Update counts
    document.getElementById('activeCount').textContent = (downloads.active || []).length;
    document.getElementById('queuedCount').textContent = (downloads.queued || []).length;
    document.getElementById('completedCount').textContent = (downloads.completed || []).length;
    document.getElementById('failedCount').textContent = (downloads.failed || []).length;
    
    // Update lists
    updateDownloadList('activeDownloads', downloads.active || [], true);
    updateDownloadList('queuedDownloads', downloads.queued || [], false);
    updateDownloadList('completedDownloads', downloads.completed || [], false);
    updateDownloadList('failedDownloads', downloads.failed || [], false);
}

function updateDownloadList(containerId, tasks, showProgress) {
    const container = document.getElementById(containerId);
    
    if (tasks.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">No downloads</p>';
        return;
    }
    
    container.innerHTML = tasks.map(task => createDownloadItem(task, showProgress)).join('');
}

function createDownloadItem(task, showProgress) {
    const statusClass = `status-${task.status}`;
    const progressBar = showProgress && task.total_size > 0 ? `
        <div class="progress">
            <div class="progress-bar ${task.status === 'paused' ? 'bg-warning' : ''}" 
                 role="progressbar" 
                 style="width: ${task.progress}%">
                ${task.progress.toFixed(1)}%
            </div>
        </div>
    ` : '';
    
    const stats = showProgress ? `
        <div class="download-stats">
            <span class="download-speed">${formatSpeed(task.speed)}</span>
            <span class="download-eta">${formatETA(task.eta)}</span>
        </div>
    ` : '';
    
    const actions = getDownloadActions(task);
    
    return `
        <div class="download-item">
            <div class="download-header">
                <h6 class="download-title">${task.filename}</h6>
                <div class="download-actions">
                    <span class="status-badge ${statusClass}">${task.status}</span>
                    ${actions}
                </div>
            </div>
            <div class="download-info">
                <span>${formatBytes(task.downloaded_size)} / ${formatBytes(task.total_size)}</span>
                <span>${task.url.substring(0, 50)}...</span>
            </div>
            ${progressBar}
            ${stats}
            ${task.error ? `<div class="text-danger small mt-1">Error: ${task.error}</div>` : ''}
        </div>
    `;
}

function getDownloadActions(task) {
    switch (task.status) {
        case 'downloading':
            return `
                <button class="btn btn-sm btn-warning" onclick="pauseDownload('${task.id}')">
                    <i class="fas fa-pause"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="cancelDownload('${task.id}')">
                    <i class="fas fa-times"></i>
                </button>
            `;
        case 'paused':
            return `
                <button class="btn btn-sm btn-success" onclick="resumeDownload('${task.id}')">
                    <i class="fas fa-play"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="cancelDownload('${task.id}')">
                    <i class="fas fa-times"></i>
                </button>
            `;
        case 'failed':
            return `
                <button class="btn btn-sm btn-info" onclick="resumeDownload('${task.id}')">
                    <i class="fas fa-redo"></i>
                </button>
            `;
        default:
            return '';
    }
}

// Settings management
async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        const data = await response.json();
        
        // Load config values
        Object.entries(data.config).forEach(([key, value]) => {
            const input = document.getElementById(key);
            if (input) input.value = value;
        });
        
        // Load settings values
        Object.entries(data.settings).forEach(([key, value]) => {
            const input = document.getElementById(key);
            if (input) {
                if (input.type === 'checkbox') {
                    input.checked = value;
                } else {
                    input.value = value;
                }
            }
        });
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function saveSettings() {
    const config = {};
    const settings = {};
    
    // Get config values
    ['download_dir', 'max_concurrent_downloads', 'timeout', 'retry_attempts'].forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            config[id] = input.type === 'number' ? parseInt(input.value) : input.value;
        }
    });
    
    // Get settings values
    ['global_chunk_size', 'global_chunk_number', 'max_speed_limit', 'min_split_size'].forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            settings[id] = parseInt(input.value);
        }
    });
    
    ['auto_start', 'resume_on_startup'].forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            settings[id] = input.checked;
        }
    });
    
    try {
        const response = await fetch(`${API_BASE}/config`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ config, settings })
        });
        
        if (response.ok) {
            showToast('Settings saved successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();
        } else {
            throw new Error('Failed to save settings');
        }
    } catch (error) {
        showToast('Failed to save settings', 'danger');
    }
}

function showSettings() {
    const modal = new bootstrap.Modal(document.getElementById('settingsModal'));
    modal.show();
}

// Utility functions
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatSpeed(bytesPerSecond) {
    if (!bytesPerSecond || bytesPerSecond === 0) return '0 KB/s';
    return formatBytes(bytesPerSecond, 1) + '/s';
}

function formatETA(seconds) {
    if (!seconds || seconds === 0) return 'Unknown';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

function showToast(message, type = 'info') {
    const toastHTML = `
        <div class="toast" role="alert">
            <div class="toast-header bg-${type} text-white">
                <strong class="me-auto">Download Manager</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    const toastElement = document.createElement('div');
    toastElement.innerHTML = toastHTML;
    
    toastContainer.appendChild(toastElement.firstElementChild);
    
    const toast = new bootstrap.Toast(toastContainer.lastElementChild);
    toast.show();
    
    // Remove toast after it's hidden
    toastContainer.lastElementChild.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// Auto-update
function startUpdating() {
    updateDownloads();
    updateInterval = setInterval(updateDownloads, 1000);
}

function stopUpdating() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
            case 'v':
                // Paste URL from clipboard
                navigator.clipboard.readText().then(text => {
                    if (isValidUrl(text)) {
                        document.getElementById('urlInput').value = text;
                        addDownload();
                    }
                });
                e.preventDefault();
                break;
            case 's':
                // Show settings
                showSettings();
                e.preventDefault();
                break;
        }
    }
});
