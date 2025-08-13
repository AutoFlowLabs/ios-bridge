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
        this.deviceDimensions = { width: 390, height: 844 };
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
            console.log('Config loaded:', this.config);
            
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
        
        // Initialize canvas
        this.canvas = document.getElementById('video-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // Set current quality
        this.currentQuality = this.config?.quality || 'high';
        this.updateQualityDisplay();
        
        // Show loading state
        this.showLoading();
    }
    
    setupEventListeners() {
        // Window controls
        document.getElementById('close-btn')?.addEventListener('click', () => {
            window.electronAPI.quitApp();
        });
        
        document.getElementById('minimize-btn')?.addEventListener('click', () => {
            window.electronAPI.minimizeWindow();
        });
        
        // Device controls
        document.getElementById('home-btn')?.addEventListener('click', () => {
            this.sendDeviceAction('button', { button: 'home' });
        });
        
        document.getElementById('screenshot-btn')?.addEventListener('click', () => {
            this.takeScreenshot();
        });
        
        document.getElementById('info-btn')?.addEventListener('click', () => {
            this.showDeviceInfo();
        });
        
        // Quality dropdown
        const qualityBtn = document.getElementById('quality-btn');
        const qualityMenu = document.getElementById('quality-menu');
        
        qualityBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            qualityBtn.classList.toggle('active');
        });
        
        qualityMenu?.addEventListener('click', (e) => {
            if (e.target.classList.contains('dropdown-item')) {
                const quality = e.target.dataset.quality;
                this.setQuality(quality);
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            qualityBtn?.classList.remove('active');
        });
        
        // Canvas interaction
        this.setupCanvasInteraction();
        
        // Keyboard input
        this.setupKeyboardInput();
        
        // Device action listener
        window.electronAPI.onDeviceAction((action) => {
            this.handleDeviceAction(action);
        });
        
        // Modal controls
        this.setupModalControls();
        
        // Retry button
        document.getElementById('retry-btn')?.addEventListener('click', () => {
            this.connect();
        });
    }
    
    setupCanvasInteraction() {
        const touchOverlay = document.getElementById('touch-overlay');
        if (!touchOverlay) return;
        
        let isMouseDown = false;
        let lastMousePos = null;
        
        const getRelativePosition = (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const scaleX = this.deviceDimensions.width / rect.width;
            const scaleY = this.deviceDimensions.height / rect.height;
            
            return {
                x: Math.round((e.clientX - rect.left) * scaleX),
                y: Math.round((e.clientY - rect.top) * scaleY)
            };
        };
        
        // Mouse events
        touchOverlay.addEventListener('mousedown', (e) => {
            if (!this.isConnected) return;
            
            isMouseDown = true;
            const pos = getRelativePosition(e);
            lastMousePos = pos;
            
            // Send tap
            this.sendDeviceAction('tap', pos);
            this.showTouchFeedback(e.clientX, e.clientY);
            
            e.preventDefault();
        });
        
        touchOverlay.addEventListener('mousemove', (e) => {
            if (!this.isConnected || !isMouseDown || !lastMousePos) return;
            
            const pos = getRelativePosition(e);
            
            // Calculate distance to determine if it's a swipe
            const dx = pos.x - lastMousePos.x;
            const dy = pos.y - lastMousePos.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance > 10) {
                // Send swipe
                this.sendDeviceAction('swipe', {
                    start_x: lastMousePos.x,
                    start_y: lastMousePos.y,
                    end_x: pos.x,
                    end_y: pos.y,
                    duration: 0.3
                });
                
                lastMousePos = pos;
            }
            
            e.preventDefault();
        });
        
        touchOverlay.addEventListener('mouseup', () => {
            isMouseDown = false;
            lastMousePos = null;
        });
        
        touchOverlay.addEventListener('mouseleave', () => {
            isMouseDown = false;
            lastMousePos = null;
        });
        
        // Prevent context menu
        touchOverlay.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });
    }
    
    setupKeyboardInput() {
        document.addEventListener('keydown', (e) => {
            if (!this.isConnected) return;
            
            // Handle special keys
            switch (e.key) {
                case 'F1':
                    e.preventDefault();
                    this.sendDeviceAction('button', { button: 'home' });
                    break;
                case 'F2':
                    e.preventDefault();
                    this.takeScreenshot();
                    break;
                case 'F3':
                    e.preventDefault();
                    this.showDeviceInfo();
                    break;
                case 'F11':
                    e.preventDefault();
                    window.electronAPI.toggleFullscreen();
                    break;
                case 'Escape':
                    // Close modals
                    this.closeModal();
                    break;
                default:
                    // Send text input for regular characters
                    if (e.key.length === 1 || e.key === 'Backspace' || e.key === 'Enter') {
                        e.preventDefault();
                        this.sendTextInput(e.key);
                    }
                    break;
            }
        });
    }
    
    setupModalControls() {
        const modal = document.getElementById('info-modal');
        const closeBtn = modal?.querySelector('.modal-close');
        
        closeBtn?.addEventListener('click', () => {
            this.closeModal();
        });
        
        modal?.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal();
            }
        });
    }
    
    async connect() {
        try {
            this.showLoading();
            this.updateConnectionStatus('connecting');
            
            // Close existing connections
            this.disconnect();
            
            const sessionId = this.config?.sessionId;
            const serverUrl = this.config?.serverUrl;
            
            if (!sessionId || !serverUrl) {
                throw new Error('Missing session ID or server URL');
            }
            
            // Create WebSocket URLs
            const wsBase = serverUrl.replace('http://', 'ws://').replace('https://', 'wss://');
            const wsUrls = {\n                video: `${wsBase}/ws/${sessionId}/video`,\n                control: `${wsBase}/ws/${sessionId}/control`\n            };\n            \n            // Connect to video WebSocket\n            await this.connectWebSocket('video', wsUrls.video);\n            \n            // Connect to control WebSocket\n            await this.connectWebSocket('control', wsUrls.control);\n            \n            this.isConnected = true;\n            this.updateConnectionStatus('connected');\n            this.showDeviceContainer();\n            \n        } catch (error) {\n            console.error('Connection error:', error);\n            this.showError(`Connection failed: ${error.message}`);\n            this.updateConnectionStatus('error');\n        }\n    }\n    \n    connectWebSocket(type, url) {\n        return new Promise((resolve, reject) => {\n            const ws = new WebSocket(url);\n            let resolved = false;\n            \n            ws.onopen = () => {\n                console.log(`${type} WebSocket connected`);\n                if (!resolved) {\n                    resolved = true;\n                    resolve();\n                }\n            };\n            \n            ws.onmessage = (event) => {\n                this.handleWebSocketMessage(type, event.data);\n            };\n            \n            ws.onclose = () => {\n                console.log(`${type} WebSocket closed`);\n                delete this.websockets[type];\n                \n                if (this.isConnected) {\n                    // Try to reconnect after a delay\n                    setTimeout(() => {\n                        if (this.isConnected) {\n                            this.connectWebSocket(type, url).catch(console.error);\n                        }\n                    }, 3000);\n                }\n            };\n            \n            ws.onerror = (error) => {\n                console.error(`${type} WebSocket error:`, error);\n                if (!resolved) {\n                    resolved = true;\n                    reject(new Error(`${type} WebSocket connection failed`));\n                }\n            };\n            \n            this.websockets[type] = ws;\n            \n            // Timeout after 10 seconds\n            setTimeout(() => {\n                if (!resolved) {\n                    resolved = true;\n                    reject(new Error(`${type} WebSocket connection timeout`));\n                }\n            }, 10000);\n        });\n    }\n    \n    disconnect() {\n        this.isConnected = false;\n        \n        Object.values(this.websockets).forEach(ws => {\n            if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {\n                ws.close();\n            }\n        });\n        \n        this.websockets = {};\n    }\n    \n    handleWebSocketMessage(type, data) {\n        try {\n            const message = JSON.parse(data);\n            \n            switch (type) {\n                case 'video':\n                    this.handleVideoFrame(message);\n                    break;\n                case 'control':\n                    // Handle control responses if needed\n                    break;\n            }\n        } catch (error) {\n            console.error(`Error handling ${type} message:`, error);\n        }\n    }\n    \n    handleVideoFrame(frameData) {\n        if (!this.canvas || !this.ctx) return;\n        \n        try {\n            // Update FPS counter\n            this.updateFpsCounter();\n            \n            // Update device dimensions\n            if (frameData.point_width && frameData.point_height) {\n                this.deviceDimensions = {\n                    width: frameData.point_width,\n                    height: frameData.point_height\n                };\n            }\n            \n            // Create image from base64 data\n            const img = new Image();\n            img.onload = () => {\n                // Resize canvas if needed\n                if (this.canvas.width !== img.width || this.canvas.height !== img.height) {\n                    this.resizeCanvas(img.width, img.height);\n                }\n                \n                // Draw the frame\n                this.ctx.drawImage(img, 0, 0);\n                \n                // Update resolution display\n                this.updateResolutionDisplay(img.width, img.height);\n            };\n            \n            img.src = `data:image/jpeg;base64,${frameData.data}`;\n            \n        } catch (error) {\n            console.error('Error handling video frame:', error);\n        }\n    }\n    \n    resizeCanvas(width, height) {\n        this.canvas.width = width;\n        this.canvas.height = height;\n        this.canvasDimensions = { width, height };\n        \n        // Ensure canvas fits in container\n        const container = document.querySelector('.device-frame');\n        if (container) {\n            const containerRect = container.getBoundingClientRect();\n            const maxWidth = containerRect.width - 40;\n            const maxHeight = containerRect.height - 40;\n            \n            const scaleX = maxWidth / width;\n            const scaleY = maxHeight / height;\n            const scale = Math.min(scaleX, scaleY, 1);\n            \n            this.canvas.style.width = `${width * scale}px`;\n            this.canvas.style.height = `${height * scale}px`;\n        }\n    }\n    \n    sendDeviceAction(type, data) {\n        const controlWs = this.websockets.control;\n        if (!controlWs || controlWs.readyState !== WebSocket.OPEN) {\n            console.warn('Control WebSocket not available');\n            return;\n        }\n        \n        const message = {\n            t: type,\n            ...data\n        };\n        \n        controlWs.send(JSON.stringify(message));\n    }\n    \n    sendTextInput(text) {\n        this.sendDeviceAction('text', { text });\n    }\n    \n    handleDeviceAction(action) {\n        switch (action) {\n            case 'home':\n                this.sendDeviceAction('button', { button: 'home' });\n                break;\n            case 'screenshot':\n                this.takeScreenshot();\n                break;\n            case 'info':\n                this.showDeviceInfo();\n                break;\n            case 'lock':\n                this.sendDeviceAction('button', { button: 'lock' });\n                break;\n        }\n    }\n    \n    setQuality(quality) {\n        this.currentQuality = quality;\n        this.updateQualityDisplay();\n        \n        // TODO: Send quality change to server\n        console.log(`Quality set to: ${quality}`);\n    }\n    \n    updateQualityDisplay() {\n        const items = document.querySelectorAll('#quality-menu .dropdown-item');\n        items.forEach(item => {\n            item.classList.toggle('active', item.dataset.quality === this.currentQuality);\n        });\n    }\n    \n    async takeScreenshot() {\n        try {\n            // For now, just show a notification\n            // TODO: Implement screenshot API call\n            console.log('Taking screenshot...');\n            \n            // Visual feedback\n            const canvas = this.canvas;\n            if (canvas) {\n                canvas.style.filter = 'brightness(1.2)';\n                setTimeout(() => {\n                    canvas.style.filter = '';\n                }, 200);\n            }\n        } catch (error) {\n            console.error('Screenshot error:', error);\n        }\n    }\n    \n    async showDeviceInfo() {\n        try {\n            const modal = document.getElementById('info-modal');\n            const body = document.getElementById('info-modal-body');\n            \n            if (!modal || !body) return;\n            \n            // Create device info table\n            const sessionInfo = this.config?.sessionInfo || {};\n            const info = [\n                ['Device Type', sessionInfo.device_type || 'Unknown'],\n                ['iOS Version', sessionInfo.ios_version || 'Unknown'],\n                ['Session ID', this.config?.sessionId || 'Unknown'],\n                ['Resolution', `${this.deviceDimensions.width}x${this.deviceDimensions.height}`],\n                ['Canvas Size', `${this.canvasDimensions.width}x${this.canvasDimensions.height}`],\n                ['Quality', this.currentQuality],\n                ['Status', this.isConnected ? 'Connected' : 'Disconnected']\n            ];\n            \n            const table = document.createElement('table');\n            table.className = 'info-table';\n            \n            info.forEach(([key, value]) => {\n                const row = table.insertRow();\n                const keyCell = row.insertCell();\n                const valueCell = row.insertCell();\n                \n                keyCell.textContent = key;\n                valueCell.textContent = value;\n            });\n            \n            body.innerHTML = '';\n            body.appendChild(table);\n            \n            modal.classList.add('show');\n            \n        } catch (error) {\n            console.error('Device info error:', error);\n        }\n    }\n    \n    closeModal() {\n        const modal = document.getElementById('info-modal');\n        modal?.classList.remove('show');\n    }\n    \n    showTouchFeedback(x, y) {\n        const feedback = document.createElement('div');\n        feedback.className = 'touch-point';\n        feedback.style.left = x + 'px';\n        feedback.style.top = y + 'px';\n        \n        document.body.appendChild(feedback);\n        \n        setTimeout(() => {\n            feedback.remove();\n        }, 300);\n    }\n    \n    updateFpsCounter() {\n        this.fpsCounter++;\n        const now = Date.now();\n        \n        if (now - this.lastFpsUpdate >= 1000) {\n            const fpsElement = document.getElementById('fps-counter');\n            if (fpsElement) {\n                fpsElement.textContent = `FPS: ${this.fpsCounter}`;\n            }\n            \n            this.fpsCounter = 0;\n            this.lastFpsUpdate = now;\n        }\n    }\n    \n    updateResolutionDisplay(width, height) {\n        const resElement = document.getElementById('resolution');\n        if (resElement) {\n            resElement.textContent = `Resolution: ${width}x${height}`;\n        }\n    }\n    \n    updateConnectionStatus(status) {\n        const statusElement = document.getElementById('connection-status');\n        if (statusElement) {\n            statusElement.className = `status-${status}`;\n        }\n    }\n    \n    showLoading() {\n        document.getElementById('loading')?.style.setProperty('display', 'block');\n        document.getElementById('device-container')?.style.setProperty('display', 'none');\n        document.getElementById('error-container')?.style.setProperty('display', 'none');\n    }\n    \n    showDeviceContainer() {\n        document.getElementById('loading')?.style.setProperty('display', 'none');\n        document.getElementById('device-container')?.style.setProperty('display', 'flex');\n        document.getElementById('error-container')?.style.setProperty('display', 'none');\n    }\n    \n    showError(message) {\n        const errorMessage = document.getElementById('error-message');\n        if (errorMessage) {\n            errorMessage.textContent = message;\n        }\n        \n        document.getElementById('loading')?.style.setProperty('display', 'none');\n        document.getElementById('device-container')?.style.setProperty('display', 'none');\n        document.getElementById('error-container')?.style.setProperty('display', 'flex');\n    }\n}\n\n// Initialize the renderer\nnew IOSBridgeRenderer();