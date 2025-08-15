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
        this.keyboardMode = false;
        this.realtimeMode = false;
        this.isRecording = false;
        
        // WebRTC properties
        this.streamMode = 'websocket'; // 'websocket' or 'webrtc'
        this.peerConnection = null;
        this.webrtcVideo = null;
        
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
            
            // Construct serverUrl from serverHost and serverPort if not present
            if (!this.config.serverUrl && this.config.serverHost && this.config.serverPort) {
                this.config.serverUrl = `http://${this.config.serverHost}:${this.config.serverPort}`;
            }
            
            // Initialize UI
            this.initializeUI();
            
            // Set up event listeners
            this.setupEventListeners();
        
        // Initialize WebRTC video element
        this.webrtcVideo = document.getElementById('webrtc-video');
            
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
        
        // Window control buttons
        document.getElementById('minimize-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.minimizeWindow();
        });
        
        document.getElementById('close-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.closeWindow();
        });
        
        // Quality/Settings dropdown toggle
        document.getElementById('quality-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleQualityMenu();
        });
        
        // Swipe dropdown toggle and menu items
        document.getElementById('swipe-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleSwipeMenu();
        });
        
        document.querySelectorAll('#swipe-menu .dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const swipeDirection = e.currentTarget?.dataset?.swipe;
                this.performSwipeGesture(swipeDirection);
            });
        });
        
        // Keyboard input section controls
        document.getElementById('send-text-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.sendKeyboardText();
        });
        
        document.getElementById('clear-text-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.clearKeyboardText();
        });
        
        document.getElementById('keyboard-input')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendKeyboardText();
            }
        });
        
        // Real-time mode toggle
        document.getElementById('realtime-mode-toggle')?.addEventListener('change', (e) => {
            this.toggleRealtimeMode(e.target.checked);
        });
        
        // Real-time keyboard input capture
        document.getElementById('keyboard-input')?.addEventListener('keydown', (e) => {
            if (this.realtimeMode) {
                this.handleRealtimeKeyPress(e);
            }
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
        
        // Listen for device actions from main process (menu shortcuts)
        window.electronAPI?.onDeviceAction((action) => {
            this.handleDeviceAction(action);
        });
        
        // Close menus when clicking outside
        document.addEventListener('click', (e) => {
            const qualityBtn = document.getElementById('quality-btn');
            const qualityMenu = document.getElementById('quality-menu');
            const swipeBtn = document.getElementById('swipe-btn');
            const swipeMenu = document.getElementById('swipe-menu');
            
            if (qualityBtn && qualityMenu && 
                !qualityBtn.contains(e.target) && 
                !qualityMenu.contains(e.target)) {
                qualityMenu.classList.remove('show');
            }
            
            if (swipeBtn && swipeMenu && 
                !swipeBtn.contains(e.target) && 
                !swipeMenu.contains(e.target)) {
                swipeMenu.classList.remove('show');
            }
        });
    }
    
    setupCanvasEventListeners() {
        // Use touch overlay for events since it's on top of the canvas
        const eventTarget = this.touchOverlay || this.canvas;
        
        if (eventTarget) {
            // Remove existing listeners first to avoid duplicates
            eventTarget.removeEventListener('mousedown', this.handleTouchStart);
            eventTarget.removeEventListener('mousemove', this.handleTouchMove);
            eventTarget.removeEventListener('mouseup', this.handleTouchEnd);
            
            // Add new listeners (used for WebSocket/canvas mode)
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
                webrtc: `${wsBase}/ws/${sessionId}/webrtc`,
                control: `${wsBase}/ws/${sessionId}/control`
            };
            
            // Connect based on stream mode
            console.log(`🎯 Current stream mode: ${this.streamMode}`);
            
            if (this.streamMode === 'webrtc') {
                console.log('🚀 Setting up WebRTC mode...');
                // Show WebRTC video, hide canvas, and ensure overlay doesn't intercept events
                this.canvas.style.display = 'none';
                this.webrtcVideo.style.display = 'block';
                if (this.touchOverlay) this.touchOverlay.style.pointerEvents = 'none';
                console.log('👀 Canvas hidden, WebRTC video shown, overlay disabled for pointer events');
                await this.connectWebRTC(wsUrls.webrtc);
            } else {
                console.log('📡 Setting up WebSocket mode...');
                // Show canvas, hide WebRTC video, and enable overlay events
                this.canvas.style.display = 'block';
                this.webrtcVideo.style.display = 'none';
                if (this.touchOverlay) this.touchOverlay.style.pointerEvents = 'auto';
                console.log('👀 WebRTC video hidden, canvas shown, overlay enabled for pointer events');
                // Connect to video WebSocket
                await this.connectWebSocket('video', wsUrls.video);
            }
            
            // Connect to control WebSocket
            console.log(`🔗 Connecting to control WebSocket: ${wsUrls.control}`);
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
                console.log(`✅ ${type} WebSocket connected successfully`);
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
                console.log(`🔌 ${type} WebSocket closed`);
                delete this.websockets[type];
                
                if (this.isConnected) {
                    console.log(`🔄 Attempting to reconnect ${type} WebSocket in 3 seconds...`);
                    // Try to reconnect after a delay
                    setTimeout(() => {
                        if (this.isConnected) {
                            this.connectWebSocket(type, url).catch(console.error);
                        }
                    }, 3000);
                }
            };
            
            ws.onerror = (error) => {
                console.error(`❌ ${type} WebSocket error:`, error);
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
        
        // Close WebRTC connection
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
    }
    
    setupWebRTCEventListeners() {
        if (!this.webrtcVideo) return;
        
        // Remove existing listeners first to avoid duplicates
        this.webrtcVideo.removeEventListener('mousedown', this.handleWebRTCTouchStart);
        this.webrtcVideo.removeEventListener('mousemove', this.handleWebRTCTouchMove);
        this.webrtcVideo.removeEventListener('mouseup', this.handleWebRTCTouchEnd);
        // Also remove potential previous resize listener
        this.webrtcVideo.removeEventListener('resize', this.handleWebRTCVideoResize);
        
        // Add new listeners
        this.webrtcVideo.addEventListener('mousedown', this.handleWebRTCTouchStart.bind(this));
        this.webrtcVideo.addEventListener('mousemove', this.handleWebRTCTouchMove.bind(this));
        this.webrtcVideo.addEventListener('mouseup', this.handleWebRTCTouchEnd.bind(this));
        
        // Listen for intrinsic video size changes (e.g., rotation)
        this.handleWebRTCVideoResize = async () => {
            try {
                console.log(`🎞️ WebRTC video resized: intrinsic ${this.webrtcVideo.videoWidth}x${this.webrtcVideo.videoHeight}`);
                await this.updateWebRTCVideoLayoutFromElement();
            } catch (e) {
                console.warn('Error handling WebRTC video resize:', e);
            }
        };
        this.webrtcVideo.addEventListener('resize', this.handleWebRTCVideoResize);
        
        this.webrtcVideo.style.cursor = 'crosshair';
    }
    
    async updateWebRTCVideoLayoutFromElement() {
        if (!this.webrtcVideo) return;
        // Update stream dimensions from actual video element
        this.streamDimensions = {
            width: this.webrtcVideo.videoWidth || this.streamDimensions.width,
            height: this.webrtcVideo.videoHeight || this.streamDimensions.height
        };
        console.log(`📺 Updating layout for WebRTC video. Stream: ${this.streamDimensions.width}x${this.streamDimensions.height}`);
        // Ask main to resize window to match stream pixel size; set CSS to scaled content size
        try {
            const res = await window.electronAPI.resizeWindow(this.streamDimensions.width, this.streamDimensions.height);
            if (res && !res.error) {
                this.applyScaledCssSize(res.contentWidth, res.contentHeight);
                this.updateOrientationClass();
                this.updateResolutionDisplay(this.streamDimensions.width, this.streamDimensions.height);
            }
        } catch (err) {
            console.error('resizeWindow error (WebRTC):', err);
        }
        // Refresh logical device dimensions from backend to ensure mapping correctness
        await this.refreshDeviceDimensions();
    }
    
    async connectWebRTC(webrtcUrl) {
        return new Promise((resolve, reject) => {
            console.log('🚀 Initializing WebRTC connection...');
            
            // Create peer connection with multiple ICE servers for better connectivity
            this.peerConnection = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' },
                    { urls: 'stun:stun1.l.google.com:19302' },
                    { urls: 'stun:stun2.l.google.com:19302' },
                    { urls: 'stun:stun.cloudflare.com:3478' },
                    { urls: 'stun:openrelay.metered.ca:80' }
                ],
                iceCandidatePoolSize: 10
            });
            
            // Handle incoming video stream
            this.peerConnection.ontrack = (event) => {
                console.log('✅ WebRTC video track received');
                if (this.webrtcVideo) {
                    this.webrtcVideo.srcObject = event.streams[0];
                    this.webrtcVideo.style.display = 'block';
                    this.canvas.style.display = 'none';
                    
                    // Debug video dimensions when stream starts
                    this.webrtcVideo.addEventListener('loadedmetadata', async () => {
                        console.log(`📺 WebRTC Video Stream Started:`);
                        console.log(`   Video Resolution: ${this.webrtcVideo.videoWidth}x${this.webrtcVideo.videoHeight}`);
                        console.log(`   CSS Display Size: ${this.webrtcVideo.clientWidth}x${this.webrtcVideo.clientHeight}`);
                        console.log(`   Offset Size: ${this.webrtcVideo.offsetWidth}x${this.webrtcVideo.offsetHeight}`);
                        console.log(`   Canvas Display Size: ${this.canvas.clientWidth}x${this.canvas.clientHeight}`);
                        console.log(`   Device Dimensions: ${this.deviceDimensions.width}x${this.deviceDimensions.height}`);

                        await this.updateWebRTCVideoLayoutFromElement();
                    }, { once: true });
                    
                    // Setup video element event listeners (including resize)
                    this.setupWebRTCEventListeners();
                }
            };
            
            // Connection state change handler
            this.peerConnection.onconnectionstatechange = () => {
                console.log(`🔗 WebRTC connection state: ${this.peerConnection.connectionState}`);
                if (this.peerConnection.connectionState === 'connected') {
                    console.log('🎉 WebRTC connection established successfully');
                } else if (this.peerConnection.connectionState === 'failed') {
                    console.error('❌ WebRTC connection failed');
                    reject(new Error('WebRTC connection failed'));
                }
            };

            // ICE connection state change handler
            this.peerConnection.oniceconnectionstatechange = () => {
                console.log(`🧊 ICE connection state: ${this.peerConnection.iceConnectionState}`);
            };

            // ICE gathering state change handler
            this.peerConnection.onicegatheringstatechange = () => {
                console.log(`🔍 ICE gathering state: ${this.peerConnection.iceGatheringState}`);
            };

            // Setup WebRTC signaling WebSocket
            const signalingWs = new WebSocket(webrtcUrl);
            
            // ICE candidate handler - send candidates to server
            this.peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    console.log(`🧊 ICE candidate: ${event.candidate.candidate}`);
                    // Send ICE candidate to server via signaling WebSocket
                    if (signalingWs && signalingWs.readyState === WebSocket.OPEN) {
                        signalingWs.send(JSON.stringify({
                            type: 'ice-candidate',
                            candidate: event.candidate
                        }));
                    }
                } else {
                    console.log('🧊 ICE gathering completed');
                }
            };
            
            signalingWs.onopen = async () => {
                console.log('📡 WebRTC signaling connected');
                
                try {
                    // Start the stream
                    console.log('📡 Sending start-stream request');
                    signalingWs.send(JSON.stringify({
                        type: 'start-stream',
                        quality: this.currentQuality,
                        sessionId: this.config?.sessionInfo?.session_id,
                        fps: 30
                    }));
                    
                    // Create offer
                    console.log('🔧 Creating WebRTC offer');
                    const offer = await this.peerConnection.createOffer({
                        offerToReceiveVideo: true,
                        offerToReceiveAudio: false
                    });
                    
                    await this.peerConnection.setLocalDescription(offer);
                    console.log('✅ Local description set');
                    
                    // Send offer to server
                    console.log('📡 Sending WebRTC offer to server');
                    signalingWs.send(JSON.stringify({
                        type: 'offer',
                        sdp: offer.sdp
                    }));
                    console.log('✅ WebRTC offer sent');
                    
                } catch (error) {
                    console.error('❌ WebRTC offer creation error:', error);
                    reject(error);
                }
            };
            
            signalingWs.onmessage = async (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log(`📡 WebRTC signaling received: ${data.type}`);
                    
                    if (data.type === 'stream-ready') {
                        console.log('🎬 WebRTC stream ready');
                    } else if (data.type === 'answer') {
                        console.log('🤝 Received WebRTC answer, setting remote description');
                        await this.peerConnection.setRemoteDescription(
                            new RTCSessionDescription({
                                type: 'answer',
                                sdp: data.sdp
                            })
                        );
                        console.log('✅ WebRTC remote description set successfully');
                        resolve();
                    } else if (data.type === 'ice-candidate') {
                        if (data.candidate) {
                            console.log(`🧊 Received server ICE candidate: ${data.candidate.candidate}`);
                            await this.peerConnection.addIceCandidate(data.candidate);
                            console.log('✅ Server ICE candidate added successfully');
                        }
                    } else if (data.type === 'error') {
                        console.error('❌ WebRTC signaling error:', data.message);
                        reject(new Error(data.message));
                    } else {
                        console.log(`📡 Unknown WebRTC message type: ${data.type}`, data);
                    }
                } catch (error) {
                    console.error('WebRTC signaling message error:', error);
                }
            };
            
            signalingWs.onerror = (error) => {
                console.error('WebRTC signaling error:', error);
                reject(error);
            };
            
            signalingWs.onclose = () => {
                console.log('📡 WebRTC signaling disconnected');
            };
            
            // Store signaling WebSocket
            this.websockets.webrtc = signalingWs;
            
            // Handle ICE candidates
            this.peerConnection.onicecandidate = (event) => {
                if (event.candidate && signalingWs.readyState === WebSocket.OPEN) {
                    signalingWs.send(JSON.stringify({
                        type: 'ice-candidate',
                        candidate: event.candidate
                    }));
                }
            };
        });
    }
    
    handleWebRTCTouchStart(event) {
        const rect = this.webrtcVideo.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        this.dragStart = { x, y };
        this.isDragging = true;
    }
    
    handleWebRTCTouchMove(event) {
        if (!this.isDragging) return;
        
        event.preventDefault();
    }
    
    handleWebRTCTouchEnd(event) {
        if (!this.isDragging) return;
        
        const rect = this.webrtcVideo.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        if (this.dragStart) {
            const deltaX = Math.abs(x - this.dragStart.x);
            const deltaY = Math.abs(y - this.dragStart.y);
            
            if (deltaX < 5 && deltaY < 5) {
                // This was a tap
                this.handleWebRTCTap(x, y);
            } else {
                // This was a swipe
                this.handleWebRTCSwipe(this.dragStart.x, this.dragStart.y, x, y);
            }
        }
        
        this.dragStart = null;
        this.isDragging = false;
    }
    
    handleWebRTCTap(displayX, displayY) {
        // Convert WebRTC video coordinates to device coordinates
        const deviceCoords = this.convertWebRTCToDeviceCoords(displayX, displayY);
        if (!deviceCoords) {
            return;
        }
        
        // Send tap command via control WebSocket
        this.sendDeviceAction('tap', { x: deviceCoords.x, y: deviceCoords.y });
    }
    
    handleWebRTCSwipe(startX, startY, endX, endY) {
        // Convert WebRTC video coordinates to device coordinates
        const startCoords = this.convertWebRTCToDeviceCoords(startX, startY);
        const endCoords = this.convertWebRTCToDeviceCoords(endX, endY);
        
        if (!startCoords || !endCoords) {
            return;
        }
        
        // Send swipe command via control WebSocket (use camelCase keys expected by sender)
        this.sendDeviceAction('swipe', {
            startX: startCoords.x,
            startY: startCoords.y,
            endX: endCoords.x,
            endY: endCoords.y
        });
    }
    
    convertWebRTCToDeviceCoords(displayX, displayY) {
        if (!this.webrtcVideo || this.deviceDimensions.width === 0 || this.deviceDimensions.height === 0) {
            return null;
        }
        
        // Get element display size
        const elemW = this.webrtcVideo.clientWidth || this.webrtcVideo.offsetWidth;
        const elemH = this.webrtcVideo.clientHeight || this.webrtcVideo.offsetHeight;
        const vidW = this.webrtcVideo.videoWidth || this.streamDimensions.width;
        const vidH = this.webrtcVideo.videoHeight || this.streamDimensions.height;
        
        if (!elemW || !elemH || !vidW || !vidH) return null;
        
        // Account for object-fit: contain letterboxing by computing actual rendered content box
        const scale = Math.min(elemW / vidW, elemH / vidH);
        const contentW = vidW * scale;
        const contentH = vidH * scale;
        const offsetX = (elemW - contentW) / 2;
        const offsetY = (elemH - contentH) / 2;
        
        // Map display coords (relative to element) into content coords
        const inContentX = displayX - offsetX;
        const inContentY = displayY - offsetY;
        
        // Normalize to [0,1]
        const nx = Math.max(0, Math.min(1, inContentX / contentW));
        const ny = Math.max(0, Math.min(1, inContentY / contentH));
        
        // Convert to logical device coordinates
        const deviceX = Math.round(nx * this.deviceDimensions.width);
        const deviceY = Math.round(ny * this.deviceDimensions.height);
        
        // Debug
        console.log(`🎯 WebRTC map -> elem ${elemW}x${elemH}, video ${vidW}x${vidH}, content ${Math.round(contentW)}x${Math.round(contentH)}, offset ${Math.round(offsetX)},${Math.round(offsetY)}, display ${Math.round(displayX)},${Math.round(displayY)} => device ${deviceX},${deviceY} (points ${this.deviceDimensions.width}x${this.deviceDimensions.height})`);
        
        return { x: deviceX, y: deviceY };
    }
    
    async refreshDeviceDimensions() {
        try {
            const sessionId = this.config?.sessionId;
            const serverUrl = this.config?.serverUrl;
            if (!sessionId || !serverUrl) return;
            const resp = await fetch(`${serverUrl}/api/sessions/${sessionId}`);
            if (!resp.ok) return;
            const data = await resp.json();
            const dw = parseInt(data?.device_width, 10);
            const dh = parseInt(data?.device_height, 10);
            if (dw > 0 && dh > 0) {
                this.deviceDimensions = { width: dw, height: dh };
                console.log(`🔧 Refreshed device logical dimensions from server: ${dw}x${dh}`);
            }
        } catch (e) {
            console.warn('Failed to refresh device dimensions:', e);
        }
    }
    
    toggleStreamMode() {
        const oldMode = this.streamMode;
        this.streamMode = this.streamMode === 'websocket' ? 'webrtc' : 'websocket';
        
        console.log(`🔄 Switching stream mode from ${oldMode} to: ${this.streamMode}`);
        
        // Update UI immediately
        const streamModeLabel = document.getElementById('stream-mode-label');
        const streamModeBtn = document.getElementById('stream-mode-btn');
        
        if (streamModeLabel) {
            streamModeLabel.textContent = this.streamMode === 'webrtc' ? 'WebRTC' : 'WebSocket';
            console.log(`✅ Updated UI label to: ${streamModeLabel.textContent}`);
        }
        
        if (streamModeBtn) {
            if (this.streamMode === 'webrtc') {
                streamModeBtn.classList.add('webrtc-mode');
                console.log('🟠 Added webrtc-mode class to button');
            } else {
                streamModeBtn.classList.remove('webrtc-mode');
                console.log('🔵 Removed webrtc-mode class from button');
            }
        }
        
        // Show visual feedback about the mode switch
        if (this.streamMode === 'webrtc') {
            this.showStatus('🚀 Switching to WebRTC mode - Lower latency, real-time streaming', 3000);
        } else {
            this.showStatus('📡 Switching to WebSocket mode - High quality screenshots', 3000);
        }
        
        // Reconnect with new mode
        if (this.isConnected) {
            console.log('🔄 Reconnecting with new stream mode...');
            this.disconnect();
            setTimeout(() => {
                this.connect();
            }, 1000);
        }
    }
    
    showStatus(message, duration = 2000) {
        // Show status message in the UI
        console.log(`📢 Status: ${message}`);
        // You can add visual status display here if needed
    }
    
    handleWebSocketMessage(type, data) {
        try {
            const message = JSON.parse(data);
            
            if (type === 'video' && message.type === 'video_frame') {
                this.handleVideoFrame(message);
            }
            // Handle other message types as needed
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
        
        // Debug: console.log(`Canvas: Display(${displayX}, ${displayY}) -> Device(${deviceX}, ${deviceY})`);
        
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
        // Only handle keyboard shortcuts when not in keyboard input mode or when input is not focused
        const keyboardInput = document.getElementById('keyboard-input');
        const isInputFocused = document.activeElement === keyboardInput;
        
        // If keyboard mode is active and input is focused, let normal typing work
        if (this.keyboardMode && isInputFocused) {
            return;
        }
        
        // Handle global keyboard shortcuts
        switch (e.key) {
            case 'F1':
                e.preventDefault();
                this.handleDeviceAction('home');
                break;
            case 'F2':
                e.preventDefault();
                this.handleDeviceAction('screenshot');
                break;
            case 'F3':
                e.preventDefault();
                this.handleDeviceAction('info');
                break;
            case 'F4':
                e.preventDefault();
                this.handleDeviceAction('keyboard');
                break;
            case 'F5':
                e.preventDefault();
                this.handleDeviceAction('lock');
                break;
            case 'F6':
                e.preventDefault();
                this.handleDeviceAction('record');
                break;
            case 'F7':
                e.preventDefault();
                this.handleDeviceAction('toggle-stream');
                break;
        }
    }
    
    sendDeviceAction(type, data) {
        console.log(`🔍 Attempting to send device action: ${type}`, data);
        console.log(`🔍 Available WebSockets:`, Object.keys(this.websockets));
        
        const controlWs = this.websockets.control;
        console.log(`🔍 Control WebSocket:`, controlWs);
        console.log(`🔍 Control WebSocket ReadyState:`, controlWs?.readyState);
        console.log(`🔍 WebSocket.OPEN constant:`, WebSocket.OPEN);
        
        if (!controlWs || controlWs.readyState !== WebSocket.OPEN) {
            console.error(`❌ Control WebSocket not available. Type: ${type}, ReadyState: ${controlWs?.readyState}`);
            console.error(`❌ WebSocket states: CONNECTING=${WebSocket.CONNECTING}, OPEN=${WebSocket.OPEN}, CLOSING=${WebSocket.CLOSING}, CLOSED=${WebSocket.CLOSED}`);
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
                    start_x: data.startX, 
                    start_y: data.startY, 
                    end_x: data.endX, 
                    end_y: data.endY,
                    duration: data.duration || 0.3
                };
                break;
            case 'text':
                message = { t: 'text', text: data.text };
                break;
            case 'button':
                message = { t: 'button', button: data.button };
                break;
            case 'key':
                message = { t: 'key', key: data.key };
                if (data.duration !== undefined) {
                    message.duration = data.duration;
                }
                break;
            default:
                message = { t: type, ...data };
        }
        
        const messageString = JSON.stringify(message);
        console.log(`✅ Sending WebSocket message:`, message);
        console.log(`✅ Message string:`, messageString);
        
        try {
            controlWs.send(messageString);
            console.log(`✅ WebSocket message sent successfully`);
        } catch (error) {
            console.error(`❌ Error sending WebSocket message:`, error);
        }
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
            case 'keyboard':
                this.toggleKeyboard();
                break;
            case 'lock':
                this.sendDeviceAction('button', { button: 'lock' });
                break;
            case 'record':
                this.startRecording();
                break;
            case 'stop-record':
                this.stopRecording();
                break;
            case 'toggle-stream':
                this.toggleStreamMode();
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
        
        // Get the session ID from config
        const sessionId = this.config?.sessionId;
        const serverUrl = this.config?.serverUrl;
        
        if (!sessionId || !serverUrl) {
            console.error('Missing session ID or server URL for screenshot');
            return;
        }
        
        try {
            // Call the screenshot API endpoint
            const response = await fetch(`${serverUrl}/api/sessions/${sessionId}/screenshot/download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                // Get the filename from Content-Disposition header or create one
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'screenshot.png';
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename=(.+)/);
                    if (filenameMatch) {
                        filename = filenameMatch[1].replace(/"/g, ''); // Remove quotes
                    }
                }
                
                // Get the blob data
                const blob = await response.blob();
                
                // Create a download link and trigger download
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                
                // Clean up
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                console.log(`Screenshot saved as ${filename}`);
            } else {
                console.error('Failed to take screenshot:', response.statusText);
            }
        } catch (error) {
            console.error('Error taking screenshot:', error);
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
    
    // Window control methods
    async minimizeWindow() {
        try {
            await window.electronAPI.minimizeWindow();
        } catch (error) {
            console.error('Error minimizing window:', error);
        }
    }
    
    async closeWindow() {
        try {
            await window.electronAPI.quitApp();
        } catch (error) {
            console.error('Error closing window:', error);
        }
    }
    
    toggleQualityMenu() {
        const qualityMenu = document.getElementById('quality-menu');
        if (qualityMenu) {
            qualityMenu.classList.toggle('show');
        }
    }
    
    // Keyboard functionality methods
    toggleKeyboard() {
        this.keyboardMode = !this.keyboardMode;
        const keyboardSection = document.getElementById('keyboard-section');
        const keyboardBtn = document.getElementById('keyboard-btn');
        const keyboardInput = document.getElementById('keyboard-input');
        
        if (this.keyboardMode) {
            keyboardSection.style.display = 'block';
            keyboardBtn.classList.add('keyboard-active');
            keyboardBtn.title = 'Hide Keyboard (F4)';
            // Focus the input field
            setTimeout(() => {
                keyboardInput?.focus();
            }, 100);
        } else {
            keyboardSection.style.display = 'none';
            keyboardBtn.classList.remove('keyboard-active');
            keyboardBtn.title = 'Toggle Keyboard (F4)';
        }
    }
    
    sendKeyboardText() {
        const keyboardInput = document.getElementById('keyboard-input');
        const text = keyboardInput?.value.trim();
        
        if (!text) return;
        
        console.log(`📝 Sending keyboard text: "${text}"`);
        
        // Send text via control WebSocket
        this.sendDeviceAction('text', { text: text });
        
        // Clear the input
        if (keyboardInput) {
            keyboardInput.value = '';
        }
        
        // Show feedback in footer
        this.showTemporaryMessage(`Text sent: "${text}"`);
    }
    
    clearKeyboardText() {
        const keyboardInput = document.getElementById('keyboard-input');
        if (keyboardInput) {
            keyboardInput.value = '';
            keyboardInput.focus();
        }
    }
    
    showTemporaryMessage(message) {
        const keyboardHint = document.querySelector('.keyboard-hint');
        if (keyboardHint) {
            const originalText = keyboardHint.textContent;
            keyboardHint.textContent = message;
            keyboardHint.style.color = '#007AFF';
            
            setTimeout(() => {
                keyboardHint.textContent = originalText;
                keyboardHint.style.color = '#888';
            }, 2000);
        }
    }
    
    // Real-time keyboard functionality
    toggleRealtimeMode(enabled) {
        this.realtimeMode = enabled;
        const keyboardHint = document.getElementById('keyboard-hint');
        const keyboardInputRow = document.querySelector('.keyboard-input-row');
        const sendBtn = document.getElementById('send-text-btn');
        const keyboardInput = document.getElementById('keyboard-input');
        
        if (enabled) {
            keyboardHint.textContent = '⚡ Real-time mode: Each keystroke is sent immediately to the device';
            keyboardHint.classList.add('realtime-active');
            keyboardInputRow.classList.add('realtime-mode');
            sendBtn.style.display = 'none';
            keyboardInput.placeholder = 'Type directly - each key press goes to device...';
        } else {
            keyboardHint.textContent = '💡 Type directly on your keyboard when this panel is open. Press Enter to send text.';
            keyboardHint.classList.remove('realtime-active');
            keyboardInputRow.classList.remove('realtime-mode');
            sendBtn.style.display = 'block';
            keyboardInput.placeholder = 'Type text to send to device...';
        }
    }
    
    handleRealtimeKeyPress(e) {
        // Prevent the default browser behavior for most keys
        const allowedKeys = ['Tab', 'Escape', 'F1', 'F2', 'F3', 'F4'];
        if (!allowedKeys.includes(e.key)) {
            e.preventDefault();
        }
        
        // Map JavaScript key events to iOS key codes
        const keyCode = this.mapKeyToIOSCode(e.key);
        
        if (keyCode) {
            // Send individual key press to device
            console.log(`Sending key: ${keyCode} for input: ${e.key}`);
            this.sendDeviceAction('key', { key: keyCode });
            
            // Show visual feedback
            this.showRealtimeKeyFeedback(e.key);
        } else {
            console.log(`No mapping found for key: ${e.key}`);
        }
    }
    
    mapKeyToIOSCode(key) {
        // iOS Key codes for idb ui key command
        // These are based on iOS/UIKit key codes and HID usage codes
        const keyMappings = {
            // Letters - using HID usage codes
            'a': '4', 'A': '4',
            'b': '5', 'B': '5', 
            'c': '6', 'C': '6',
            'd': '7', 'D': '7',
            'e': '8', 'E': '8',
            'f': '9', 'F': '9',
            'g': '10', 'G': '10',
            'h': '11', 'H': '11',
            'i': '12', 'I': '12',
            'j': '13', 'J': '13',
            'k': '14', 'K': '14',
            'l': '15', 'L': '15',
            'm': '16', 'M': '16',
            'n': '17', 'N': '17',
            'o': '18', 'O': '18',
            'p': '19', 'P': '19',
            'q': '20', 'Q': '20',
            'r': '21', 'R': '21',
            's': '22', 'S': '22',
            't': '23', 'T': '23',
            'u': '24', 'U': '24',
            'v': '25', 'V': '25',
            'w': '26', 'W': '26',
            'x': '27', 'X': '27',
            'y': '28', 'Y': '28',
            'z': '29', 'Z': '29',
            
            // Numbers - HID usage codes
            '1': '30', '2': '31', '3': '32', '4': '33', '5': '34',
            '6': '35', '7': '36', '8': '37', '9': '38', '0': '39',
            
            // Special keys
            'Enter': '40',      // Return
            'Escape': '41',     // Escape
            'Backspace': '42',  // Backspace
            'Tab': '43',        // Tab
            ' ': '44',          // Space
            
            // Punctuation
            '-': '45',          // Minus/Hyphen
            '=': '46',          // Equal
            '[': '47',          // Left bracket
            ']': '48',          // Right bracket
            '\\': '49',         // Backslash
            ';': '51',          // Semicolon
            "'": '52',          // Apostrophe
            '`': '53',          // Grave accent
            ',': '54',          // Comma
            '.': '55',          // Period
            '/': '56',          // Slash
            
            // Arrow keys
            'ArrowRight': '79', // Right arrow
            'ArrowLeft': '80',  // Left arrow
            'ArrowDown': '81',  // Down arrow
            'ArrowUp': '82',    // Up arrow
            
            // Delete key
            'Delete': '76'      // Delete forward
        };
        
        // Try direct mapping first
        if (keyMappings[key]) {
            return keyMappings[key];
        }
        
        // No fallback - only use mapped keys
        return null;
    }
    
    showRealtimeKeyFeedback(key) {
        const keyboardHint = document.getElementById('keyboard-hint');
        if (keyboardHint) {
            const displayKey = key === ' ' ? 'SPACE' : key === 'Enter' ? 'RETURN' : key;
            keyboardHint.textContent = `⚡ Sent: ${displayKey}`;
            keyboardHint.style.color = '#00ff00';
            
            setTimeout(() => {
                keyboardHint.textContent = '⚡ Real-time mode: Each keystroke is sent immediately to the device';
                keyboardHint.style.color = '#007AFF';
            }, 500);
        }
    }
    
    // Swipe gesture functionality
    toggleSwipeMenu() {
        const swipeMenu = document.getElementById('swipe-menu');
        if (swipeMenu) {
            swipeMenu.classList.toggle('show');
        }
    }
    
    performSwipeGesture(direction) {
        // Close the menu
        const swipeMenu = document.getElementById('swipe-menu');
        if (swipeMenu) {
            swipeMenu.classList.remove('show');
        }
        
        // Define swipe coordinates based on device dimensions
        const centerX = Math.round(this.deviceDimensions.width / 2);
        const centerY = Math.round(this.deviceDimensions.height / 2);
        const swipeDistance = Math.round(Math.min(this.deviceDimensions.width, this.deviceDimensions.height) * 0.3);
        
        let startX, startY, endX, endY;
        
        switch (direction) {
            case 'up':
                startX = centerX;
                startY = centerY + swipeDistance;
                endX = centerX;
                endY = centerY - swipeDistance;
                break;
            case 'down':
                startX = centerX;
                startY = centerY - swipeDistance;
                endX = centerX;
                endY = centerY + swipeDistance;
                break;
            case 'left':
                startX = centerX + swipeDistance;
                startY = centerY;
                endX = centerX - swipeDistance;
                endY = centerY;
                break;
            case 'right':
                startX = centerX - swipeDistance;
                startY = centerY;
                endX = centerX + swipeDistance;
                endY = centerY;
                break;
            default:
                return;
        }
        
        console.log(`Performing ${direction} swipe: (${startX}, ${startY}) -> (${endX}, ${endY})`);
        this.sendDeviceAction('swipe', {
            startX: startX,
            startY: startY,
            endX: endX,
            endY: endY,
            duration: 0.3
        });
    }
    
    // Video recording functionality
    async startRecording() {
        if (this.isRecording) {
            return;
        }
        
        try {
            const sessionId = this.config?.sessionId;
            const serverUrl = this.config?.serverUrl;
            
            if (!sessionId || !serverUrl) {
                console.error('Missing session ID or server URL for recording');
                return;
            }
            
            // Call the recording start API
            const response = await fetch(`${serverUrl}/api/sessions/${sessionId}/recording/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                this.isRecording = true;
                this.updateRecordingUI(true);
                console.log('Recording started successfully');
            } else {
                console.error('Failed to start recording:', response.statusText);
            }
        } catch (error) {
            console.error('Error starting recording:', error);
        }
    }
    
    async stopRecording() {
        if (!this.isRecording) {
            return;
        }
        
        try {
            const sessionId = this.config?.sessionId;
            const serverUrl = this.config?.serverUrl;
            
            if (!sessionId || !serverUrl) {
                console.error('Missing session ID or server URL for recording');
                return;
            }
            
            // Call the recording stop API
            const response = await fetch(`${serverUrl}/api/sessions/${sessionId}/recording/stop`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                // Get the recording file and trigger download
                const blob = await response.blob();
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                const filename = `ios-recording-${sessionId.substring(0, 8)}-${timestamp}.mp4`;
                
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                
                // Clean up
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.isRecording = false;
                this.updateRecordingUI(false);
                console.log(`Recording saved as ${filename}`);
            } else {
                console.error('Failed to stop recording:', response.statusText);
            }
        } catch (error) {
            console.error('Error stopping recording:', error);
        }
    }
    
    updateRecordingUI(recording) {
        const recordBtn = document.getElementById('record-btn');
        const stopRecordBtn = document.getElementById('stop-record-btn');
        
        if (recording) {
            recordBtn.style.display = 'none';
            recordBtn.classList.add('recording');
            stopRecordBtn.style.display = 'flex';
            stopRecordBtn.classList.add('recording');
        } else {
            recordBtn.style.display = 'flex';
            recordBtn.classList.remove('recording');
            stopRecordBtn.style.display = 'none';
            stopRecordBtn.classList.remove('recording');
        }
    }
}

// Initialize the renderer
new IOSBridgeRenderer();