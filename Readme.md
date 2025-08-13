# 🎮 iOS Simulator Remote Control Platform

A comprehensive remote control solution for iOS simulators built with FastAPI and modern web technologies. Provides real-time streaming, device interaction, and app management capabilities through a modern web interface with persistent session management.

## 📋 Table of Contents
* [Overview](#-overview)
* [System Requirements](#-system-requirements)
* [Prerequisites](#-prerequisites)
* [Installation](#-installation)
* [Features](#-features)
* [Electron Desktop App](#-electron-desktop-app)
* [Architecture](#️-architecture)
* [Usage](#-usage)
* [API Reference](#-api-reference)
* [Technical Stack](#️-technical-stack)
* [Configuration](#-configuration)
* [Troubleshooting](#-troubleshooting)
* [Contributing](#-contributing)

## 🌟 Overview

This project provides a complete remote control solution for iOS simulators, enabling developers and testers to interact with iOS devices through both a web browser and a native Electron desktop application. It combines real-time video streaming (WebRTC/WebSocket), gesture controls, app management, video recording, and persistent session storage in a unified FastAPI-based platform.

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
* **Predefined Swipe Gestures**: Quick swipe controls (⬆️ Up, ⬇️ Down, ⬅️ Left, ➡️ Right)
* **Hardware Buttons**: Home, lock, volume, Siri, Apple Pay, shake simulation
* **Text Input**: Send text directly to simulator input fields with real-time keyboard mode
* **Real-time Keyboard**: Live key-by-key input using HID usage codes for natural typing
* **Device Configuration**: Support for all iOS device types and versions (iPhone, iPad)
* **Real-time Status**: Live simulator state monitoring and health checks

### 🚀 Advanced Features

**Video Streaming & Recording**
* **Multiple Modes**: WebSocket video streaming and WebRTC for real-time interaction
* **Screenshot Mode**: High-quality static image capture with on-demand updates
* **Performance Control**: Dynamic quality adjustment and frame rate control
* **Stream Management**: Per-session streaming with quality presets (low, medium, high, ultra)
* **Video Recording**: MP4 video recording with automatic download functionality
* **Emergency Recording Save**: Automatic recording preservation on app exit

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

## 🖥️ Electron Desktop App

### iOS Bridge CLI

A powerful command-line interface with integrated Electron desktop application for native iOS simulator control.

#### 🚀 **Key Features**

**Desktop Streaming Window**
* **Native Application**: Full-featured Electron app with native window controls
* **High-Performance Streaming**: Real-time iOS simulator video streaming
* **Touch Controls**: Direct mouse/trackpad interaction with the simulator
* **Minimize/Close**: Functional window management buttons
* **Auto-Scaling**: Responsive simulator display that adapts to window size

**Advanced Input Methods**
* **Predefined Swipe Gestures**: Quick-access swipe buttons with dropdown menu
  - ⬆️ **Swipe Up**: Perfect for Control Center, app switching
  - ⬇️ **Swipe Down**: Notification Center, search
  - ⬅️ **Swipe Left**: Navigation, page transitions
  - ➡️ **Swipe Right**: Back navigation, page transitions
* **Dual Keyboard Modes**:
  - 📝 **Batch Mode**: Type text and send as complete messages
  - ⚡ **Real-time Mode**: Live key-by-key input with HID usage codes
* **Hardware Controls**: One-click access to device functions
  - 🏠 **Home Button**: Return to home screen
  - 🔒 **Lock Device**: Instant device lock/unlock
  - 📸 **Screenshot**: Capture and auto-download device screenshots

**Video Recording System**
* **Professional Recording**: MP4 video recording using `idb record-video`
* **Smart Controls**: 
  - 🔴 **Start Recording**: Begin video capture with visual feedback
  - ⏹️ **Stop Recording**: End recording and auto-download MP4 file
* **Emergency Safety**: Automatic recording preservation on app exit
* **Intelligent Naming**: `ios-recording_<session>_<timestamp>.mp4`

#### ⌨️ **Keyboard Shortcuts**

| Shortcut | Action | Description |
|----------|--------|-------------|
| **F1** | Home | Return to iOS home screen |
| **F2** | Screenshot | Capture and download screenshot |
| **F3** | Device Info | Show device information modal |
| **F4** | Toggle Keyboard | Open/close keyboard input panel |
| **F5** | Lock Device | Lock/unlock the iOS device |
| **F6** | Start Recording | Begin video recording |
| **F7** | Stop Recording | End recording and download video |

#### 🎛️ **Desktop Interface Features**

**Window Controls**
* **Draggable Header**: Native window drag functionality
* **Minimize Button**: Minimize app to dock/taskbar
* **Close Button**: Safe app closure with recording cleanup
* **Settings Menu**: Quality controls and configuration options

**Real-time Keyboard Panel**
* **Toggle Interface**: Slide-down keyboard input panel
* **Mode Switching**: Toggle between batch and real-time input modes
* **Visual Feedback**: Live keystroke confirmation and status
* **Auto-focus**: Intelligent input field focusing

**Recording Interface**
* **Status Indicators**: Visual recording state with pulsing animations
* **Button States**: Dynamic show/hide of start/stop controls
* **Progress Feedback**: Real-time recording status updates
* **Safe Termination**: Graceful recording stop on app exit

#### 📦 **CLI Installation & Usage**

**Installation**
```bash
# Install the iOS Bridge CLI
pip install ios-bridge-cli

# Or install from source
cd ios-bridge-cli
pip install -e .
```

**Basic Usage**
```bash
# Stream iOS simulator in desktop window
ios-bridge stream

# Stream with specific server configuration
ios-bridge stream --host localhost --port 8000

# Stream with session selection
ios-bridge stream --session-id <session-id>

# Start server (if not running)
ios-bridge server --port 8000
```

**Advanced CLI Options**
```bash
# Enable verbose logging
ios-bridge stream --verbose

# Custom server URL
ios-bridge stream --server-url http://localhost:8000

# Force specific session
ios-bridge stream --session-id abc123 --force

# Stream with recording auto-start
ios-bridge stream --auto-record
```

#### 🔧 **Desktop App Configuration**

**Settings Panel**
* **Video Quality**: Low, Medium, High, Ultra presets
* **Stream Mode**: WebSocket vs WebRTC selection
* **Recording Settings**: Default save location, quality settings
* **Keyboard Settings**: Real-time mode preferences

**Window Management**
* **Always on Top**: Keep app visible during development
* **Fullscreen Mode**: Immersive simulator interaction
* **Window Size Memory**: Remembers preferred window dimensions
* **Multi-Monitor Support**: Works across multiple displays

#### 🛡️ **Safety & Reliability**

**Graceful Shutdown**
* **Recording Protection**: Automatically stops and saves recordings on exit
* **Session Cleanup**: Proper WebSocket connection cleanup
* **Process Management**: Clean Electron process termination
* **Emergency Recovery**: Saves recordings to Downloads folder on forced exit

**Error Handling**
* **Connection Recovery**: Automatic reconnection on network issues
* **Session Validation**: Ensures valid session before connecting
* **Fallback Modes**: Graceful degradation when features unavailable
* **User Feedback**: Clear error messages and status indicators

#### 💡 **Use Cases**

**Development Workflow**
* **Live Testing**: Real-time app testing with immediate feedback
* **Screen Recording**: Capture demos and bug reports
* **Multiple Devices**: Quick switching between different iOS simulators
* **Gesture Testing**: Test swipe gestures and touch interactions

**Quality Assurance**
* **Test Documentation**: Record test sessions for review
* **Bug Reproduction**: Capture exact steps and interactions
* **Cross-Device Testing**: Test across multiple iOS device types
* **Automated Screenshots**: Quick capture for documentation

**Presentations & Demos**
* **Live Demos**: Present iOS apps in native desktop environment
* **Training Materials**: Record tutorials and walkthroughs
* **Client Presentations**: Professional app demonstrations
* **Documentation**: Create visual guides and tutorials
## 🏗️ Architecture

### Complete System Architecture

The iOS Bridge platform supports two main interface modes: **Web Interface** (browser-based) and **Desktop App** (Electron CLI-based). Both connect to the same FastAPI server backend.

#### **Desktop App Architecture (CLI + Electron)**

```
┌─────────────────┐    HTTP/REST     ┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Python CLI    │ ←──────────────→ │  FastAPI Server │ ←─────────────→ │ Electron Desktop│
│                 │                  │                 │                 │ Application     │
│ • Session List  │                  │ • Session Mgmt  │                 │                 │
│ • Validation    │                  │ • REST API      │                 │ • Video Stream  │
│ • App Launch    │                  │ • WebSocket Hub │                 │ • Touch Input   │
│ • Process Mgmt  │                  │ • Recording Svc │                 │ • Keyboard I/O  │
│ • Config Mgmt   │                  │ • Device Ctrl   │                 │ • Recording UI  │
└─────────────────┘                  └─────────────────┘                 │ • Gesture Ctrl  │
       ↓ IPC                                  ↓                           │ • Native UI     │
┌─────────────────┐                  ┌─────────────────┐                 └─────────────────┘
│ Electron Main   │                  │ Session Manager │
│   Process       │                  │                 │
│                 │                  │ • JSON Storage  │
│ • Window Mgmt   │                  │ • Validation    │
│ • Menu System   │                  │ • Recovery      │
│ • Lifecycle     │                  │ • Backup/Restore│
│ • Cleanup       │                  └─────────────────┘
│ • Signal Handle │                           ↓
└─────────────────┘                  ┌─────────────────┐
                                     │ iOS Sim Manager │
                                     │                 │
                                     │ • xcrun simctl  │
                                     │ • Device Control│
                                     │ • App Lifecycle │
                                     │ • Process Track │
                                     └─────────────────┘
                                              ↓
                                     ┌─────────────────┐
                                     │ IDB Integration │
                                     │                 │
                                     │ • Device Bridge │
                                     │ • HID Input     │
                                     │ • Video Record  │
                                     │ • File Transfer │
                                     └─────────────────┘
                                              ↓
                                     ┌─────────────────┐
                                     │ iOS Simulators  │
                                     │                 │
                                     │ • Multiple UDID │
                                     │ • Concurrent    │
                                     │ • Persistent    │
                                     └─────────────────┘
```

#### **Web Interface Architecture (Browser-based)**

```
┌─────────────────┐    HTTP/WebSocket   ┌─────────────────┐
│   Web Browser   │ ←─────────────────→ │  FastAPI Server │
│                 │                     │                 │
│ • HTML5 Canvas  │                     │ • Session Mgmt  │
│ • WebSocket JS  │                     │ • REST API      │
│ • Touch Events  │                     │ • WebSocket Hub │
│ • WebRTC        │                     │ • Video Stream  │
│ • File Upload   │                     │ • Control WS    │
│ • Responsive UI │                     │ • Screenshot WS │
└─────────────────┘                     │ • WebRTC WS     │
                                        └─────────────────┘
                                                 ↓
                                        ┌─────────────────┐
                                        │ WebSocket       │
                                        │ Services        │
                                        │                 │
                                        │ • VideoWebSocket│
                                        │ • ControlWS     │
                                        │ • ScreenshotWS  │
                                        │ • WebRTCWS      │
                                        └─────────────────┘
                                                 ↓
                                    [Same backend infrastructure as Desktop App]
```

#### **Unified Backend Infrastructure**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Server Core                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ REST Endpoints │ WebSocket Hub │ Session Manager │ Recording Service       │
│                │               │                 │                         │
│ • /api/sessions│ • Video Stream│ • JSON Storage  │ • idb record-video     │
│ • /api/apps    │ • Control I/O │ • Validation    │ • Emergency Save       │
│ • /api/recording│ • Screenshot │ • Recovery      │ • MP4 Download         │
│ • /health      │ • WebRTC      │ • Cleanup       │ • Process Management   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                        iOS Device Management Layer                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ iOS Simulator Manager │ Device Service │ IDB Integration │ System Utils    │
│                       │                │                 │                 │
│ • xcrun simctl        │ • Touch/Swipe  │ • Video Record  │ • Process Track │
│ • Device Create/Boot  │ • Button Press │ • HID Keyboard  │ • File Mgmt     │
│ • App Install/Launch  │ • Text Input   │ • Screenshot    │ • Cleanup       │
│ • UDID Management     │ • Coordinate   │ • Device Lock   │ • Error Handle  │
│ • State Monitoring    │   Translation  │ • File Transfer │ • Logging       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           macOS System Layer                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Xcode/iOS Simulator │ Facebook IDB │ FFmpeg │ System Commands              │
│                     │              │        │                              │
│ • Simulator Runtime │ • idb daemon │ • Video│ • Process Management         │
│ • Device Types      │ • Device Com │   Proc │ • File System Operations     │
│ • iOS Versions      │ • Automation │ • Stream│ • Network I/O                │
│ • Hardware Sim      │ • Testing    │   Enc  │ • Signal Handling            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Component Analysis

#### **Client Interface Components**

**1. Desktop Application (Electron + Python CLI)**
- **Python CLI Layer**: Command-line interface using Click framework
  - Session validation and API client communication
  - Electron app lifecycle management and process spawning
  - Configuration handling and environment setup
  - Graceful shutdown and cleanup orchestration
  
- **Electron Main Process**: Native desktop window management
  - Window creation, resizing, and lifecycle management
  - Menu system with keyboard shortcuts (F1-F7)
  - IPC communication between main and renderer processes
  - Signal handling for clean app termination
  
- **Electron Renderer Process**: Real-time UI and streaming
  - WebSocket client for video streaming and device control
  - HTML5 Canvas for hardware-accelerated video rendering
  - Touch input translation (mouse coordinates → device coordinates)
  - Real-time keyboard input with HID usage code mapping
  - Recording controls with start/stop and emergency save
  - Gesture controls with predefined swipe directions
  
**2. Web Interface (Browser-based)**
- **Frontend JavaScript**: Vanilla JS for maximum performance
  - WebSocket client management with auto-reconnection
  - Canvas-based video rendering with frame queuing
  - Touch event handling and coordinate mapping
  - WebRTC support for low-latency streaming
  - Responsive design for various screen sizes
  
- **HTML5 Interface**: Modern web standards
  - Semantic HTML5 structure with accessibility support
  - CSS Grid/Flexbox for responsive layout
  - Progressive Web App (PWA) capabilities
  - File upload for IPA installation

#### **Server Infrastructure Components**

**FastAPI Application Core (`main.py`)**
- **Application Lifespan**: Startup/shutdown hooks with graceful cleanup
- **Orphaned Recovery**: Automatic detection and session restoration on startup
- **WebSocket Hub**: Centralized management of multiple WebSocket endpoints
- **Session-aware Routing**: All operations scoped to specific simulator sessions
- **Health Monitoring**: Comprehensive health checks and status endpoints
- **Error Handling**: Global exception handling with detailed error reporting

**Session Management Layer (`session_manager.py`)**
- **Persistent Storage**: JSON-based session storage with atomic writes
- **Validation Engine**: Real-time session health checks and validation
- **Recovery System**: Automatic orphaned simulator detection and session restoration
- **Concurrency Support**: Thread-safe operations for multiple concurrent sessions
- **Backup System**: Automated backup rotation with configurable retention
- **Hot Reload**: Development-friendly session persistence across server restarts

**iOS Simulator Management (`ios_sim_manager_service.py`)**
- **Device Lifecycle**: Complete simulator management (create, boot, shutdown, delete)
- **App Management**: IPA installation with automatic simulator compatibility fixes
- **Process Monitoring**: PID tracking and process health monitoring
- **Device Control**: Integration with `xcrun simctl` for hardware simulation
- **State Synchronization**: Real-time device state monitoring and updates
- **Error Recovery**: Comprehensive error handling with automatic retry logic

**Recording Service (`recording_service.py`)**
- **Video Recording**: MP4 recording using `idb record-video` with quality settings
- **Process Management**: Graceful recording start/stop with SIGTERM handling
- **Emergency Save**: Automatic recording preservation on unexpected app termination
- **File Management**: Temporary file handling with automatic cleanup
- **Download System**: Secure file download with automatic post-download cleanup

**WebSocket Services Hub**
- **ControlWebSocket**: Real-time device control and input handling
  - Touch events (tap, swipe) with coordinate translation
  - Keyboard input with HID usage code mapping
  - Hardware button simulation (home, lock, volume)
  - Text input forwarding with encoding support
- **VideoWebSocket**: High-performance video streaming
  - Base64 JPEG frame encoding with metadata
  - Dynamic quality adjustment and frame rate control
  - Frame queuing and buffer management
- **WebRTCWebSocket**: Low-latency streaming for modern browsers
  - Peer-to-peer connection establishment
  - Adaptive bitrate and quality control
  - ICE candidate handling and connection management
- **ScreenshotWebSocket**: High-quality screenshot capture
  - On-demand screenshot generation
  - Multiple format support (PNG, JPEG)
  - Compression and quality optimization

#### **Device Integration Layer**

**Device Service (`device_service.py`)**
- **Input Translation**: Coordinate mapping for different device types and orientations
- **Gesture Processing**: Complex gesture recognition and execution
- **Hardware Simulation**: Complete hardware button and sensor simulation
- **Text Processing**: Unicode text input with proper encoding
- **Response Handling**: Asynchronous command execution with error handling

**IDB Integration**
- **Device Bridge**: Facebook IDB for advanced device automation
- **HID Input**: Hardware-level keyboard input using HID usage codes
- **Video Recording**: Professional-quality MP4 recording
- **File Transfer**: Bidirectional file transfer capabilities
- **Device Lock**: Secure device lock/unlock functionality

#### **System Integration**

**macOS System Layer**
- **Xcode Integration**: Deep integration with iOS Simulator runtime
- **Process Management**: System-level process tracking and cleanup
- **File System**: Secure file operations with proper permissions
- **Network Stack**: WebSocket and HTTP server with SSL/TLS support

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

**Video Recording**
```bash
# Start recording
POST /api/sessions/{session_id}/recording/start

# Stop recording and download MP4
POST /api/sessions/{session_id}/recording/stop

# Get recording status
GET /api/sessions/{session_id}/recording/status

# Cleanup all recordings (emergency stop)
POST /api/sessions/cleanup-recordings
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

// Send individual key presses (real-time keyboard)
controlSocket.send(JSON.stringify({
    type: 'key',
    key: '11' // HID usage code for 'H'
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

**7. Electron Desktop App issues**
```bash
# Common issues:
# - WebSocket connection failures
# - Recording not starting/stopping
# - Keyboard input not working

# Check server connection
curl "http://localhost:8000/health"

# Verify recording endpoints
curl -X POST "http://localhost:8000/api/sessions/{session_id}/recording/start"

# Check real-time keyboard mode
# Ensure HID usage codes are being sent correctly
```

**8. Video recording problems**
```bash
# Recording not stopping on app exit
# - Check idb process: ps aux | grep idb
# - Manually kill if needed: killall -TERM idb

# Recording file not found
# - Check Downloads folder for emergency saves
# - Look for files named: ios-recording-emergency_*

# Recording permission issues
# - Ensure idb has proper permissions
# - Check iOS Simulator accessibility settings
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

# Check recording status
curl "http://localhost:8000/api/sessions/{session_id}/recording/status"

# Emergency stop all recordings
curl -X POST "http://localhost:8000/api/sessions/cleanup-recordings"

# Test swipe gestures
curl -X POST "http://localhost:8000/ws/{session_id}/control" \
  -d '{"t":"swipe","start_x":195,"start_y":500,"end_x":195,"end_y":300,"duration":0.3}'

# Test key input (real-time keyboard)
curl -X POST "http://localhost:8000/ws/{session_id}/control" \
  -d '{"t":"key","key":"11"}' # HID code for 'H'
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
