class MediaTransferManager {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.maxFileSize = 100 * 1024 * 1024; // 100MB
        this.supportedPhotoFormats = ['.jpg', '.jpeg', '.png', '.gif', '.heic', '.heif'];
        this.supportedVideoFormats = ['.mp4', '.mov', '.m4v', '.avi', '.mkv'];
    }

    // Initialize media transfer UI
    init() {
        this.setupEventListeners();
        this.loadMediaInfo();
        console.log('MediaTransferManager initialized for session:', this.sessionId);
    }

    setupEventListeners() {
        // Photo upload
        const photoInput = document.getElementById('photoUpload');
        if (photoInput) {
            photoInput.addEventListener('change', (e) => this.handlePhotoUpload(e));
        }

        // Video upload
        const videoInput = document.getElementById('videoUpload');
        if (videoInput) {
            videoInput.addEventListener('change', (e) => this.handleVideoUpload(e));
        }

        // File push
        const pushFileBtn = document.getElementById('pushFileBtn');
        if (pushFileBtn) {
            pushFileBtn.addEventListener('click', () => this.handleFilePush());
        }

        // File pull
        const pullFileBtn = document.getElementById('pullFileBtn');
        if (pullFileBtn) {
            pullFileBtn.addEventListener('click', () => this.handleFilePull());
        }

        // Drag and drop
        this.setupDragAndDrop();
    }

    setupDragAndDrop() {
        const dropZone = document.getElementById('mediaDropZone');
        if (!dropZone) return;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-highlight'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-highlight'), false);
        });

        dropZone.addEventListener('drop', (e) => this.handleDrop(e), false);
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    async handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        console.log('Files dropped:', files.length);
        
        // Categorize files
        const photos = [];
        const videos = [];
        const others = [];

        for (let file of files) {
            const ext = this.getFileExtension(file.name);
            if (this.supportedPhotoFormats.includes(ext)) {
                photos.push(file);
            } else if (this.supportedVideoFormats.includes(ext)) {
                videos.push(file);
            } else {
                others.push(file);
            }
        }

        // Upload categorized files
        try {
            if (photos.length > 0) {
                await this.uploadPhotos(photos);
            }
            if (videos.length > 0) {
                await this.uploadVideos(videos);
            }
            if (others.length > 0) {
                this.showTemporaryStatus(`⚠️ ${others.length} unsupported files skipped`);
            }
        } catch (error) {
            console.error('Error handling dropped files:', error);
            this.showTemporaryStatus('❌ Error uploading files');
        }
    }

    async handlePhotoUpload(event) {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;

        try {
            await this.uploadPhotos(files);
            event.target.value = ''; // Clear input
        } catch (error) {
            console.error('Error uploading photos:', error);
            this.showTemporaryStatus('❌ Error uploading photos');
        }
    }

    async handleVideoUpload(event) {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;

        try {
            await this.uploadVideos(files);
            event.target.value = ''; // Clear input
        } catch (error) {
            console.error('Error uploading videos:', error);
            this.showTemporaryStatus('❌ Error uploading videos');
        }
    }

    async uploadPhotos(files) {
        // Validate files
        for (let file of files) {
            if (!this.validatePhotoFile(file)) {
                throw new Error(`Invalid photo file: ${file.name}`);
            }
        }

        this.showTemporaryStatus(`📷 Uploading ${files.length} photo(s)...`);

        const formData = new FormData();
        files.forEach(file => {
            formData.append('photos', file);
        });

        try {
            const response = await fetch(`/api/sessions/${this.sessionId}/media/photos/add`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.showTemporaryStatus(`✅ Added ${result.count} photo(s) to simulator`);
                console.log('Photos uploaded successfully:', result);
            } else {
                throw new Error(result.message || 'Failed to upload photos');
            }
        } catch (error) {
            console.error('Photo upload error:', error);
            throw error;
        }
    }

    async uploadVideos(files) {
        // Validate files
        for (let file of files) {
            if (!this.validateVideoFile(file)) {
                throw new Error(`Invalid video file: ${file.name}`);
            }
        }

        this.showTemporaryStatus(`🎥 Uploading ${files.length} video(s)...`);

        const formData = new FormData();
        files.forEach(file => {
            formData.append('videos', file);
        });

        try {
            const response = await fetch(`/api/sessions/${this.sessionId}/media/videos/add`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.showTemporaryStatus(`✅ Added ${result.count} video(s) to simulator`);
                console.log('Videos uploaded successfully:', result);
            } else {
                throw new Error(result.message || 'Failed to upload videos');
            }
        } catch (error) {
            console.error('Video upload error:', error);
            throw error;
        }
    }

    async handleFilePush() {
        const fileInput = document.getElementById('pushFileInput');
        const devicePathInput = document.getElementById('devicePathInput');
        const bundleIdInput = document.getElementById('bundleIdInput');

        if (!fileInput?.files?.[0]) {
            this.showTemporaryStatus('❌ Please select a file to push');
            return;
        }

        if (!devicePathInput?.value?.trim()) {
            this.showTemporaryStatus('❌ Please enter device path');
            return;
        }

        const file = fileInput.files[0];
        const devicePath = devicePathInput.value.trim();
        const bundleId = bundleIdInput?.value?.trim() || null;

        this.showTemporaryStatus(`📤 Pushing ${file.name}...`);

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('device_path', devicePath);
            if (bundleId) {
                formData.append('bundle_id', bundleId);
            }

            const response = await fetch(`/api/sessions/${this.sessionId}/files/push`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.showTemporaryStatus(`✅ Pushed ${result.filename} to simulator`);
                console.log('File pushed successfully:', result);
                
                // Clear inputs
                fileInput.value = '';
                devicePathInput.value = '';
                if (bundleIdInput) bundleIdInput.value = '';
            } else {
                throw new Error(result.message || 'Failed to push file');
            }
        } catch (error) {
            console.error('File push error:', error);
            this.showTemporaryStatus('❌ Error pushing file');
        }
    }

    async handleFilePull() {
        const devicePathInput = document.getElementById('pullDevicePathInput');
        const bundleIdInput = document.getElementById('pullBundleIdInput');
        const filenameInput = document.getElementById('pullFilenameInput');

        if (!devicePathInput?.value?.trim()) {
            this.showTemporaryStatus('❌ Please enter device path');
            return;
        }

        const devicePath = devicePathInput.value.trim();
        const bundleId = bundleIdInput?.value?.trim() || null;
        const filename = filenameInput?.value?.trim() || null;

        this.showTemporaryStatus(`📥 Pulling file from simulator...`);

        try {
            const formData = new FormData();
            formData.append('device_path', devicePath);
            if (bundleId) {
                formData.append('bundle_id', bundleId);
            }
            if (filename) {
                formData.append('filename', filename);
            }

            const response = await fetch(`/api/sessions/${this.sessionId}/files/pull`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                // Get filename from response headers or use default
                const contentDisposition = response.headers.get('content-disposition');
                let downloadFilename = 'pulled_file';
                if (contentDisposition) {
                    const matches = /filename="([^"]*)"/.exec(contentDisposition);
                    if (matches) downloadFilename = matches[1];
                }

                // Create download link
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = downloadFilename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                this.showTemporaryStatus(`✅ Downloaded ${downloadFilename}`);
                console.log('File pulled successfully');
                
                // Clear inputs
                devicePathInput.value = '';
                if (bundleIdInput) bundleIdInput.value = '';
                if (filenameInput) filenameInput.value = '';
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to pull file');
            }
        } catch (error) {
            console.error('File pull error:', error);
            this.showTemporaryStatus('❌ Error pulling file');
        }
    }

    async loadMediaInfo() {
        try {
            const response = await fetch(`/api/sessions/${this.sessionId}/media/info`);
            const result = await response.json();
            
            if (result.success) {
                this.supportedPhotoFormats = result.supported_photo_formats;
                this.supportedVideoFormats = result.supported_video_formats;
                console.log('Media info loaded:', result);
            }
        } catch (error) {
            console.error('Error loading media info:', error);
        }
    }

    validatePhotoFile(file) {
        const ext = this.getFileExtension(file.name);
        if (!this.supportedPhotoFormats.includes(ext)) {
            this.showTemporaryStatus(`❌ Unsupported photo format: ${ext}`);
            return false;
        }
        if (file.size > this.maxFileSize) {
            this.showTemporaryStatus(`❌ File too large: ${file.name}`);
            return false;
        }
        return true;
    }

    validateVideoFile(file) {
        const ext = this.getFileExtension(file.name);
        if (!this.supportedVideoFormats.includes(ext)) {
            this.showTemporaryStatus(`❌ Unsupported video format: ${ext}`);
            return false;
        }
        if (file.size > this.maxFileSize) {
            this.showTemporaryStatus(`❌ File too large: ${file.name}`);
            return false;
        }
        return true;
    }

    getFileExtension(filename) {
        return filename.toLowerCase().substring(filename.lastIndexOf('.'));
    }

    showTemporaryStatus(message) {
        console.log(message);
        
        // Try to use existing status function
        if (typeof showTemporaryStatus === 'function') {
            showTemporaryStatus(message);
        } else {
            // Fallback: show in console and try to find a status element
            const statusElement = document.getElementById('statusMessage') || 
                                 document.querySelector('.status-message') ||
                                 document.querySelector('.status');
            
            if (statusElement) {
                statusElement.textContent = message;
                setTimeout(() => {
                    statusElement.textContent = '';
                }, 3000);
            }
        }
    }

    // Utility method to get app container path
    async getAppContainerPath(bundleId) {
        try {
            const response = await fetch(`/api/sessions/${this.sessionId}/files/app-container?bundle_id=${bundleId}`);
            const result = await response.json();
            
            if (result.success) {
                return result.container_path;
            } else {
                throw new Error('Failed to get app container path');
            }
        } catch (error) {
            console.error('Error getting app container path:', error);
            return null;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Get session ID from global variable or URL
    const sessionId = window.SESSION_ID || document.body.getAttribute('data-session-id');
    
    if (sessionId) {
        window.mediaTransferManager = new MediaTransferManager(sessionId);
        // Don't auto-init, let the main app control this
    } else {
        console.warn('Session ID not found for MediaTransferManager');
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MediaTransferManager;
}