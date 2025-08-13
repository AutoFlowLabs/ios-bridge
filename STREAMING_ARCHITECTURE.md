# iOS Bridge Streaming Architecture

## Overview

The iOS Bridge system supports multiple streaming methods to provide iOS simulator video and control capabilities to both web interfaces and desktop applications. This document explains the architecture, implementation, and trade-offs of each streaming approach.

## Table of Contents

1. [Streaming Methods Overview](#streaming-methods-overview)
2. [WebSocket Streaming Architecture](#websocket-streaming-architecture)
3. [WebRTC Streaming Architecture](#webrtc-streaming-architecture)
4. [Ultra Low-Latency Mode](#ultra-low-latency-mode)
5. [Queue Management](#queue-management)
6. [Performance Optimization](#performance-optimization)
7. [Integration with iOS Bridge](#integration-with-ios-bridge)

---

## Streaming Methods Overview

### Available Streaming Modes

| Mode | Technology | Latency | Quality | Use Case |
|------|------------|---------|---------|----------|
| **WebSocket** | Screenshot-based | Medium (100-300ms) | High | General usage, high quality needed |
| **Ultra Low-Latency** | Optimized Screenshots | Low (50-150ms) | Medium | Interactive applications, gaming |
| **WebRTC** | Real-time Protocol | Lowest (20-100ms) | Variable | Real-time collaboration, demos |

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   iOS Simulator │    │   iOS Bridge     │    │    Client       │
│                 │    │    Server        │    │  (Web/Electron) │
│  ┌───────────┐  │    │                  │    │                 │
│  │    App    │  │────┤  Video Services  │────┤  Video Display  │
│  │ Interface │  │    │  Queue System    │    │  Touch Handling │
│  └───────────┘  │    │  WebSocket/WebRTC│    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## WebSocket Streaming Architecture

### 1. Core Implementation

WebSocket streaming uses the **VideoService** which employs multiple fallback methods for video capture:

```python
# Video capture hierarchy (app/services/video_service.py)
1. idb video-stream (H.264) - Primary method
2. FFmpeg hardware acceleration - Fallback 1  
3. FFmpeg software encoding - Fallback 2
4. High-frequency screenshots - Final fallback
```

### 2. Video Capture Pipeline

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  iOS Simulator  │    │   VideoService   │    │  VideoWebSocket │
│                 │    │                  │    │                 │
│                 │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ idb video-stream│───▶│ │ Capture Loop │ │───▶│ │ Frame Queue │ │
│    (H.264)      │    │ │   60 FPS     │ │    │ │  (3 frames) │ │
│                 │    │ └──────────────┘ │    │ └─────────────┘ │
│                 │    │        │         │    │        │        │
│                 │    │ ┌──────▼──────┐  │    │ ┌──────▼──────┐ │
│                 │    │ │JPEG Encoding│  │    │ │   WebSocket │ │
│                 │    │ │  Quality 80 │  │    │ │ Transmission│ │
│                 │    │ └─────────────┘  │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 3. WebSocket Message Flow

#### Server Side (`app/api/websockets/video_ws.py`)

```javascript
// Frame Processing Loop
while (connected) {
    frame_data = video_service.get_frame(timeout=0.05)
    
    if (frame_data) {
        video_frame = VideoFrame({
            data: frame_data["data"],           // Base64 JPEG
            pixel_width: frame_data["width"],   // 1179px (3x scaling)
            pixel_height: frame_data["height"], // 2556px 
            point_width: 393,                   // Logical points
            point_height: 852,
            frame: frame_count,
            timestamp: current_time,
            fps: calculated_fps,
            format: "jpeg"
        })
        
        await websocket.send_text(video_frame.json())
    }
}
```

#### Client Side Processing

**Web Interface (`templates/control.html`):**
```javascript
videoWs.onmessage = (event) => {
    const frame = JSON.parse(event.data);
    
    // Update canvas dimensions if needed
    if (canvas.width !== frame.pixel_width) {
        canvas.width = frame.pixel_width;
        canvas.height = frame.pixel_height;
    }
    
    // Render frame
    const img = new Image();
    img.onload = () => {
        ctx.drawImage(img, 0, 0);
    };
    img.src = `data:image/jpeg;base64,${frame.data}`;
};
```

**Electron App (`ios-bridge-cli/src/renderer.js`):**
```javascript
handleVideoFrame(frameData) {
    // Auto-resize window based on video dimensions
    if (img.width !== this.streamDimensions.width) {
        this.streamDimensions = { width: img.width, height: img.height };
        window.electronAPI.resizeWindow(img.width, img.height);
    }
    
    // Update canvas and render
    this.ctx.drawImage(img, 0, 0);
}
```

### 4. Queue Management in WebSocket Mode

```python
# VideoService Queue Configuration
VIDEO_QUEUE_SIZE = 3  # Maximum buffered frames
frame_timeout = 0.05  # 50ms timeout for frame retrieval

class VideoService:
    def _enqueue_frame(self, frame_data):
        try:
            self.video_frame_queue.put_nowait(frame_data)
        except queue.Full:
            # Drop oldest frame to prevent buffering
            self.video_frame_queue.get_nowait()  
            self.video_frame_queue.put_nowait(frame_data)
```

**Queue Behavior:**
- **Size**: 3 frames maximum
- **Overflow**: Drop oldest frame when full
- **Retrieval**: 50ms timeout prevents blocking
- **Purpose**: Balance latency vs. frame drops

### 5. Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Target FPS** | 60 FPS | Configurable via `DEFAULT_VIDEO_FPS` |
| **Frame Buffer** | 3 frames | `VIDEO_QUEUE_SIZE` |
| **JPEG Quality** | 80% | `DEFAULT_JPEG_QUALITY` |
| **Typical Latency** | 100-300ms | Depends on network and processing |
| **Resolution** | 1179x2556 | 3x logical scaling for retina |

---

## WebRTC Streaming Architecture

### 1. Core Implementation

WebRTC streaming uses the **FastWebRTCService** which provides real-time peer-to-peer video transmission:

```python
# WebRTC Service (app/services/fast_webrtc_service.py)
- Screenshot-based frames at high frequency
- aiortc library for WebRTC implementation
- Optimized for low latency over quality
```

### 2. WebRTC Pipeline

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  iOS Simulator  │    │ FastWebRTCService│    │   WebRTC Peer   │
│                 │    │                  │    │   Connection    │
│                 │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ Screenshot API  │───▶│ │ Capture Loop │ │───▶│ │ Video Track │ │
│   (PNG->JPEG)   │    │ │   75 FPS     │ │    │ │  (H.264)    │ │
│                 │    │ └──────────────┘ │    │ └─────────────┘ │
│                 │    │        │         │    │        │        │
│                 │    │ ┌──────▼──────┐  │    │ ┌──────▼──────┐ │
│                 │    │ │VideoFrame   │  │    │ │   Browser   │ │
│                 │    │ │PyAV Encoding│  │    │ │   Decoder   │ │
│                 │    │ └─────────────┘  │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 3. WebRTC Signaling Flow

#### Server Side (`app/api/websockets/webrtc_ws.py`)

```python
# WebRTC Signaling Messages
{
    "start-stream": {
        "quality": "high",    # low/medium/high/ultra
        "fps": 75
    },
    
    "offer": {
        "sdp": "...",         # Session Description
        "type": "offer"
    },
    
    "ice-candidate": {
        "candidate": "...",   # ICE candidate data
        "sdpMLineIndex": 0
    }
}
```

#### Quality Presets

```python
# WebRTC Quality Configuration (app/main.py)
presets = {
    "low":    {"fps": 45, "resolution": "234x507",  "quality": "good"},
    "medium": {"fps": 60, "resolution": "312x675",  "quality": "better"},
    "high":   {"fps": 75, "resolution": "390x844",  "quality": "high"},
    "ultra":  {"fps": 90, "resolution": "468x1014", "quality": "best"}
}
```

### 4. Client-Side WebRTC Implementation

**Web Interface WebRTC Setup:**
```javascript
async function setupWebRTCStream() {
    // Create peer connection
    peerConnection = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    });
    
    // Handle incoming video stream
    peerConnection.ontrack = (event) => {
        webrtcVideo.srcObject = event.streams[0];
    };
    
    // Create offer and start signaling
    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    
    // Send offer via WebSocket
    webrtcWs.send(JSON.stringify({
        type: 'offer',
        sdp: offer.sdp
    }));
}
```

**Electron App WebRTC Integration:**
```javascript
async function connectWebRTC(wsUrl) {
    this.peerConnection = new RTCPeerConnection();
    
    this.peerConnection.ontrack = (event) => {
        this.webrtcVideo.srcObject = event.streams[0];
        
        // Auto-resize and coordinate mapping
        this.webrtcVideo.onloadedmetadata = async () => {
            await this.updateWebRTCVideoLayoutFromElement();
        };
    };
}
```

### 5. Queue Management in WebRTC Mode

```python
# FastWebRTCService Queue Configuration
WEBRTC_QUEUE_SIZE = 2  # Minimal buffering for low latency

class FastWebRTCService:
    def start_video_stream(self, quality="high", fps=60):
        # High-frequency capture thread
        self.frame_thread = threading.Thread(
            target=self._generate_fast_frames, 
            daemon=True
        )
```

**WebRTC Queue Behavior:**
- **Size**: 2 frames maximum
- **Strategy**: Aggressive frame dropping
- **Timing**: Precise frame intervals
- **Goal**: Minimize end-to-end latency

### 6. Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Target FPS** | 75 FPS | Optimized for low latency |
| **Frame Buffer** | 2 frames | Minimal buffering |
| **Encoding** | H.264 | Hardware accelerated when available |
| **Typical Latency** | 50-150ms | Peer-to-peer connection |
| **Quality** | Variable | Adaptive based on network |

---

## Ultra Low-Latency Mode

### 1. Implementation Strategy

Ultra Low-Latency mode uses the working **VideoService** with optimized settings and processing:

```python
# Ultra Low-Latency Configuration
ULTRA_LOW_LATENCY_FPS = 75        # Realistic target
ULTRA_LOW_LATENCY_QUEUE_SIZE = 1  # Single frame buffer
FRAME_DROP_THRESHOLD = 0.05       # 50ms max processing
```

### 2. Optimized Processing Pipeline

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   VideoService  │    │UltraLowLatencyWS │    │     Client      │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │idb video-   │ │───▶│ │ Frame Queue  │ │───▶│ │Ultra-fast   │ │
│ │stream (H264)│ │    │ │ (1 frame)    │ │    │ │Rendering    │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
│        │        │    │        │         │    │        │        │
│ ┌──────▼──────┐ │    │ ┌──────▼──────┐  │    │ ┌──────▼──────┐ │
│ │JPEG Encoding│ │    │ │  1ms timeout│  │    │ │   Canvas    │ │
│ │ Quality 80  │ │    │ │  retrieval  │  │    │ │ clearRect() │ │
│ └─────────────┘ │    │ └─────────────┘  │    │ │ drawImage() │ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 3. Frame Processing Optimizations

#### Server Side (`app/api/websockets/ultra_low_latency_ws.py`)

```python
async def _ultra_low_latency_video_loop(self, websocket):
    # Pre-create reusable objects
    base_frame_data = {
        "point_width": point_width,
        "point_height": point_height,
        "format": "jpeg"
    }
    
    while True:
        # Minimal timeout frame retrieval
        frame_data = self.video_service.get_frame(timeout=0.001)
        
        if frame_data:
            # Optimized VideoFrame creation
            video_frame = VideoFrame(
                data=frame_data["data"],
                pixel_width=frame_data.get("pixel_width", 390),
                pixel_height=frame_data.get("pixel_height", 844),
                **base_frame_data,
                frame=frame_count,
                timestamp=frame_data["timestamp"],
                fps=int(round(current_fps))  # Integer conversion
            )
            
            # Immediate transmission
            await websocket.send_text(video_frame.model_dump_json())
```

#### Client Side Processing

```javascript
// Ultra-fast image loading and rendering
const img = new Image();
img.onload = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    
    // Update performance stats
    updateUltraLowLatencyStats(frame);
};
img.src = `data:image/jpeg;base64,${frame.data}`;
```

---

## Queue Management

### 1. Queue Architecture Comparison

| Mode | Queue Size | Timeout | Strategy | Latency Impact |
|------|------------|---------|----------|----------------|
| **WebSocket** | 3 frames | 50ms | Balanced | Medium |
| **Ultra Low-Latency** | 1 frame | 1ms | Aggressive | Minimal |
| **WebRTC** | 2 frames | Variable | Adaptive | Low |

### 2. Frame Drop Strategies

#### WebSocket Mode
```python
def _enqueue_frame(self, frame_data):
    try:
        self.video_frame_queue.put_nowait(frame_data)
    except queue.Full:
        # Drop oldest, keep newest
        self.video_frame_queue.get_nowait()
        self.video_frame_queue.put_nowait(frame_data)
```

#### Ultra Low-Latency Mode
```python
def _enqueue_frame_ultra_fast(self, frame_data):
    try:
        self.video_frame_queue.put_nowait(frame_data)
    except queue.Full:
        # Immediate overflow handling
        try:
            self.video_frame_queue.get_nowait()
            self.video_frame_queue.put_nowait(frame_data)
            self.dropped_frames += 1
        except queue.Empty:
            pass
```

#### WebRTC Mode
```python
class IDBVideoStreamTrack(VideoStreamTrack):
    async def recv(self):
        # Direct frame generation without queue
        frame = await self._generate_frame()
        return frame
```

### 3. Buffer Management

```
WebSocket Queue (Size: 3)
┌─────────┬─────────┬─────────┬─────────┐
│ Frame 1 │ Frame 2 │ Frame 3 │  Empty  │
└─────────┴─────────┴─────────┴─────────┘
    ↑         ↑         ↑
  Oldest    Middle    Newest
  (Drop)   (Keep)    (Keep)

Ultra Low-Latency Queue (Size: 1)
┌─────────┬─────────┐
│ Frame 1 │  Empty  │
└─────────┴─────────┘
    ↑
  Current
(Replace immediately)

WebRTC (No Queue - Direct)
┌─────────┐
│ Generate│ ──► Encode ──► Transmit
└─────────┘
```

---

## Performance Optimization

### 1. FPS Management

#### Dynamic FPS Calculation
```python
# Real-time FPS tracking
fps_counter = []
current_time = time.time()
fps_counter.append(current_time)

# Keep last 60 frames for accurate calculation
if len(fps_counter) > 60:
    fps_counter = fps_counter[-60:]

# Calculate instantaneous FPS
time_span = current_time - fps_counter[0]
current_fps = len(fps_counter) / time_span if time_span > 0 else 0
```

#### Adaptive Frame Rates
```python
# Mode-specific FPS targets
DEFAULT_VIDEO_FPS = 60        # WebSocket mode
ULTRA_LOW_LATENCY_FPS = 75    # Ultra low-latency mode
WEBRTC_TARGET_FPS = 75        # WebRTC mode

# Quality vs Performance trade-offs
quality_presets = {
    "low": {"fps": 45, "quality": 50},
    "medium": {"fps": 60, "quality": 65}, 
    "high": {"fps": 75, "quality": 80},
    "ultra": {"fps": 90, "quality": 95}
}
```

### 2. Quality Management

#### JPEG Compression Settings
```python
# Quality hierarchy
DEFAULT_JPEG_QUALITY = 80        # Balanced quality/size
LOW_LATENCY_JPEG_QUALITY = 65    # Optimized for speed
ULTRA_LOW_LATENCY_JPEG_QUALITY = 50  # Maximum speed
WEBRTC_HIGH_QUALITY = 95         # WebRTC high quality
```

#### Adaptive Quality
```javascript
// Client-side quality adjustment
function adjustQuality(networkCondition) {
    const qualityMap = {
        'excellent': 'ultra',
        'good': 'high',
        'fair': 'medium',
        'poor': 'low'
    };
    
    setWebRTCQuality(qualityMap[networkCondition]);
}
```

### 3. Memory Optimization

#### Object Reuse
```python
# Pre-allocate frame data structure
base_frame_data = {
    "point_width": point_width,
    "point_height": point_height,
    "format": "jpeg"
}

# Reuse for each frame
video_frame = VideoFrame(**base_frame_data, **frame_specific_data)
```

#### Canvas Optimization
```javascript
// Minimize canvas operations
if (canvas.width !== frame.pixel_width || canvas.height !== frame.pixel_height) {
    canvas.width = frame.pixel_width;
    canvas.height = frame.pixel_height;
}

// Ultra-fast rendering
ctx.clearRect(0, 0, canvas.width, canvas.height);
ctx.drawImage(img, 0, 0);
```

---

## Integration with iOS Bridge

### 1. Session Management

```python
# Session-based streaming (app/services/session_manager.py)
class SessionManager:
    def create_session(self, udid):
        """Create new streaming session for device"""
        
    def get_session_udid(self, session_id):
        """Get device UDID for session"""
        
    def cleanup_session(self, session_id):
        """Clean up streaming resources"""
```

### 2. WebSocket Endpoints

```python
# Streaming endpoints (app/main.py)
@app.websocket("/ws/{session_id}/video")           # Standard WebSocket
@app.websocket("/ws/{session_id}/ultra-low-latency")  # Ultra Low-Latency
@app.websocket("/ws/{session_id}/webrtc")          # WebRTC signaling
@app.websocket("/ws/{session_id}/control")         # Touch/control
```

### 3. Client Integration

#### Web Interface
```html
<!-- Streaming mode selection -->
<div class="controls-section">
    <h3>📱 Stream Mode</h3>
    <div class="mode-toggle controls-grid">
        <button onclick="switchMode('webrtc')">🚀 WebRTC Stream</button>
        <button onclick="switchMode('video')" class="active">🎥 WebSocket Stream</button>
        <button onclick="switchMode('ultra-low-latency')">⚡ Ultra Low-Latency</button>
        <button onclick="switchMode('screenshot')">📷 Screenshot Mode</button>
    </div>
</div>
```

#### Electron App
```javascript
// Stream mode cycling: websocket → ultra-low-latency → webrtc → websocket
toggleStreamMode() {
    if (this.streamMode === 'websocket') {
        this.streamMode = 'ultra-low-latency';
    } else if (this.streamMode === 'ultra-low-latency') {
        this.streamMode = 'webrtc';
    } else {
        this.streamMode = 'websocket';
    }
}
```

### 4. Coordinate Mapping

```javascript
// Convert display coordinates to device coordinates
function convertToDeviceCoords(displayX, displayY) {
    const deviceX = Math.round((displayX / displayWidth) * pointWidth);
    const deviceY = Math.round((displayY / displayHeight) * pointHeight);
    return { x: deviceX, y: deviceY };
}

// Handle touch events across all streaming modes
function handleTouchEvent(event) {
    const coords = convertToDeviceCoords(event.offsetX, event.offsetY);
    
    if (controlWs) {
        controlWs.send(JSON.stringify({
            t: 'tap',
            x: coords.x,
            y: coords.y
        }));
    }
}
```

---

## Summary

The iOS Bridge streaming architecture provides flexible, high-performance video streaming with three distinct modes optimized for different use cases:

- **WebSocket Mode**: Balanced approach with reliable quality and moderate latency
- **Ultra Low-Latency Mode**: Optimized for interactive applications requiring minimal delay
- **WebRTC Mode**: Real-time streaming with peer-to-peer efficiency

Each mode employs sophisticated queue management, adaptive quality control, and performance optimization to deliver the best possible user experience while maintaining system reliability and responsiveness.