# iOS Bridge

**Complete iOS Simulator Remote Control Platform** - Stream, control, and automate iOS simulators from anywhere.

iOS Bridge is a comprehensive remote control solution that enables developers to stream iOS simulators to any device with full touch interaction, app management, and video recording capabilities. Perfect for cross-platform development teams, remote work, and iOS app testing.

## What iOS Bridge Provides

🖥️ **Desktop Streaming** - Native desktop apps for Windows, Linux, and macOS  
🌐 **Web Interface** - Browser-based control with no installation required  
🎮 **Complete Touch Control** - Click, swipe, type, and gesture naturally  
📱 **Real Device Experience** - Home button, screenshots, app installation  
🚀 **Cross-Platform Access** - Stream from Mac to any platform  
⚡ **High Performance** - WebRTC and WebSocket streaming options

## Project Architecture

iOS Bridge consists of three main components that work together:

```
┌─────────────────┐    HTTP/WebSocket    ┌─────────────────┐    simctl/idb    ┌─────────────────┐
│   iOS Bridge    │ ←─────────────────→ │  FastAPI Server │ ←─────────────→ │ iOS Simulators  │
│    Clients      │                     │                 │                  │                 │
│                 │                     │ • Session Mgmt  │                  │ • Multiple UDIDs│
│ • Desktop Apps  │                     │ • WebSocket Hub │                  │ • Concurrent    │
│ • Web Interface │                     │ • REST API      │                  │ • Persistent    │
│ • CLI Tools     │                     │ • Recording     │                  │ • Automated     │
└─────────────────┘                     └─────────────────┘                  └─────────────────┘
```

## Components Overview

### 1. 🖥️ iOS Bridge CLI & Desktop App

**Location**: [`ios-bridge-cli/`](ios-bridge-cli/)

A powerful Python CLI with integrated Electron desktop application providing native iOS simulator control.

**Key Features:**
- 📦 **Easy Installation**: `pip install ios-bridge-cli`
- 🖥️ **Native Desktop App**: Cross-platform Electron client
- ⚡ **Zero Configuration**: Automatic server management
- 🎯 **Session Management**: Create, list, and control iOS simulators
- 🔄 **Auto-Detection**: Smart session discovery

**Quick Start:**
```bash
# Install the CLI
pip install ios-bridge-cli

# On macOS (local server + client)
ios-bridge create "iPhone 15 Pro" "18.2" --wait
ios-bridge stream

# On Windows/Linux (remote client with full features)
ios-bridge connect http://MAC-IP:8000 --save
ios-bridge create "iPhone 15 Pro" "18.2" --wait  # Full session management
ios-bridge stream                                 # Full streaming & control
```
*Note: Server hosting requires macOS + Xcode. Windows/Linux clients have full feature parity when connected.*

**Perfect For:**
- Individual developers wanting desktop iOS simulator access
- Quick testing and development workflows
- Cross-platform teams (Mac server → Windows/Linux clients)

### 2. 🌐 FastAPI Server (Core Engine)

**Location**: [`app/`](app/)

The heart of iOS Bridge - a FastAPI-based server that manages iOS simulators and provides real-time streaming.

**Key Features:**
- 🏗️ **FastAPI Backend**: Modern async web framework
- 📱 **Simulator Management**: Complete lifecycle control via `xcrun simctl`
- 🔌 **WebSocket Streaming**: Real-time video and control
- 🚀 **WebRTC Support**: Ultra-low latency streaming
- 💾 **Session Persistence**: Survives server restarts
- 🔄 **Auto-Recovery**: Detects orphaned simulators

**Core Capabilities:**
- Session management with JSON storage
- App installation and lifecycle control
- Video recording with MP4 download
- Multi-client WebSocket support
- RESTful API with automatic documentation

**Perfect For:**
- Server deployment for team access
- Custom integration and automation
- Building on top of iOS Bridge platform

### 3. 🌐 Web Interface

**Location**: [`templates/`](templates/) and [`static/`](static/)

A modern web interface that provides iOS simulator control directly in your browser.

**Key Features:**
- 🌐 **Browser-Based**: No installation required
- 📱 **Responsive Design**: Works on desktop and mobile
- 🎮 **Full Touch Control**: Native gesture support
- 📦 **App Management**: Drag-and-drop IPA installation
- 🎥 **Recording Controls**: Start/stop video recording
- 🔄 **Stream Modes**: WebSocket and WebRTC options

**Access Points:**
- **Main Dashboard**: `http://localhost:8000`
- **Session Control**: `http://localhost:8000/control/{session-id}`
- **Direct Web Client**: `http://localhost:8000/web/{session-id}`

**Perfect For:**
- Team collaboration and sharing
- Remote access without app installation
- Mobile access to iOS simulators
- Quick testing and demonstrations

## Quick Start Guide

### 1. For Individual Developers (CLI + Desktop App)

**On macOS (Local Server + Client):**
```bash
# Install the CLI
pip install ios-bridge-cli

# Create and stream an iOS session (server starts automatically)
ios-bridge create "iPhone 15 Pro" "18.2" --wait
ios-bridge stream
```

**On Windows/Linux (Remote Client with Full Features):**
```bash
# Install the CLI
pip install ios-bridge-cli

# Connect to Mac server (replace MAC-IP with actual Mac IP address)
ios-bridge connect http://MAC-IP:8000 --save

# Full session management via remote server
ios-bridge create "iPhone 15 Pro" "18.2" --wait  # Create sessions
ios-bridge list                                   # List sessions
ios-bridge stream                                 # Stream to desktop
ios-bridge terminate <session-id>                # Terminate sessions
```

> **⚠️ Note**: Server hosting requires macOS + Xcode. Windows/Linux clients have **full functionality** when connected to Mac server including session creation, management, streaming, and app control.

### 2. For Teams (Server + Web Interface)

**Mac Server Setup:**
```bash
# Install iOS Bridge CLI (includes server)
pip install ios-bridge-cli

# Start server for team access
ios-bridge start-server --host 0.0.0.0 --port 8000
```

**Team Access:**
- **Web Interface**: `http://MAC-IP:8000`
- **Desktop Clients**: `ios-bridge connect http://MAC-IP:8000 --save`

### 3. For Custom Integration (API)

```bash
# Start the server
pip install ios-bridge-cli
ios-bridge start-server --background

# Create session via API
curl -X POST "http://localhost:8000/api/sessions/create" \
  -d "device_type=iPhone 15 Pro&ios_version=18.2"

# Connect to WebSocket for control
ws://localhost:8000/ws/{session-id}/control
```

## Installation & Setup

### Requirements

- **macOS**: Required for iOS simulator server
- **Python 3.8+**: For CLI and server components
- **Xcode**: iOS Simulator runtime and tools
- **Node.js**: For desktop app development (optional)

### Option 1: CLI Only (Recommended)

```bash
pip install ios-bridge-cli
ios-bridge create "iPhone 15 Pro" "18.2" --wait
ios-bridge stream
```

### Option 2: Team Server Setup

```bash
# Install iOS Bridge CLI (includes all dependencies)
pip install ios-bridge-cli

# Install additional tools for advanced features
brew install ffmpeg idb-companion
pip install fb-idb

# Start server for team access
ios-bridge start-server --host 0.0.0.0 --port 8000
```

### Option 3: Development Setup (Advanced)

*Only needed for contributing to iOS Bridge or custom server modifications*

```bash
# Clone repository for development
git clone <repo-url>
cd ios-bridge

# Server development with hot reload
pip install -r requirements.txt
PYTHONPATH=$(pwd) uvicorn app.main:app --reload

# Desktop app development
cd ios-bridge-cli/ios_bridge_cli/electron_app
npm install
npm run dev
```

## Platform Compatibility

| Component | macOS | Windows | Linux | iOS/Android |
|-----------|:-----:|:-------:|:-----:|:-----------:|
| **FastAPI Server** | ✅ Host Only | ❌ No Server | ❌ No Server | ❌ |
| **CLI Client** | ✅ Local + Remote | ✅ Remote Full | ✅ Remote Full | ❌ |
| **Desktop App** | ✅ Local + Remote | ✅ Remote Full | ✅ Remote Full | ❌ |
| **Web Interface** | ✅ Local + Remote | ✅ Remote Full | ✅ Remote Full | ✅ Mobile |

**Capabilities when connected to Mac server:**
- ✅ **Create/Delete Sessions** - Full session lifecycle management
- ✅ **Stream & Control** - Desktop app and web interface streaming  
- ✅ **App Management** - Install, launch, terminate iOS apps
- ✅ **All Features** - Complete feature parity with local Mac usage

*Server hosting requires macOS + Xcode for iOS Simulator access*

## Core Features

### Session Management
- **Persistent Sessions**: Simulators survive server restarts
- **Multi-Simulator**: Run multiple iOS devices simultaneously  
- **Auto-Recovery**: Detect and reconnect orphaned simulators
- **Hot Reload**: Development-friendly session persistence

### Device Control
- **Touch Input**: Precise tap, swipe, and gesture controls
- **Hardware Buttons**: Home, lock, volume, Siri, Apple Pay
- **Keyboard Input**: Real-time typing with HID support
- **Text Input**: Bulk text insertion

### Streaming & Recording
- **Multiple Modes**: WebSocket and WebRTC streaming
- **Quality Control**: Low, medium, high, ultra presets
- **Video Recording**: MP4 recording with download
- **Screenshot Capture**: High-quality static images

### App Management
- **IPA Installation**: Automatic simulator compatibility
- **App Lifecycle**: Install, launch, terminate, uninstall
- **Bundle Processing**: Code signing and compatibility fixes

## API Reference

### REST Endpoints

#### Session Management
```bash
# Core Session Operations
GET    /api/sessions/configurations      # Get available device types and iOS versions
POST   /api/sessions/create              # Create new simulator session
GET    /api/sessions/                    # List all active sessions
GET    /api/sessions/{id}                # Get detailed session information
DELETE /api/sessions/{id}                # Delete simulator session
DELETE /api/sessions/                    # Delete all simulator sessions

# Session Management
GET    /api/sessions/refresh             # Refresh session states
POST   /api/sessions/recover-orphaned    # Recover orphaned simulators
POST   /api/sessions/cleanup             # Clean up old storage files
GET    /api/sessions/storage/info        # Get session storage information
```

#### App Management
```bash
# App Installation and Control
POST   /api/sessions/{id}/apps/install           # Install IPA/ZIP app
POST   /api/sessions/{id}/apps/install-and-launch # Install and launch immediately
GET    /api/sessions/{id}/apps                   # List installed apps
POST   /api/sessions/{id}/apps/{bundle}/launch   # Launch specific app
POST   /api/sessions/{id}/apps/{bundle}/terminate # Terminate specific app
DELETE /api/sessions/{id}/apps/{bundle}          # Uninstall app
```

#### Device Controls
```bash
# Device Interaction
POST   /api/sessions/{id}/screenshot/download    # Take and download screenshot
GET    /api/sessions/{id}/screenshot             # Take screenshot (return as response)
POST   /api/sessions/{id}/orientation            # Change simulator orientation
POST   /api/sessions/{id}/url/open               # Open URL on simulator
GET    /api/sessions/{id}/url/schemes            # Get supported URL schemes
```

#### Location Services
```bash
# GPS and Location
POST   /api/sessions/{id}/location/set           # Set custom GPS coordinates
POST   /api/sessions/{id}/location/clear         # Clear mock location
GET    /api/sessions/{id}/location/presets       # Get predefined locations
POST   /api/sessions/{id}/location/set-predefined # Set predefined location
```

#### Media and File Management
```bash
# Media Operations
POST   /api/sessions/{id}/media/photos/add       # Add photos to simulator
POST   /api/sessions/{id}/media/videos/add       # Add videos to simulator
GET    /api/sessions/{id}/media/info             # Get supported media formats

# File Operations
POST   /api/sessions/{id}/files/push             # Push file to simulator
POST   /api/sessions/{id}/files/pull             # Pull file from simulator
GET    /api/sessions/{id}/files/app-container    # Get app container path
```

#### Logging and Debugging
```bash
# Logging
GET    /api/sessions/{id}/logs                   # Get recent simulator logs
POST   /api/sessions/{id}/logs/clear             # Clear simulator logs
GET    /api/sessions/{id}/logs/processes         # Get list of logging processes

# Debug Endpoints
GET    /debug/screenshot/{id}                    # Debug screenshot capture
GET    /debug/tap/{id}/{x}/{y}                   # Debug tap action
GET    /debug/home/{id}                          # Debug home button
```

#### Recording
```bash
# Video Recording
POST   /api/sessions/{id}/recording/start        # Start video recording
POST   /api/sessions/{id}/recording/stop         # Stop recording and download
GET    /api/sessions/{id}/recording/status       # Get recording status
POST   /api/sessions/cleanup-recordings          # Emergency cleanup all recordings
```

#### System and Status
```bash
# Health and Status
GET    /health                                   # Health check with stats
GET    /stats                                    # Detailed connection stats
GET    /status/{id}                              # Get session status
GET    /webrtc/quality/{id}/{quality}            # Set WebRTC quality (low/medium/high/ultra)
```

### WebSocket Endpoints

#### Control WebSocket (`/ws/{session-id}/control`)
```javascript
// Touch Controls
controlSocket.send(JSON.stringify({
    "t": "tap",
    "x": 195,
    "y": 422
}));

// Swipe Gestures
controlSocket.send(JSON.stringify({
    "t": "swipe",
    "start_x": 100,
    "start_y": 400,
    "end_x": 300,
    "end_y": 400,
    "duration": 0.2
}));

// Hardware Buttons
controlSocket.send(JSON.stringify({
    "t": "button",
    "button": "home" // home|lock|siri|side-button|apple-pay
}));

// Text Input
controlSocket.send(JSON.stringify({
    "t": "text",
    "text": "Hello World"
}));

// Individual Key Presses
controlSocket.send(JSON.stringify({
    "t": "key",
    "key": "RETURN", // RETURN|SPACE|DELETE|etc
    "duration": 0.1
}));
```

#### Video Streaming WebSocket (`/ws/{session-id}/video`)
```javascript
// Real-time video frames with metadata
videoSocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    // data.frame: base64 encoded image
    // data.width, data.height: frame dimensions
    // data.fps, data.timestamp: performance info
};
```

#### WebRTC WebSocket (`/ws/{session-id}/webrtc`)
```javascript
// Start WebRTC streaming
webrtcSocket.send(JSON.stringify({
    "type": "start-stream",
    "quality": "high", // low|medium|high|ultra
    "fps": 60
}));

// Quality control
webrtcSocket.send(JSON.stringify({
    "type": "quality-change",
    "quality": "ultra"
}));

// FPS control
webrtcSocket.send(JSON.stringify({
    "type": "fps-change",
    "fps": 90
}));
```

#### Screenshot WebSocket (`/ws/{session-id}/screenshot`)
```javascript
// On-demand screenshot capture
screenshotSocket.send(JSON.stringify({
    "t": "refresh"
}));

// Auto-refresh on tap
screenshotSocket.send(JSON.stringify({
    "t": "tap",
    "x": 195,
    "y": 422
}));
```

#### Logs WebSocket (`/ws/{session-id}/logs`)
```javascript
// Real-time log filtering
logsSocket.send(JSON.stringify({
    "type": "filter",
    "filter": "search_term",
    "level": "error" // error|warning|info|debug
}));
```

## Backend Features

### Device Control Capabilities
- **Touch Gestures**: Precise tap and swipe with customizable duration and coordinates
- **Hardware Buttons**: Complete hardware simulation including:
  - Home button, Lock/Sleep button, Side button
  - Siri activation, Apple Pay simulation
  - Volume up/down controls
- **Keyboard Input**: 
  - Real-time individual key presses with HID codes
  - Bulk text input with Unicode support
  - Special keys: RETURN, SPACE, DELETE, arrow keys
- **Device Orientation**: Portrait, landscape, portrait upside down, landscape left/right

### Location Services
- **Custom GPS Coordinates**: Set any latitude/longitude combination
- **Predefined Locations**: Built-in presets including:
  - Apple Park (Cupertino, CA)
  - Major world cities (San Francisco, New York, London, Tokyo, Sydney)
  - Activity presets (City Bicycle Ride, City Run, Freeway Drive)
- **Location Simulation**: Realistic GPS simulation for location-based app testing

### Media and File Management
- **Photo Library**: Add images to simulator photo library
  - Supported formats: JPG, JPEG, PNG, GIF, HEIC, HEIF
  - Batch upload support
- **Video Library**: Add videos to simulator video library
  - Supported formats: MP4, MOV, M4V, AVI, MKV
- **File Transfer**: Bidirectional file operations
  - Push files to simulator file system
  - Pull files from simulator
  - App container access for app-specific files

### Logging and Debugging
- **Real-time Logs**: Live log streaming from iOS Simulator
- **Log Filtering**: Filter by log level (error, warning, info, debug)
- **Process Monitoring**: Track specific app processes
- **Debug Endpoints**: Direct testing of device functions
- **Comprehensive Error Handling**: Detailed error reporting and graceful degradation

### Session Management
- **Persistent Storage**: JSON-based session storage with atomic writes
- **Orphaned Recovery**: Automatic detection and recovery of running simulators
- **Multi-Session Support**: Concurrent management of multiple iOS simulators
- **Hot Reload**: Development-friendly session persistence across server restarts
- **Session Validation**: Real-time health checks and cleanup

### Streaming and Recording
- **Multiple Streaming Modes**:
  - WebSocket-based video streaming with configurable quality
  - WebRTC ultra-low latency streaming with adaptive bitrate
  - Screenshot mode for high-quality static captures
- **Quality Presets**: Low, Medium, High, Ultra with different resolutions and FPS
- **Video Recording**: Full session recording with MP4 export
- **Emergency Recording Save**: Automatic recording preservation on unexpected termination

### Performance and Reliability
- **Connection Management**: Rate limiting and connection tracking
- **Resource Monitoring**: Memory usage and performance metrics
- **Automatic Cleanup**: Background cleanup of resources and temporary files
- **Health Monitoring**: Comprehensive health checks and status reporting
- **Graceful Shutdown**: Clean termination with proper resource cleanup

### Security Features
- **Session Isolation**: Each simulator session is completely isolated
- **Secure File Operations**: Safe file transfer with validation
- **Process Sandboxing**: Proper process management and security
- **Error Sanitization**: Safe error reporting without sensitive information exposure

### Integration Capabilities
- **REST API**: Complete RESTful API for all operations
- **WebSocket Real-time**: Bidirectional real-time communication
- **CLI Integration**: Seamless integration with command-line tools
- **Web Interface**: Browser-based control with no installation required

## Common Use Cases

### Development Teams
- **QA Testing**: Windows/Linux testers access Mac-hosted simulators
- **Remote Work**: Develop on Mac, test from anywhere via web
- **Code Reviews**: Share live iOS sessions for collaborative debugging

### Individual Developers  
- **Multi-Monitor**: Stream simulator to second display
- **Screen Recording**: Capture iOS interactions for tutorials
- **Cross-Platform**: Test iOS apps while working on Windows/Linux

### Enterprise
- **CI/CD Integration**: Automated iOS testing in build pipelines
- **Remote Support**: Support team access to customer iOS environments
- **Training**: Interactive iOS training without physical devices

## Documentation

- **[CLI Documentation](ios-bridge-cli/README.md)** - Complete CLI usage guide
- **[Desktop App README](ios-bridge-cli/ios_bridge_cli/electron_app/README.md)** - Electron desktop app overview
- **[Desktop App Development](ios-bridge-cli/ios_bridge_cli/electron_app/DEVELOPMENT.md)** - Electron app development guide
- **[Desktop App Commands](ios-bridge-cli/ios_bridge_cli/electron_app/DEV-COMMANDS.md)** - Quick development commands
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when server running)
- **[Cross-Platform Setup](CROSS_PLATFORM_SETUP.md)** - Team deployment guide

## Advanced Features

### WebRTC Streaming
- Ultra-low latency video streaming
- Adaptive quality based on network conditions
- Peer-to-peer connections for optimal performance
- Real-time toggle between WebSocket and WebRTC modes

### Session Persistence
- JSON-based session storage with atomic writes
- Automatic backup rotation and recovery
- Orphaned simulator detection and restoration
- Hot reload support for development

### Security & Reliability
- Session validation and health monitoring
- Graceful error handling and recovery
- Emergency recording preservation
- Comprehensive logging and debugging

## Contributing

### Quick Development Start

```bash
# For most users - just use the CLI
pip install ios-bridge-cli
ios-bridge start-server --background

# For server development (contributors only)
git clone <repo-url>
cd ios-bridge
pip install -r requirements.txt
PYTHONPATH=$(pwd) uvicorn app.main:app --reload

# CLI development
cd ios-bridge-cli
pip install -e .

# Desktop app development
cd ios-bridge-cli/ios_bridge_cli/electron_app
npm install
npm run dev
```

### Project Structure

```
ios-bridge/
├── app/                          # FastAPI server
│   ├── main.py                   # Server entry point
│   ├── api/                      # REST endpoints
│   ├── websockets/               # WebSocket handlers
│   └── services/                 # Core services
├── ios-bridge-cli/               # CLI and desktop app
│   ├── ios_bridge_cli/           # Python CLI
│   └── ios_bridge_cli/electron_app/  # Electron desktop app
├── templates/                    # Web interface HTML
├── static/                       # Web interface assets
└── README.md                     # This file
```

## Troubleshooting

### Common Issues

**"No sessions available"**
```bash
ios-bridge list                    # Check existing sessions
ios-bridge create "iPhone 15" "18.2" --wait  # Create new session
```

**Connection errors**
```bash
curl http://localhost:8000/health  # Check server status
ios-bridge server-status           # Check CLI connection
```

**Desktop app won't start**
```bash
ios-bridge start-server            # Ensure server running
ios-bridge stream --web-only       # Try web interface
```

### Debug Commands

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/api/sessions/

# Session management
curl -X POST http://localhost:8000/api/sessions/recover-orphaned
curl http://localhost:8000/api/sessions/refresh
```

## License

MIT License - see LICENSE file for details.

## Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/AutoFlowLabs/ios-bridge/issues)
- 📖 **Documentation**: [Project Wiki](https://github.com/AutoFlowLabs/ios-bridge/wiki)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/AutoFlowLabs/ios-bridge/discussions)

## Project Status & Contributing

### 🚧 Development Phase

This project is currently in **active development** with continuous improvements being made. While iOS Bridge provides a solid foundation for iOS simulator remote control, we're aware that the streaming quality (both WebRTC and WebSocket) is not yet at the level we envision.

**Current Focus Areas:**
- 🎥 **Streaming Quality Optimization** - Improving video quality, reducing latency, and enhancing performance
- 🚀 **WebRTC Enhancement** - Better codec selection, adaptive bitrate, and connection stability  
- 📡 **WebSocket Streaming** - Frame rate optimization and quality improvements
- 🛠️ **Performance Tuning** - Memory usage, CPU optimization, and resource management

### 🤝 Contributors Welcome!

We especially welcome contributions in **streaming technology**! If you have experience with:
- Video streaming protocols (WebRTC, WebSocket)
- Video encoding/decoding optimization
- Real-time communication systems
- iOS Simulator integration improvements
- Cross-platform performance optimization

Your expertise could make a significant impact on this project. Whether it's code contributions, performance insights, or architectural suggestions - we'd love to collaborate!

**How to Contribute:**
1. Check out our [GitHub Issues](https://github.com/AutoFlowLabs/ios-bridge/issues) for open tasks
2. Fork the repository and submit pull requests
3. Share your streaming optimization ideas in [Discussions](https://github.com/AutoFlowLabs/ios-bridge/discussions)
4. Help improve documentation and user experience

### 🙏 Acknowledgments

**Special Thanks:**
- **[Meta's IDB (iOS Debug Bridge)](https://fbidb.io/)** - For providing the foundational CLI commands and iOS control capabilities that inspired iOS Bridge. The [idb project](https://github.com/facebook/idb) serves as the backbone for iOS device automation, and without their excellent work, iOS Bridge wouldn't exist.
- **[Claude Code](https://claude.ai/code)** - For exceptional assistance with documentation, code structure improvements, and being an invaluable development companion throughout this project
- **The Open Source Community** - For inspiration, tools, and the collaborative spirit that makes projects like this possible
- **All Contributors** - Past, present, and future contributors who help make iOS Bridge better

---

**Getting Started**: `pip install ios-bridge-cli && ios-bridge start-server && ios-bridge create "iPhone 15 Pro" "18.2" --wait && ios-bridge stream`