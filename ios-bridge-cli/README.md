# iOS Bridge CLI

A Python-based command-line tool for streaming and controlling iOS simulator sessions from your desktop, similar to how scrcpy works for Android devices.

## Features

- 🖥️ **Desktop streaming** of iOS simulator sessions
- 🎮 **Touch and keyboard** input control  
- 📱 **Device controls** (Home, Screenshot, Device Info)
- 🔌 **WebSocket-based** real-time streaming
- 🚀 **Easy installation** via pip
- 💻 **Cross-platform** Electron-based UI
- 🌐 **Remote server** support (Windows/Linux/macOS)
- 🖥️ **Local server** management (macOS only)

## Installation

```bash
pip install ios-bridge-cli
```

## Platform Support

### macOS (Full Functionality)
- ✅ Local server management
- ✅ Remote client connections
- ✅ Desktop streaming
- ✅ All CLI commands

### Windows/Linux (Remote Client Only)
- ❌ Local server (requires macOS + Xcode)
- ✅ Remote client connections  
- ✅ Desktop streaming
- ✅ Session management commands

## Usage

### Remote Server Connection (All Platforms)
```bash
# Connect to your deployed iOS Bridge server
ios-bridge connect https://ios-bridge.yourcompany.com --save

# Test connection
ios-bridge server-status

# Use all commands with remote server
ios-bridge devices
ios-bridge create "iPhone 14 Pro" "18.2" --wait
ios-bridge stream <session_id>
```

### Local Server Management (macOS Only)
```bash
# Start the iOS Bridge server (auto-detects server location)
ios-bridge start-server

# Start server in background
ios-bridge start-server --background

# Start server on custom port
ios-bridge start-server --port 9000

# Check server status
ios-bridge server-status

# Stop the server
ios-bridge kill-server

# Force stop all server processes
ios-bridge kill-server --force --all
```

### Session Management
```bash
# List available device types and iOS versions
ios-bridge devices

# Create a new iOS simulator session
ios-bridge create "iPhone 14 Pro" "16.0" --wait

# List active sessions
ios-bridge list

# Get session information
ios-bridge info <session_id>

# Terminate a session
ios-bridge terminate <session_id>
```

### Streaming and Control
```bash
# Stream an existing session in desktop window
ios-bridge stream <session_id>

# Stream with quality settings
ios-bridge stream <session_id> --quality ultra --fullscreen

# Take screenshot
ios-bridge screenshot <session_id> --output screenshot.png
```

**Note:** The `--server` option is still available if you need to connect to a remote server, but it defaults to `http://localhost:8000` when using the local server commands.

## Controls

- **Mouse**: Click and drag for touch input
- **Keyboard**: Type directly into the device
- **Ctrl+C**: Close streaming window and exit
- **F1**: Home button
- **F2**: Take screenshot
- **F3**: Show device info

## Requirements

- macOS (for iOS Bridge server)
- Python 3.8+
- Running iOS Bridge server instance

## Architecture

```
┌─────────────────┐    HTTP/WS     ┌─────────────────┐    IPC    ┌─────────────────┐
│   Python CLI    │ ←─────────────→ │  iOS Bridge     │           │  Electron App   │
│                 │                 │    Server       │           │                 │
│ • CLI parsing   │                 │                 │           │ • Video render  │
│ • API client    │                 │ • Session mgmt  │ ←────────→ │ • Touch input   │
│ • Process mgmt  │                 │ • WebSockets    │           │ • UI controls   │
└─────────────────┘                 └─────────────────┘           └─────────────────┘
```

## License

MIT License