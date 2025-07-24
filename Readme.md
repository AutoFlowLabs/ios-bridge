# 🎮 iOS Simulator Remote Control Platform

A comprehensive remote control solution for iOS simulators built with FastAPI and modern web technologies. Provides real-time streaming, device interaction, and app management capabilities through a modern web interface with persistent session management.

## 📋 Table of Contents
* [Overview](#-overview)
* [System Requirements](#-system-requirements)
* [Prerequisites](#-prerequisites)
* [Installation](#-installation)
* [Features](#-features)
* [Architecture](#️-architecture)
* [Usage](#-usage)
* [API Reference](#-api-reference)
* [Technical Stack](#️-technical-stack)
* [Configuration](#-configuration)
* [Troubleshooting](#-troubleshooting)
* [Contributing](#-contributing)

## 🌟 Overview

This project provides a complete remote control solution for iOS simulators, enabling developers and testers to interact with iOS devices through a web browser. It combines real-time video streaming (WebRTC/WebSocket), gesture controls, app management, and persistent session storage in a unified FastAPI-based platform.

## 🖥️ System Requirements

**⚠️ macOS REQUIRED - This project only works on macOS systems**

* **Operating System**: macOS 12.0 (Monterey) or later
* **Xcode**: Xcode 14.0 or later (required for iOS Simulator and simctl)
* **Python**: Python 3.8 or later
* **Hardware**: Apple Silicon (M1/M2) or Intel Mac with at least 8GB RAM

## 🔧 Prerequisites

Before installing this project, you must have the following tools installed on your macOS system:

### Essential macOS Tools

1. **Xcode and iOS Simulator**
   ```bash
   # Install Xcode from Mac App Store
   # Then install command line tools
   xcode-select --install
   ```

2. **Homebrew** (Package manager for macOS)
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. **FFmpeg** (Video processing and streaming)
   ```bash
   brew install ffmpeg
   ```

4. **iOS Device Bridge (idb)** (Facebook's iOS automation tool)
   ```bash
   brew install idb-companion
   pip install fb-idb
   ```

5. **Node.js** (For any frontend dependencies)
   ```bash
   brew install node
   ```

### Python Dependencies
```bash
pip install fastapi uvicorn websockets pillow asyncio
```

### Verify iOS Simulator Installation
```bash
# Check if simctl is available
xcrun simctl list devices

# Check if iOS runtimes are installed
xcrun simctl list runtimes
```

## Key Capabilities

* **Session Persistence**: Simulators remain active across server restarts with automatic recovery
* **Orphaned Simulator Recovery**: Automatically detects and manages running simulators not in session database
* **Multi-Simulator Support**: Create and manage multiple iOS simulator sessions simultaneously
* **Real-time Streaming**: WebSocket/WebRTC-based video streaming with screenshot mode
* **Interactive Controls**: Precise touch controls, hardware buttons, and gesture support
* **App Lifecycle Management**: Install IPA files, launch, terminate, and uninstall apps
* **Modern API**: FastAPI-based REST API with automatic documentation
## ✨ Features

### 🎯 Core Features

**Session Management**
* **Persistent Sessions**: Simulators survive server restarts with JSON-based storage
* **Orphaned Recovery**: Automatically detects and creates sessions for running simulators on startup
* **Multi-Simulator**: Create and manage multiple iOS simulator sessions simultaneously
* **Session Validation**: Automatic validation and cleanup of invalid sessions
* **Hot Reload**: Development server restarts without killing simulators

**Simulator Control**
* **Touch Interactions**: Precise tap and swipe gestures with coordinate mapping
* **Hardware Buttons**: Home, lock, volume, Siri, Apple Pay, shake simulation
* **Text Input**: Send text directly to simulator input fields
* **Device Configuration**: Support for all iOS device types and versions (iPhone, iPad)
* **Real-time Status**: Live simulator state monitoring and health checks

### 🚀 Advanced Features

**Video Streaming**
* **Multiple Modes**: WebSocket video streaming and WebRTC for real-time interaction
* **Screenshot Mode**: High-quality static image capture with on-demand updates
* **Performance Control**: Dynamic quality adjustment and frame rate control
* **Stream Management**: Per-session streaming with quality presets (low, medium, high, ultra)

**App Management**
* **IPA Installation**: Automatic app installation with simulator compatibility modifications
* **Bundle Processing**: Auto-modify apps for simulator compatibility (remove code signing, fix Info.plist)
* **App Lifecycle**: Complete install, launch, terminate, uninstall operations
* **Debug Support**: Comprehensive installation diagnostics and error reporting
* **App Tracking**: Monitor installed apps per session with metadata

**API & Integration**
* **FastAPI Backend**: Modern async web framework with automatic OpenAPI documentation
* **WebSocket Endpoints**: Real-time bidirectional communication for control and streaming
* **REST API**: Complete CRUD operations for sessions and app management
* **Session-Aware**: All operations are scoped to specific simulator sessions
* **Error Handling**: Comprehensive error reporting and graceful degradation
## 🏗️ Architecture

### System Overview

```
┌─────────────────┐    WebSocket/HTTP    ┌─────────────────┐
│   Web Frontend  │ ←→ ←→ ←→ ←→ ←→ ←→ │  FastAPI Server │
│                 │                     │                 │
│ • Video Stream  │                     │ • Session Mgmt  │
│ • WebRTC        │                     │ • App Control   │
│ • Touch Input   │                     │ • WebSocket     │
│ • Controls UI   │                     │ • Persistence   │
└─────────────────┘                     └─────────────────┘
                                                 ↓
                                        ┌─────────────────┐
                                        │ Session Manager │
                                        │                 │
                                        │ • JSON Storage  │
                                        │ • Validation    │
                                        │ • Recovery      │
                                        │ • Cleanup       │
                                        └─────────────────┘
                                                 ↓
                                        ┌─────────────────┐
                                        │ iOS Simulator   │
                                        │ Manager         │
                                        │                 │
                                        │ • xcrun simctl  │
                                        │ • Device Ctrl   │
                                        │ • App Mgmt      │
                                        └─────────────────┘
                                                 ↓
                                        ┌─────────────────┐
                                        │ iOS Simulators  │
                                        │                 │
                                        │ • Session 1     │
                                        │ • Session 2     │
                                        │ • Session N     │
                                        └─────────────────┘
```

### Component Breakdown

**FastAPI Application (`main.py`)**
* Lifespan management with startup/shutdown hooks
* Orphaned simulator recovery on application startup
* WebSocket endpoints for control, video, WebRTC, and screenshots
* Session-aware routing with validation
* Health check and status endpoints

**Session Manager (`session_manager.py`)**
* Persistent JSON-based session storage
* Automatic session validation and cleanup
* Orphaned simulator detection and recovery
* Thread-safe session operations
* Backup and restore functionality

**iOS Simulator Manager (`ios_sim_manager_service.py`)**
* Core simulator lifecycle management (create, boot, shutdown, delete)
* App installation with simulator compatibility fixes
* Device control via `xcrun simctl`
* PID tracking and process management
* Comprehensive error handling and logging

**WebSocket Services**
* `ControlWebSocket`: Device control and touch input
* `VideoWebSocket`: Real-time video streaming
* `WebRTCWebSocket`: WebRTC-based streaming
* `ScreenshotWebSocket`: High-quality screenshot capture

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ios-bridge
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify iOS Simulator setup**
   ```bash
   xcrun simctl list devices
   xcrun simctl list runtimes
   ```

4. **Start the server**
   ```bash
   # Set Python path and run
   PYTHONPATH=/path/to/ios-bridge python app/main.py
   
   # Or use uvicorn directly
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Access the web interface**
   ```
   http://localhost:8000
   ```


## 🎯 Usage

### Basic Workflow

1. **Start the server**
   ```bash
   PYTHONPATH=/path/to/ios-bridge python app/main.py
   ```

2. **Access the web interface**
   ```
   http://localhost:8000
   ```

3. **The system will automatically:**
   * Load existing sessions from persistent storage
   * Scan for orphaned running simulators and create sessions for them
   * Provide a session list interface to manage simulators

### Web Interface Guide

**Session Management**
* View all active simulator sessions
* Create new simulator sessions with device type and iOS version selection
* Access individual simulator control pages
* Monitor session status and health

**Control Interface (`/control/{session_id}`)**
* **Video Streaming**: Real-time simulator display with WebSocket/WebRTC
* **Screenshot Mode**: High-quality static screenshots on demand
* **Touch Controls**: Precise tap and swipe with coordinate mapping
* **Hardware Buttons**: Home, lock, volume, Siri, Apple Pay, shake
* **Text Input**: Send text directly to simulator
* **App Management**: Install IPA files, launch, terminate, and uninstall apps

**Quality Controls**
* Stream quality presets: Low, Medium, High, Ultra
* Dynamic frame rate adjustment
* WebRTC vs WebSocket streaming modes

### API Usage Examples

**Create a new session**
```bash
curl -X POST "http://localhost:8000/api/sessions/create" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "device_type=iPhone 16&ios_version=18.2"
```

**List all sessions**
```bash
curl "http://localhost:8000/api/sessions/"
```

**Install an app**
```bash
curl -X POST "http://localhost:8000/api/sessions/{session_id}/apps/install" \
     -F "ipa_file=@/path/to/app.ipa"
```

**Recover orphaned simulators**
```bash
curl -X POST "http://localhost:8000/api/sessions/recover-orphaned"
```

## 🔧 API Reference

### REST Endpoints

**Session Management**
```bash
# List all sessions
GET /api/sessions/

# Get available device configurations
GET /api/sessions/configurations

# Create new session
POST /api/sessions/create
Content-Type: application/x-www-form-urlencoded
Body: device_type=iPhone 16&ios_version=18.2

# Get session details
GET /api/sessions/{session_id}

# Delete session
DELETE /api/sessions/{session_id}

# Delete all sessions
DELETE /api/sessions/

# Recover orphaned simulators
POST /api/sessions/recover-orphaned

# Refresh session states
GET /api/sessions/refresh
```

**App Management**
```bash
# Install IPA file
POST /api/sessions/{session_id}/apps/install
Content-Type: multipart/form-data
Body: ipa_file=@app.ipa

# List installed apps
GET /api/sessions/{session_id}/apps

# Launch app
POST /api/sessions/{session_id}/apps/{bundle_id}/launch

# Terminate app
POST /api/sessions/{session_id}/apps/{bundle_id}/terminate

# Uninstall app
DELETE /api/sessions/{session_id}/apps/{bundle_id}
```

**Status & Health**
```bash
# Application health check
GET /health

# Session-specific status
GET /status/{session_id}

# Legacy status (all sessions)
GET /status

# WebRTC quality control
GET /webrtc/quality/{session_id}/{quality}
# quality: low, medium, high, ultra
```

### WebSocket Endpoints

**Control WebSocket**
```javascript
// Connect to control WebSocket
const controlSocket = new WebSocket(`ws://localhost:8000/ws/${sessionId}/control`);

// Send touch commands
controlSocket.send(JSON.stringify({
    type: 'tap',
    x: 195,
    y: 422
}));

// Send swipe commands
controlSocket.send(JSON.stringify({
    type: 'swipe',
    start_x: 100,
    start_y: 400,
    end_x: 300,
    end_y: 400,
    duration: 0.3
}));

// Send hardware button commands
controlSocket.send(JSON.stringify({
    type: 'button',
    button: 'home' // home, lock, volume_up, volume_down, siri, apple_pay, shake
}));

// Send text input
controlSocket.send(JSON.stringify({
    type: 'text',
    text: 'Hello World'
}));
```

**Video Streaming WebSocket**
```javascript
// Connect to video stream
const videoSocket = new WebSocket(`ws://localhost:8000/ws/${sessionId}/video`);

videoSocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'video_frame') {
        // data.frame contains base64 encoded image
        // data.width, data.height contain dimensions
        updateVideoCanvas(data.frame, data.width, data.height);
    }
};
```

**WebRTC WebSocket**
```javascript
// Connect to WebRTC stream for higher quality
const webrtcSocket = new WebSocket(`ws://localhost:8000/ws/${sessionId}/webrtc`);

// Handle WebRTC signaling messages
webrtcSocket.onmessage = function(event) {
    const message = JSON.parse(event.data);
    // Handle offer, answer, ice-candidate messages
    handleWebRTCSignaling(message);
};
```

**Screenshot WebSocket**
```javascript
// Connect to screenshot service
const screenshotSocket = new WebSocket(`ws://localhost:8000/ws/${sessionId}/screenshot`);

// Request screenshot
screenshotSocket.send(JSON.stringify({
    type: 'capture'
}));

screenshotSocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'screenshot') {
        // High-quality screenshot data
        displayScreenshot(data.image, data.width, data.height);
    }
};
```



## 🛠️ Technical Stack

### Backend Technologies

**Web Framework & Server**
* **FastAPI** - Modern Python async web framework
  * Automatic OpenAPI/Swagger documentation
  * Built-in WebSocket support for real-time communication
  * Async/await support for high-performance concurrent operations
  * Automatic request/response validation and serialization
* **Uvicorn** - Lightning-fast ASGI server with hot reload capabilities
* **Starlette** - FastAPI's underlying framework for WebSocket handling

**Session Management & Storage**
* **JSON-based Persistence** - Lightweight session storage with backup rotation
* **Automatic Recovery** - Orphaned simulator detection and session restoration
* **Thread-safe Operations** - Concurrent session access with proper locking
* **Validation System** - Session health checks and cleanup routines

**iOS Simulator Integration**
* **xcrun simctl** - Apple's official iOS Simulator command-line interface
  * Device creation, booting, and management
  * App installation and lifecycle management
  * Screenshot capture and device control
* **Process Management** - PID tracking and simulator process monitoring
* **Device State Management** - Real-time simulator state synchronization

**Streaming & Communication**
* **WebSocket** - Real-time bidirectional communication
  * Control commands (touch, gestures, hardware buttons)
  * Video frame streaming with base64 encoding
  * Screenshot delivery with quality optimization
* **WebRTC** - Low-latency video streaming with multiple quality presets
* **Async I/O** - Non-blocking operations for concurrent client support

### Frontend Technologies

**Core Web Technologies**
* **HTML5 Canvas** - Hardware-accelerated video rendering
* **WebSocket API** - Real-time bidirectional communication
* **Vanilla JavaScript** - No framework dependencies for maximum performance
* **CSS Grid/Flexbox** - Responsive layout system

**Video & Streaming**
* **Canvas 2D API** - Efficient frame rendering and display
* **WebRTC** - Low-latency streaming with peer-to-peer capabilities
* **Base64 Image Processing** - Frame decoding and display optimization
* **Dynamic Quality Control** - Client-side quality adjustment

### System Integration

**macOS-Specific Requirements**
* **Xcode & iOS Simulator** - Essential for simulator device management
* **Command Line Tools** - xcrun, simctl for system integration
* **macOS Security** - Proper permissions for simulator access

**Development Tools**
* **Python 3.8+** - Modern Python with async/await support
* **Virtual Environment** - Isolated Python environment management
* **Hot Reload** - Development server with automatic restart
* **Logging System** - Comprehensive error tracking and debugging

**Performance Optimizations**
* **Multi-threaded Processing** - Concurrent screenshot and video processing
* **Frame Caching** - Intelligent frame buffering and delivery
* **Memory Management** - Automatic cleanup and resource pooling
* **Dynamic Quality Adaptation** - Adaptive streaming based on client capabilities

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Paths
STATIC_DIR=static
TEMPLATE_DIR=templates

# Session Storage
SESSION_STORAGE_DIR=session_storage
BACKUP_RETENTION_COUNT=5

# Streaming Configuration
DEFAULT_VIDEO_QUALITY=medium
SCREENSHOT_CACHE_TTL=60
MAX_CONCURRENT_SESSIONS=10
```

### Session Storage Configuration

```python
# app/config/settings.py
class Settings:
    # Storage settings
    SESSION_STORAGE_DIR: str = "session_storage"
    BACKUP_RETENTION_COUNT: int = 5
    
    # Video streaming settings
    DEFAULT_VIDEO_QUALITY: str = "medium"
    SCREENSHOT_CACHE_TTL: int = 60
    
    # Simulator settings
    MAX_CONCURRENT_SESSIONS: int = 10
    SIMULATOR_BOOT_TIMEOUT: int = 120
```

### Simulator Configuration

Available device types and iOS versions are automatically detected from your Xcode installation:

```bash
# Check available configurations
curl "http://localhost:8000/api/sessions/configurations"
```

Response includes:
```json
{
  "success": true,
  "configurations": {
    "device_types": {
      "iPhone 16": "com.apple.CoreSimulator.SimDeviceType.iPhone-16",
      "iPhone 16 Pro": "com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro",
      "iPad Pro 11-inch (M4)": "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-11-inch-M4"
    },
    "ios_versions": {
      "18.2": "com.apple.CoreSimulator.SimRuntime.iOS-18-2",
      "17.5": "com.apple.CoreSimulator.SimRuntime.iOS-17-5"
    }
  }
}
```

## 🐛 Troubleshooting

### Common Issues

**1. "Module not found" errors**
```bash
# Solution: Set Python path
export PYTHONPATH=/path/to/ios-bridge
python app/main.py

# Or use uvicorn directly
cd ios-bridge
uvicorn app.main:app --reload
```

**2. No iOS Simulators available**
```bash
# Check Xcode installation
xcode-select -p

# Install iOS Simulator if missing
# Open Xcode > Preferences > Components > Install iOS Simulators

# Verify simulators are available
xcrun simctl list devices available
```

**3. Session not persisting after restart**
- Check `session_storage` directory permissions
- Verify JSON files are not corrupted
- Use the refresh endpoint: `GET /api/sessions/refresh`

**4. WebSocket connection failures**
- Ensure no firewall blocking port 8000
- Check browser console for WebSocket errors
- Verify session exists before connecting

**5. App installation fails**
```bash
# Common causes:
# - IPA file is device-only (not simulator compatible)
# - Code signing issues
# - Invalid bundle structure

# Check logs for detailed error messages
# The system automatically modifies IPAs for simulator compatibility
```

**6. Orphaned simulator detection not working**
```bash
# Manually trigger recovery
curl -X POST "http://localhost:8000/api/sessions/recover-orphaned"

# Check for running simulators
xcrun simctl list devices | grep Booted

# Verify session creation
curl "http://localhost:8000/api/sessions/"
```

### Debug Commands

```bash
# Check system health
curl "http://localhost:8000/health"

# Get detailed session info
curl "http://localhost:8000/api/sessions/{session_id}"

# Check session storage
curl "http://localhost:8000/api/sessions/storage/info"

# Refresh all sessions
curl "http://localhost:8000/api/sessions/refresh"

# Clean up storage
curl -X POST "http://localhost:8000/api/sessions/cleanup"
```

### Log Analysis

The application provides comprehensive logging:

```bash
# Check application logs for errors
tail -f logs/app.log

# Common log patterns to look for:
# - "Session {id} no longer valid" - Session cleanup
# - "Recovered {count} orphaned simulator sessions" - Startup recovery
# - "Failed to validate session" - Session validation issues
# - "WebSocket disconnected" - Client connection issues
```

## 🤝 Contributing

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone <your-fork>
   cd ios-bridge
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

4. **Run in development mode**
   ```bash
   PYTHONPATH=$(pwd) uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings for all public methods
- Include error handling and logging

### Testing

```bash
# Run tests (if test suite exists)
python -m pytest

# Test specific functionality
curl -X POST "http://localhost:8000/api/sessions/recover-orphaned"
```

### Submitting Changes

1. Create a feature branch
2. Make your changes with proper commit messages
3. Test thoroughly on macOS
4. Submit a pull request with detailed description

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Apple for iOS Simulator and development tools
- FastAPI team for the excellent web framework
- The Python async/await ecosystem
- macOS development community

---

**⚠️ Important: This project requires macOS and will not work on Windows or Linux due to iOS Simulator dependencies.**
