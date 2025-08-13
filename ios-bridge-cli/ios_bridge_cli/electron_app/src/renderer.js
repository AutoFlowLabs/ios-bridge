/**
 * iOS Bridge Desktop Renderer
 * Handles WebSocket communication, video streaming, and device control
 */

class IOSBridgeRenderer {
    constructor() {
        this.config = null;
        this.websockets = {};
        this.canvas = null;
        this.ctx = null;
        this.deviceDimensions = { width: 390, height: 844 }; // logical points from frame metadata
        this.streamDimensions = { width: 0, height: 0 }; // pixel dimensions for video frames
        this.canvasDimensions = { width: 0, height: 0 };
        this.isConnected = false;
        this.currentQuality = 'high';
        this.fpsCounter = 0;
        this.lastFpsUpdate = Date.now();
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    async init() {
        try {
            // Get configuration from main process
            this.config = await window.electronAPI.getConfig();
            
            // Initialize UI
            this.initializeUI();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Connect to iOS Bridge
            await this.connect();
            
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Failed to initialize iOS Bridge Desktop');
        }
    }
    
    initializeUI() {
        // Update device info
        const deviceName = document.getElementById('device-name');
        if (deviceName) {
            const sessionInfo = this.config?.sessionInfo || {};
            const deviceType = sessionInfo.device_type || 'iOS Simulator';
            const iosVersion = sessionInfo.ios_version || '';
            deviceName.textContent = `${deviceType} ${iosVersion}`.trim();
        }
        
        // Set device and stream dimensions from config
        const sessionInfo = this.config?.sessionInfo || {};
        if (sessionInfo.device_width && sessionInfo.device_height) {
            this.deviceDimensions = {
                width: sessionInfo.device_width,
                height: sessionInfo.device_height
            };
            console.log(`Using device logical dimensions from config: ${this.deviceDimensions.width}x${this.deviceDimensions.height}`);
        }
        if (sessionInfo.stream_width && sessionInfo.stream_height) {
            this.streamDimensions = {
                width: sessionInfo.stream_width,
                height: sessionInfo.stream_height
            };
            console.log(`Using stream pixel dimensions from config: ${this.streamDimensions.width}x${this.streamDimensions.height}`);
        }
        
        // Initialize canvas
        this.canvas = document.getElementById('video-canvas');
        this.touchOverlay = document.getElementById('touch-overlay');
        this.deviceScreen = document.querySelector('.device-screen');
        
        if (this.canvas) {
            this.ctx = this.canvas.getContext('2d');
        }
        
        if (!this.canvas || !this.touchOverlay) {
            return;
        }
        
        // If we already have stream dimensions, inform main to size the window and set CSS size
        if (this.streamDimensions.width > 0 && this.streamDimensions.height > 0) {
            window.electronAPI.resizeWindow(this.streamDimensions.width, this.streamDimensions.height)
                .then((res) => {
                    if (res && !res.error) {
                        // Set CSS size of canvas and device screen to scaled content size applied by main
                        this.applyScaledCssSize(res.contentWidth, res.contentHeight);
                        this.updateOrientationClass();
                    }
                })
                .catch(err => console.error('resizeWindow error:', err));
        }
        
        // Initialize quality display
        this.updateQualityDisplay();
    }
    
    setupEventListeners() {
        // Device action buttons
        document.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = e.currentTarget?.dataset?.action || e.target.dataset.action;
                this.handleDeviceAction(action);
            });
        });
        
        // Quality menu
        document.querySelectorAll('#quality-menu .dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const quality = e.currentTarget?.dataset?.quality || e.target.dataset.quality;
                this.setQuality(quality);
            });
        });
        
        // Modal close
        document.getElementById('info-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'info-modal') {
                this.closeModal();
            }
        });
        
        // Modal close button
        document.querySelector('.modal-close')?.addEventListener('click', (e) => {
            this.closeModal();
        });
        
        // Setup canvas event listeners
        this.setupCanvasEventListeners();
        
        // Keyboard input
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
    }
    
    setupCanvasEventListeners() {
        // Use touch overlay for events since it's on top of the canvas
        const eventTarget = this.touchOverlay || this.canvas;
        
        if (eventTarget) {
            // Remove existing listeners first to avoid duplicates
            eventTarget.removeEventListener('mousedown', this.handleTouchStart);
            eventTarget.removeEventListener('mousemove', this.handleTouchMove);
            eventTarget.removeEventListener('mouseup', this.handleTouchEnd);
            
            // Add new listeners
            eventTarget.addEventListener('mousedown', this.handleTouchStart.bind(this));
            eventTarget.addEventListener('mousemove', this.handleTouchMove.bind(this));
            eventTarget.addEventListener('mouseup', this.handleTouchEnd.bind(this));
            
            eventTarget.style.cursor = 'crosshair';
        }
    }
    
    
    async connect() {
        try {
            this.disconnect();
            
            const sessionId = this.config?.sessionId;
            const serverUrl = this.config?.serverUrl;
            
            if (!sessionId || !serverUrl) {
                throw new Error('Missing session ID or server URL');
            }
            
            // Create WebSocket URLs
            const wsBase = serverUrl.replace('http://', 'ws://').replace('https://', 'wss://');
            const wsUrls = {
                video: `${wsBase}/ws/${sessionId}/video`,
                control: `${wsBase}/ws/${sessionId}/control`
            };
            
            // Connect to video WebSocket
            await this.connectWebSocket('video', wsUrls.video);
            
            // Connect to control WebSocket
            await this.connectWebSocket('control', wsUrls.control);
            
            this.isConnected = true;
            this.updateConnectionStatus('connected');
            this.showDeviceContainer();
            
            // Re-setup event listeners after connection (in case canvas wasn't ready before)
            this.setupCanvasEventListeners();
            
        } catch (error) {
            console.error('Connection error:', error);
            this.showError(`Connection failed: ${error.message}`);
            this.updateConnectionStatus('error');
        }
    }
    
    connectWebSocket(type, url) {
        return new Promise((resolve, reject) => {
            const ws = new WebSocket(url);
            let resolved = false;
            
            ws.onopen = () => {
                this.websockets[type] = ws;
                if (!resolved) {
                    resolved = true;
                    resolve();
                }
            };
            
            ws.onmessage = (event) => {
                this.handleWebSocketMessage(type, event.data);
            };
            
            ws.onclose = () => {
                delete this.websockets[type];
                
                if (this.isConnected) {
                    // Try to reconnect after a delay
                    setTimeout(() => {
                        if (this.isConnected) {
                            this.connectWebSocket(type, url).catch(console.error);
                        }
                    }, 3000);
                }
            };
            
            ws.onerror = (error) => {
                console.error(`${type} WebSocket error:`, error);
                if (!resolved) {
                    resolved = true;
                    reject(new Error(`${type} WebSocket connection failed`));
                }
            };
            
            this.websockets[type] = ws;
            
            // Timeout after 10 seconds
            setTimeout(() => {
                if (!resolved) {
                    resolved = true;
                    reject(new Error(`${type} WebSocket connection timeout`));
                }
            }, 10000);
        });
    }
    
    disconnect() {
        this.isConnected = false;
        
        Object.entries(this.websockets).forEach(([type, ws]) => {
            if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                ws.close();
            }
        });
        
        this.websockets = {};
    }
    
    handleWebSocketMessage(type, data) {
        try {
            const message = JSON.parse(data);
            
            if (type === 'video' && message.type === 'video_frame') {
                this.handleVideoFrame(message);
            }
        } catch (error) {
            console.error(`Error handling ${type} message:`, error);
        }
    }
    
    handleVideoFrame(frameData) {
        if (!this.canvas || !this.ctx) {
            return;
        }
        
        try {
            // Update FPS counter
            this.updateFpsCounter();
            
            // Update logical device point dimensions if present
            if (frameData.point_width && frameData.point_height &&
                !isNaN(frameData.point_width) && !isNaN(frameData.point_height) &&
                frameData.point_width > 0 && frameData.point_height > 0) {
                this.deviceDimensions = {
                    width: parseInt(frameData.point_width, 10),
                    height: parseInt(frameData.point_height, 10)
                };
                // console.log(`Updated device point dimensions: ${this.deviceDimensions.width}x${this.deviceDimensions.height}`);
            }
            
            // Create image from base64 data
            const img = new Image();
            img.onload = () => {
                // Update stream pixel dimensions
                if (img.width && img.height && (img.width !== this.streamDimensions.width || img.height !== this.streamDimensions.height)) {
                    this.streamDimensions = { width: img.width, height: img.height };
                    // Ask main to resize window to stream size, and set CSS to applied content size
                    window.electronAPI.resizeWindow(img.width, img.height)
                        .then((res) => {
                            if (res && !res.error) {
                                this.applyScaledCssSize(res.contentWidth, res.contentHeight);
                                this.updateOrientationClass();
                            }
                        })
                        .catch(err => console.error('resizeWindow error:', err));
                }
                
                // Resize backing canvas buffer if needed (kept at raw px for fidelity)
                if (this.canvas.width !== img.width || this.canvas.height !== img.height) {
                    this.resizeCanvas(img.width, img.height);
                }
                
                // Draw the frame
                this.ctx.drawImage(img, 0, 0);
                
                // Update resolution display
                this.updateResolutionDisplay(img.width, img.height);
            };
            
            img.onerror = (error) => {
                console.error('Image load error:', error);
            };
            
            img.src = `data:image/jpeg;base64,${frameData.data}`;
            
        } catch (error) {
            console.error('Error handling video frame:', error);
        }
    }
    
    applyScaledCssSize(contentWidth, contentHeight) {
        if (!contentWidth || !contentHeight) return;
        // Canvas CSS size
        this.canvas.style.width = `${contentWidth}px`;
        this.canvas.style.height = `${contentHeight}px`;
        // Ensure device screen wrapper and overlay match exactly
        if (this.deviceScreen) {
            this.deviceScreen.style.width = `${contentWidth}px`;
            this.deviceScreen.style.height = `${contentHeight}px`;
        }
        if (this.touchOverlay) {
            this.touchOverlay.style.width = `${contentWidth}px`;
            this.touchOverlay.style.height = `${contentHeight}px`;
        }
    }
    
    updateOrientationClass() {
        const isLandscape = this.streamDimensions.width > this.streamDimensions.height;
        document.body.classList.toggle('landscape', isLandscape);
    }
    
    resizeCanvas(width, height) {
        if (!width || !height || isNaN(width) || isNaN(height) || width <= 0 || height <= 0) {
            console.error(`Invalid canvas dimensions: ${width}x${height}`);
            return;
        }
        
        // Backing store size in pixels
        this.canvas.width = width;
        this.canvas.height = height;
        this.canvasDimensions = { width, height };
        
        // CSS size is managed based on main process applied scale in handleVideoFrame/init
        
        // Re-setup event listeners after resize
        this.setupCanvasEventListeners();
    }
    
    handleTouchStart(e) {
        e.preventDefault();
        
        const rect = this.canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;
        
        this.isDragging = false;
        this.dragStart = { x: clickX, y: clickY };
        this.canvas.style.cursor = 'grabbing';
    }
    
    handleTouchMove(e) {
        e.preventDefault();
        
        if (!this.dragStart) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;
        
        const deltaX = currentX - this.dragStart.x;
        const deltaY = currentY - this.dragStart.y;
        const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        
        // If moved more than 5 pixels, consider it a drag
        if (distance > 5) {
            this.isDragging = true;
        }
    }
    
    handleTouchEnd(e) {
        e.preventDefault();
        
        if (!this.dragStart) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const endX = e.clientX - rect.left;
        const endY = e.clientY - rect.top;
        
        this.canvas.style.cursor = 'crosshair';
        
        if (this.isDragging) {
            // Handle swipe/drag
            this.handleSwipe(this.dragStart.x, this.dragStart.y, endX, endY);
        } else {
            // Handle tap
            this.handleTap(this.dragStart.x, this.dragStart.y);
        }
        
        this.dragStart = null;
        this.isDragging = false;
    }
    
    convertDisplayToDeviceCoords(displayX, displayY) {
        if (!this.canvas || this.deviceDimensions.width === 0 || this.deviceDimensions.height === 0) {
            return null;
        }
        
        // Get the actual displayed size of the canvas (CSS size)
        const displayWidth = this.canvas.clientWidth || this.canvas.offsetWidth || this.streamDimensions.width;
        const displayHeight = this.canvas.clientHeight || this.canvas.offsetHeight || this.streamDimensions.height;
        
        // Convert to device coordinates based on logical point dimensions from video frame
        const deviceX = Math.round((displayX / displayWidth) * this.deviceDimensions.width);
        const deviceY = Math.round((displayY / displayHeight) * this.deviceDimensions.height);
        
        return { x: deviceX, y: deviceY };
    }
    
    handleTap(displayX, displayY) {
        // Convert display coordinates to device coordinates
        const deviceCoords = this.convertDisplayToDeviceCoords(displayX, displayY);
        if (!deviceCoords) {
            return;
        }
        
        // Send tap command via control WebSocket
        this.sendDeviceAction('tap', { x: deviceCoords.x, y: deviceCoords.y });
        
        // Show visual feedback
        this.showTouchFeedback(displayX, displayY);
    }
    
    handleSwipe(startX, startY, endX, endY) {
        // Convert coordinates
        const startCoords = this.convertDisplayToDeviceCoords(startX, startY);
        const endCoords = this.convertDisplayToDeviceCoords(endX, endY);
        
        if (!startCoords || !endCoords) return;
        
        // Send swipe command
        this.sendDeviceAction('swipe', { 
            startX: startCoords.x, 
            startY: startCoords.y, 
            endX: endCoords.x, 
            endY: endCoords.y 
        });
    }
    
    handleKeyDown(e) {
        // Key handling implementation
    }
    
    sendDeviceAction(type, data) {
        const controlWs = this.websockets.control;
        if (!controlWs || controlWs.readyState !== WebSocket.OPEN) {
            return;
        }
        
        let message;
        
        switch (type) {
            case 'tap':
                message = { t: 'tap', x: data.x, y: data.y };
                break;
            case 'swipe':
                message = { 
                    t: 'swipe', 
                    startX: data.startX, 
                    startY: data.startY, 
                    endX: data.endX, 
                    endY: data.endY 
                };
                break;
            case 'text':
                message = { t: 'text', text: data.text };
                break;
            case 'button':
                message = { t: 'button', button: data.button };
                break;
            default:
                message = { t: type, ...data };
        }
        
        controlWs.send(JSON.stringify(message));
    }
    
    handleDeviceAction(action) {
        switch (action) {
            case 'home':
                this.sendDeviceAction('button', { button: 'home' });
                break;
            case 'screenshot':
                this.takeScreenshot();
                break;
            case 'info':
                this.showDeviceInfo();
                break;
            case 'lock':
                this.sendDeviceAction('button', { button: 'lock' });
                break;
        }
    }
    
    setQuality(quality) {
        this.currentQuality = quality;
        this.updateQualityDisplay();
    }
    
    updateQualityDisplay() {
        const items = document.querySelectorAll('#quality-menu .dropdown-item');
        items.forEach(item => {
            item.classList.toggle('active', item.dataset.quality === this.currentQuality);
        });
    }
    
    async takeScreenshot() {
        const canvas = this.canvas;
        if (canvas) {
            canvas.style.filter = 'brightness(1.2)';
            setTimeout(() => {
                canvas.style.filter = '';
            }, 200);
        }
    }
    
    async showDeviceInfo() {
        const modal = document.getElementById('info-modal');
        const modalBody = document.getElementById('info-modal-body');
        
        if (!modal || !modalBody) return;
        
        // Get session info and device dimensions
        const sessionInfo = this.config?.sessionInfo || {};
        const deviceType = sessionInfo.device_type || 'Unknown Device';
        const iosVersion = sessionInfo.ios_version || 'Unknown';
        const sessionId = this.config?.sessionId || 'Unknown';
        const serverUrl = this.config?.serverUrl || 'Unknown';
        
        // Create device info table
        modalBody.innerHTML = `
            <table class="info-table">
                <tr>
                    <th>Device Type</th>
                    <td>${deviceType}</td>
                </tr>
                <tr>
                    <th>iOS Version</th>
                    <td>${iosVersion}</td>
                </tr>
                <tr>
                    <th>Session ID</th>
                    <td>${sessionId}</td>
                </tr>
                <tr>
                    <th>Server URL</th>
                    <td>${serverUrl}</td>
                </tr>
                <tr>
                    <th>Device Point Dimensions</th>
                    <td>${this.deviceDimensions.width} × ${this.deviceDimensions.height}</td>
                </tr>
                <tr>
                    <th>Stream Pixel Dimensions</th>
                    <td>${this.streamDimensions.width} × ${this.streamDimensions.height}</td>
                </tr>
                <tr>
                    <th>Canvas Backing Dimensions</th>
                    <td>${this.canvasDimensions.width} × ${this.canvasDimensions.height}</td>
                </tr>
                <tr>
                    <th>Connection Status</th>
                    <td>${this.isConnected ? 'Connected' : 'Disconnected'}</td>
                </tr>
                <tr>
                    <th>Quality Setting</th>
                    <td>${this.currentQuality}</td>
                </tr>
            </table>
        `;
        
        // Show modal
        modal.classList.add('show');
    }
    
    closeModal() {
        const modal = document.getElementById('info-modal');
        modal?.classList.remove('show');
    }
    
    updateFpsCounter() {
        this.fpsCounter++;
        const now = Date.now();
        
        if (now - this.lastFpsUpdate >= 1000) {
            const fpsElement = document.getElementById('fps-counter');
            if (fpsElement) {
                fpsElement.textContent = `FPS: ${this.fpsCounter}`;
            }
            
            this.fpsCounter = 0;
            this.lastFpsUpdate = now;
        }
    }
    
    updateResolutionDisplay(width, height) {
        const resElement = document.getElementById('resolution');
        if (resElement) {
            resElement.textContent = `Resolution: ${width}x${height}`;
        }
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.className = `status-${status}`;
        }
    }
    
    showLoading() {
        document.getElementById('loading')?.style.setProperty('display', 'block');
        document.getElementById('device-container')?.style.setProperty('display', 'none');
        document.getElementById('error-container')?.style.setProperty('display', 'none');
    }
    
    showDeviceContainer() {
        document.getElementById('loading')?.style.setProperty('display', 'none');
        document.getElementById('device-container')?.style.setProperty('display', 'flex');
        document.getElementById('error-container')?.style.setProperty('display', 'none');
    }
    
    showError(message) {
        const errorMessage = document.getElementById('error-message');
        if (errorMessage) {
            errorMessage.textContent = message;
        }
        
        document.getElementById('loading')?.style.setProperty('display', 'none');
        document.getElementById('device-container')?.style.setProperty('display', 'none');
        document.getElementById('error-container')?.style.setProperty('display', 'flex');
    }
    
    showTouchFeedback(x, y) {
        // Get canvas position relative to the viewport
        const canvasRect = this.canvas.getBoundingClientRect();
        
        const feedback = document.createElement('div');
        feedback.className = 'touch-point';
        feedback.style.position = 'fixed';
        feedback.style.left = (canvasRect.left + x) + 'px';
        feedback.style.top = (canvasRect.top + y) + 'px';
        feedback.style.width = '20px';
        feedback.style.height = '20px';
        feedback.style.borderRadius = '50%';
        feedback.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
        feedback.style.border = '2px solid #007AFF';
        feedback.style.pointerEvents = 'none';
        feedback.style.zIndex = '9999';
        feedback.style.transform = 'translate(-50%, -50%)';
        feedback.style.animation = 'touchFeedback 0.3s ease-out';
        
        // Add CSS animation if not already present
        if (!document.getElementById('touch-feedback-styles')) {
            const style = document.createElement('style');
            style.id = 'touch-feedback-styles';
            style.textContent = `
                @keyframes touchFeedback {
                    0% { transform: translate(-50%, -50%) scale(0.5); opacity: 0; }
                    50% { transform: translate(-50%, -50%) scale(1.2); opacity: 1; }
                    100% { transform: translate(-50%, -50%) scale(1); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(feedback);
        
        setTimeout(() => {
            feedback.remove();
        }, 300);
    }
}

// Initialize the renderer
new IOSBridgeRenderer();