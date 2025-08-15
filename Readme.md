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
# Install and create an iOS session
pip install ios-bridge-cli
ios-bridge create "iPhone 15 Pro" "17.0" --wait

# Stream to desktop app
ios-bridge stream
```

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

```bash
# Install the CLI
pip install ios-bridge-cli

# Create and stream an iOS session
ios-bridge create "iPhone 15 Pro" "17.0" --wait
ios-bridge stream
```

### 2. For Teams (Server + Web Interface)

**Mac Server Setup:**
```bash
# Clone and start the server
git clone <repo-url>
cd ios-bridge
pip install -r requirements.txt
PYTHONPATH=$(pwd) python app/main.py
```

**Team Access:**
- **Web Interface**: `http://MAC-IP:8000`
- **Desktop Clients**: `ios-bridge connect http://MAC-IP:8000 --save`

### 3. For Custom Integration (API)

```bash
# Create session via API
curl -X POST "http://localhost:8000/api/sessions/create" \
  -d "device_type=iPhone 15 Pro&ios_version=17.0"

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
ios-bridge create "iPhone 15 Pro" "17.0" --wait
ios-bridge stream
```

### Option 2: Full Server Setup

```bash
# Clone repository
git clone <repo-url>
cd ios-bridge

# Install dependencies
pip install -r requirements.txt

# Install additional tools
brew install ffmpeg idb-companion
pip install fb-idb

# Start server
PYTHONPATH=$(pwd) python app/main.py
```

### Option 3: Development Setup

```bash
# Server development
PYTHONPATH=$(pwd) uvicorn app.main:app --reload

# Desktop app development
cd ios-bridge-cli/ios_bridge_cli/electron_app
npm install
npm run dev
```

## Platform Compatibility

| Component | macOS | Windows | Linux | iOS/Android |
|-----------|:-----:|:-------:|:-----:|:-----------:|
| **FastAPI Server** | ✅ Host | ❌ | ❌ | ❌ |
| **CLI Client** | ✅ Full | ✅ Remote | ✅ Remote | ❌ |
| **Desktop App** | ✅ Native | ✅ Native | ✅ Native | ❌ |
| **Web Interface** | ✅ Browser | ✅ Browser | ✅ Browser | ✅ Mobile |

*Server requires macOS + Xcode for iOS Simulator access*

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

```bash
# Session Management
GET    /api/sessions/                    # List all sessions
POST   /api/sessions/create              # Create new session
GET    /api/sessions/{id}                # Get session details
DELETE /api/sessions/{id}                # Delete session

# App Management  
POST   /api/sessions/{id}/apps/install   # Install IPA
GET    /api/sessions/{id}/apps           # List installed apps
POST   /api/sessions/{id}/apps/{bundle}/launch   # Launch app

# Recording
POST   /api/sessions/{id}/recording/start # Start recording
POST   /api/sessions/{id}/recording/stop  # Stop and download
```

### WebSocket Endpoints

```javascript
// Control WebSocket
ws://localhost:8000/ws/{session-id}/control

// Video Streaming
ws://localhost:8000/ws/{session-id}/video

// WebRTC Streaming
ws://localhost:8000/ws/{session-id}/webrtc

// Screenshots
ws://localhost:8000/ws/{session-id}/screenshot
```

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
- **[Desktop App Development](ios-bridge-cli/ios_bridge_cli/electron_app/DEVELOPMENT.md)** - Electron app development
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
# Server development
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
ios-bridge create "iPhone 15" "17.0" --wait  # Create new session
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

---

**Getting Started**: `pip install ios-bridge-cli && ios-bridge create "iPhone 15 Pro" "17.0" --wait && ios-bridge stream`