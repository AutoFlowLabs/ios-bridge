
# 🎮 iOS Simulator Remote Control Platform

A comprehensive remote control solution for iOS simulators, providing real-time streaming, device interaction, and app management capabilities through a modern web interface.



## 📋 Table of Contents
* Overview
* Features
* Architecture
* Installation
* Usage
* API Reference
* Frontend Features
* Backend Architecture
* Technical Stack
* Configuration
* Troubleshooting
* Contributing
## 🌟 Overview

This project provides a complete remote control solution for iOS simulators, enabling developers and testers to interact with iOS devices through a web browser. It combines real-time video streaming, gesture controls, app management, and file operations in a unified platform.


## Key Capabilities

* Real-time simulator streaming with WebSocket-based video feed
* Interactive touch controls (tap, swipe, gestures)
* App lifecycle management (install, launch, uninstall)
* File system operations (push/pull files)
* Hardware button simulation (home, lock, volume, etc.)
* Session persistence across server restarts
* Multi-simulator support with hot-reload capabilities
## ✨ Features

### 🎯 Core Features

**Simulator Management**

* Multi-simulator support: Create and manage multiple iOS simulator sessions
* Session persistence: Simulators remain active across server restarts
* Hot reload: Development server restarts without killing simulators
* Device configuration: Support for all iOS device types and versions
* Automatic discovery: Detect existing simulator sessions on startup

**Interactive Controls**

* Touch interactions: Precise tap and swipe gestures
* Hardware buttons: Home, lock, volume, Siri, Apple Pay, shake
* Text input: Send text directly to simulator
* Gesture modes: Toggle between tap and swipe modes
* Keyboard shortcuts: Quick access to common functions


### 🚀 Advanced Features

**App Management**

* IPA installation: Automatic app installation with simulator compatibility fixes
* Bundle modification: Auto-modify apps for simulator compatibility
* Launch management: Launch apps with custom arguments
* App lifecycle: Install, launch, terminate, uninstall operations
* Debug information: Comprehensive app installation diagnostics

**File Operations**

* File transfer: Push/pull files between host and simulator
* Media management: Add photos and videos to simulator
* Container access: Direct access to app containers and documents
* Backup operations: Extract app data and logs

**Development Tools**

* Debug endpoints: Direct API access for automation
* Log extraction: Real-time app and system logs
* Health monitoring: System status and performance metrics
* Error handling: Comprehensive error reporting and recovery
## 🏗️ Architecture

### System Overview

```
┌─────────────────┐    WebSocket/HTTP    ┌─────────────────┐
│   Web Frontend  │ ←→ ←→ ←→ ←→ ←→ ←→ │  FastAPI Server │
│                 │                     │                 │
│ • Video Stream  │                     │ • Session Mgmt  │
│ • Touch Input   │                     │ • App Control   │
│ • Controls UI   │                     │ • File Ops      │
└─────────────────┘                     └─────────────────┘
                                                 ↓
                                        ┌─────────────────┐
                                        │ iOS Simulator   │
                                        │ Manager         │
                                        │                 │
                                        │ • simctl        │
                                        │ • ffmpeg        │
                                        │ • Session Store │
                                        └─────────────────┘
                                                 ↓
                                        ┌─────────────────┐
                                        │ iOS Simulators  │
                                        │                 │
                                        │ • Device 1      │
                                        │ • Device 2      │
                                        │ • Device N      │
                                        └─────────────────┘
                                        
```

### Component Breakdown

**Frontend Components**

* Video Canvas: Real-time rendering with hardware acceleration
* Control Panel: Organized sections for different control types
* WebSocket Clients: Separate connections for video and control
* Responsive Design: Adaptive layout for different screen sizes

**Backend Services**

* FastAPI Server: Modern async web framework
* WebSocket Handlers: Real-time communication endpoints
* Session Storage: JSON-based persistent session management
* Simulator Manager: Core simulator lifecycle management


## 🎯 Usage

### Basic Workflow

1. Start the server: Run python main.py
2. Access the web interface: Open http://localhost:5002
3. The system will automatically:
* Detect existing simulators or create a new one
* Start video streaming
* Enable interactive controls

### Web Interface Guide

**Stream Modes**
* 🎥 Video Mode: Real-time streaming for interactive testing
* 📷 Screenshot Mode: High-quality static images for detailed inspection

**Control Sections**

* 📱 Stream Mode: Switch between video and screenshot modes
* 🎮 System Controls: Restart, status check, refresh, test functions
* 🔘 Hardware Buttons: Home, lock, volume, Siri, Apple Pay, shake
* 👆 Gesture Controls: Tap/swipe mode toggle and directional swipes
* ⌨️ Text Input: Send text directly to the simulator
* ⌨️ Keyboard Shortcuts: Quick access hotkeys

**Keyboard Shortcuts**
* H - Home button
* L - Lock device
* S - Activate Siri
* P - Apple Pay
* +/- - Volume up/down
* K - Shake device
* Space - Toggle swipe mode
* Arrow Keys - Quick directional swipes
* Enter - Send text input

## 🔧 API Reference

### REST Endpoints

**Session Management**
```
GET /sessions
# Returns list of active simulator sessions

GET /session/{session_id}
# Get detailed session information

POST /session/create
# Create new simulator session
```

**App Management**
```
POST /install/{session_id}
# Install IPA file to simulator

POST /launch/{session_id}/{bundle_id}
# Launch installed app

DELETE /uninstall/{session_id}/{bundle_id}
# Uninstall app from simulator
```

**File Operations**
```
POST /push/{session_id}
# Push file to simulator

POST /pull/{session_id}
# Pull file from simulator

GET /logs/{session_id}/{bundle_id}
# Get app logs
```

**Debug Endpoints**
```
GET /debug/tap/{x}/{y}
# Send tap at coordinates

GET /debug/volume-up
GET /debug/volume-down
# Volume controls

GET /debug/shake
# Shake device

GET /status
# System health check
```

### WebSocket Endpoints

**Video Streaming**
```
ws://localhost:5002/ws/video
// High-performance video stream
// Receives: { type: 'video_frame', data: 'base64...', width: 390, height: 844 }
```

**Screenshot Mode**
```
ws://localhost:5002/ws/screenshot
// On-demand high-quality screenshots
// Receives: { type: 'screenshot', data: 'base64...', width: 1170, height: 2532 }
```

**Control Channel**
```
ws://localhost:5002/ws/control
// Send touch and gesture commands
// Send: { t: 'tap', x: 195, y: 422 }
// Send: { t: 'swipe', start_x: 100, start_y: 400, end_x: 300, end_y: 400, duration: 0.3 }
// Send: { t: 'button', button: 'home' }
// Send: { t: 'text', text: 'Hello World' }
```



## 🎨 Frontend Features

### Visual Design

* Modern UI: Clean, professional interface with iOS-inspired design
* Responsive Layout: Adapts to desktop, tablet, and mobile screens
* Real-time Feedback: Status updates and confirmation messages
* Performance Indicators: FPS counters and connection status

### Interaction Features
* Precise Touch Mapping: Accurate coordinate translation between display and device
* Gesture Recognition: Support for complex touch interactions
* Visual Feedback: Immediate response to user actions
* Error Handling: Graceful degradation and error recovery

### Technical Implementation
* Canvas Rendering: Hardware-accelerated video display
* WebSocket Management: Automatic reconnection and failover
* Performance Optimization: Frame dropping and quality adaptation
* Memory Management: Efficient resource usage and cleanup


## ⚙️ Backend Architecture

### Core Components

**EnhancediOSSimulatorManager**
* Session Management: Create, track, and destroy simulator sessions
* Device Control: Interface with iOS Simulator via simctl
* App Lifecycle: Install, launch, and manage applications
* File Operations: Push/pull files to/from simulator

**SessionStorage**
* Persistence: JSON-based session storage across restarts
* Recovery: Automatic session restoration on startup
* Cleanup: Orphaned session detection and cleanup

**Streaming Services**
* Video Streamer: Real-time frame capture and encoding
* Screenshot Service: High-quality static image capture
* WebSocket Handlers: Bidirectional communication channels

### Technical Features

**Performance Optimizations**
* Async Architecture: Non-blocking I/O for concurrent operations
* Frame Caching: Intelligent frame buffering and delivery
* Quality Adaptation: Dynamic resolution and framerate adjustment
* Resource Pooling: Efficient resource reuse and management

**Error Handling**
* Graceful Degradation: Fallback mechanisms for failed operations
* Retry Logic: Automatic retry for transient failures
* Logging: Comprehensive error logging and diagnostics
* Recovery: Automatic recovery from common failure scenarios

**Security Features**
* CORS Protection: Configurable cross-origin restrictions
* Input Validation: Sanitization of user inputs
* Rate Limiting: Protection against abuse and overload
* Session Isolation: Secure separation between simulator sessions
## 🛠️ Technical Stack

### Frontend Technologies

* HTML5 Canvas: Hardware-accelerated rendering
* WebSocket API: Real-time bidirectional communication
* CSS Grid/Flexbox: Responsive layout system
* Vanilla JavaScript: No framework dependencies for maximum performance

### Backend Technologies
 
**Web Framework & Server**
* FastAPI - Modern Python async web framework with automatic API documentation
    * Async/await support for high-performance concurrent operations
    * Built-in WebSocket support for real-time communication
    * Automatic request/response validation and serialization
* Uvicorn - Lightning-fast ASGI server with hot reload capabilities
* Starlette - FastAPI's underlying framework for WebSocket handling

**Async & Concurrency**
* asyncio - Python's native async library for concurrent operations
* ThreadPoolExecutor - Multi-threaded screenshot processing
* WebSocket Connections - Multiple concurrent client support
* Threading - Thread-safe caching and resource management

**System Integration Tools**
* idb (iOS DeviceBoard) - Facebook's advanced iOS debugging and automation tool
    * UI interaction (idb ui tap, idb ui swipe, idb ui button)
    * Screenshot capture (idb screenshot)
    * Device information (idb describe)
    * Text input (idb ui text)
* subprocess - System command execution with timeout handling
* xcrun simctl - Apple's iOS Simulator command-line interface (fallback for volume/shake)

**Performance & Caching**
* Multi-level Caching System:
    * Screenshot cache with 16ms refresh rate (60 FPS target)
    * Point dimensions cache (60-second TTL)
    * Thread-safe locking mechanisms
* Frame Rate Control - Dynamic FPS adjustment (target: 30 FPS)
* Memory Management - Automatic cleanup and resource pooling
