# Cross-Platform iOS Bridge Setup Guide

Complete guide for running iOS Bridge server on Mac and connecting from Windows/Linux clients for iOS simulator streaming.

## Overview

This is the **most common use case** for iOS Bridge: developers want to stream and control iOS simulators on their Windows or Linux machines, but iOS simulators can only run on macOS.

**Architecture:**
- **Mac (Server)**: Runs iOS simulators and iOS Bridge server
- **Windows/Linux (Clients)**: Connect via advanced web interface or basic desktop app

---

## Quick Start Summary

1. **Mac**: `ios-bridge start-server --host 0.0.0.0 --port 8000`
2. **Client Web Browser** (Recommended): Open `http://[MAC-IP]:8000` directly - **full feature set, no installation**
3. **Client Desktop App** (Basic): `ios-bridge connect http://[MAC-IP]:8000 --save` then `ios-bridge stream <session-id>`

---

## Detailed Setup

### Part 1: Mac Setup (Server Machine)

#### Prerequisites
- **macOS 10.15+** with Xcode installed
- **iOS Bridge CLI** installed: `pip install ios-bridge-cli`
- **Network access** to Mac from client machines

#### Step 1: Install iOS Bridge CLI
```bash
# Install the CLI
pip install ios-bridge-cli

# Verify installation
ios-bridge --version
```

#### Step 2: Find Your Mac's Network IP
```bash
# Get your Mac's local network IP address
ifconfig | grep "inet 192.168" | head -1
# Example output: inet 192.168.0.101 netmask 0xffffff00

# Alternative methods:
ifconfig en0 | grep "inet " | grep -v 127.0.0.1
system_profiler SPNetworkDataType | grep "IP Address"
```

**Write down this IP address** - you'll need it for client connections.

#### Step 3: Start Server with Network Access
```bash
# Start server accessible from network (not just localhost)
ios-bridge start-server --host 0.0.0.0 --port 8000 --background

# Verify server is running
ios-bridge server-status
```

**Important**: The server must bind to `0.0.0.0` (all interfaces) instead of `127.0.0.1` (localhost only) to accept network connections.

#### Step 4: Configure macOS Firewall (If Enabled)
```bash
# Check if firewall is enabled
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# If firewall is enabled, allow incoming connections on port 8000
# Go to: System Preferences → Security & Privacy → Firewall → Options
# Or run: sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
```

#### Step 5: Test Network Access
```bash
# Test from Mac itself
curl http://YOUR-MAC-IP:8000

# Should return HTML page starting with:
# <!DOCTYPE html>
# <html>
# <head>
#     <title>iOS Simulator Manager</title>
```

#### Step 6: Create iOS Simulator Sessions
```bash
# Create a simulator session for clients to connect to
ios-bridge create --device "iPhone 15 Pro" --version "17.1"

# List available sessions
ios-bridge list
```

### Part 2: Windows/Linux Setup (Client Machines)

#### Prerequisites
- **Windows 10+** or **Linux** (Ubuntu 20.04+, Fedora 34+, etc.)  
- **Network access** to the Mac server
- **For Desktop App**: Python 3.8+ installed
- **For Web Interface**: Modern web browser (Chrome, Firefox, Safari, Edge)

#### Step 1: Choose Access Method

**Option A: Desktop App (Full CLI Features)**
```bash
# Install the CLI
pip install ios-bridge-cli

# Verify installation  
ios-bridge --version
```

**Option B: Web Browser (Direct Access)**
```bash
# No installation needed!
# Simply open your browser to: http://192.168.0.101:8000
# (Replace 192.168.0.101 with your Mac's IP address)
# You can skip to "Step 4" if using web interface only
```

#### Step 2: Connect to Mac Server (Desktop App Only)
```bash
# Connect to Mac server (replace IP with your Mac's IP)
# Skip this step if using web browser
ios-bridge connect http://192.168.0.101:8000 --save

# This command:
# 1. Tests connection to Mac server
# 2. Saves server URL for future commands
# 3. Configures CLI to use remote server by default
```

#### Step 3: Verify Connection (Desktop App Only)
```bash
# Check server status
# Skip this step if using web browser
ios-bridge server-status

# Should show: "🌐 Checking remote iOS Bridge server: http://192.168.0.101:8000"

# List available sessions
ios-bridge list

# Should show sessions created on Mac
```

#### Step 4: Stream iOS Simulator

**Option A: Web Interface (Recommended - Full Features)**
```bash
# Access via web browser directly (no CLI needed)
# Open in browser: http://192.168.0.101:8000
# (Replace 192.168.0.101 with your Mac's IP)

# Features available in web interface:
# ✅ WebRTC + WebSocket streaming
# ✅ Install and launch IPA files
# ✅ File transfer (push/pull)
# ✅ Mock location, deep links, text input
# ✅ Real-time device logs
# ✅ Advanced gesture controls
# ✅ Hardware button simulation
```

**Option B: Desktop App (Basic Streaming)**
```bash
# Stream a session in desktop app (auto-downloads desktop app)
ios-bridge stream <session-id>

# First time will show:
# 🔍 iOS Bridge Desktop not found or outdated
# 🏗️ Downloading iOS Bridge Desktop for Linux/Windows...
# ████████████████████████████████████████ 25.4MB / 25.4MB
# ✅ iOS Bridge Desktop installed successfully
# 🚀 Starting iOS Bridge Desktop

# Note: Desktop app currently supports basic streaming only
# Advanced features (file transfer, app management, etc.) coming soon
```

---

## Common Usage Scenarios

### Scenario 1: Development Team Setup
**Team**: 1 Mac with Xcode + multiple Windows/Linux developers

```bash
# Mac (shared server)
ios-bridge start-server --host 0.0.0.0 --port 8000 --background

# Each developer's machine (Option A: Desktop App)
ios-bridge connect http://TEAM-MAC-IP:8000 --save
ios-bridge create --device "iPhone 15 Pro"  # Creates on Mac
ios-bridge stream SESSION-ID                # Streams to local desktop

# Each developer's machine (Option B: Web Interface)
# Simply open: http://TEAM-MAC-IP:8000 in browser
# No CLI installation needed for basic streaming
```

### Scenario 2: CI/CD Testing
**Use case**: Automated testing on Windows/Linux runners with Mac build agent

```bash
# Mac CI agent (server)
ios-bridge start-server --host 0.0.0.0 --port 8000
ios-bridge create --device "iPhone 15 Pro" > session.txt

# Windows/Linux test runner (client)
ios-bridge connect http://MAC-CI-IP:8000
ios-bridge stream $(cat session.txt) --screenshot /tests/results/
```

### Scenario 3: Remote Work Setup
**Use case**: Developer working from Windows/Linux laptop, Mac mini at office

```bash
# Mac mini at office (with port forwarding/VPN)
ios-bridge start-server --host 0.0.0.0 --port 8000

# Developer's laptop (via VPN)
ios-bridge connect http://OFFICE-MAC-IP:8000 --save
ios-bridge list
ios-bridge stream SESSION-ID
```

---

## Network Configuration

### Port Requirements
- **Port 8000**: HTTP API and WebSocket connections
- **Outbound only** from client to server (no incoming ports needed on clients)

### Firewall Configuration

#### macOS Server
```bash
# Allow incoming on port 8000
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
# Or disable firewall temporarily: sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off
```

#### Windows Client
- Windows Defender should allow outbound connections automatically
- Corporate firewalls: ensure access to Mac IP on port 8000

#### Linux Client
```bash
# Usually no configuration needed (outbound connections allowed by default)
# If using iptables/firewalld, ensure outbound HTTPS/HTTP is allowed
```

### Network Troubleshooting

#### Test Basic Connectivity
```bash
# From client machine, test if Mac server is reachable
ping MAC-IP-ADDRESS
telnet MAC-IP-ADDRESS 8000

# Should connect successfully
```

#### Test HTTP Access
```bash
# From client machine
curl http://MAC-IP-ADDRESS:8000

# Should return HTML page, not connection refused
```

#### Common Issues

**"Connection refused"**
```bash
# On Mac, check if server is running on correct interface
ios-bridge server-status
netstat -an | grep 8000

# Should show: tcp4  0  0  *.8000  *.*  LISTEN (not 127.0.0.1.8000)
```

**"No sessions found"**
```bash
# Ensure sessions are created on Mac server
# From Mac: ios-bridge list
# Should show sessions that clients can access
```

**"Desktop app won't start on client"**
```bash
# Check if auto-download works
ios-bridge stream SESSION-ID --verbose

# If download fails, check internet access from client
curl -I https://github.com
```

---

## Advanced Configuration

### Custom Ports
```bash
# Mac server (custom port)
ios-bridge start-server --host 0.0.0.0 --port 9000

# Clients
ios-bridge connect http://MAC-IP:9000 --save
```

### Multiple Servers
```bash
# Connect to different servers as needed
ios-bridge connect http://mac1.local:8000 --save --name "office-mac"
ios-bridge connect http://mac2.local:8000 --save --name "lab-mac"

# Use specific server
ios-bridge --server http://mac1.local:8000 list
```

### Persistent Server Setup
```bash
# Mac: Create systemd/launchd service for persistent server
# Example launchd plist for macOS:
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.iosbridge.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/ios-bridge</string>
        <string>start-server</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

---

## Performance Optimization

### Network Performance
- **LAN**: Best performance (< 1ms latency)
- **WiFi**: Good performance (< 10ms latency)
- **VPN**: Acceptable (< 50ms latency)
- **Internet**: Variable (depends on bandwidth/latency)

### Quality Settings
```bash
# High quality (requires good network)
ios-bridge stream SESSION-ID --quality ultra

# Balanced (recommended for most setups)
ios-bridge stream SESSION-ID --quality high

# Low bandwidth networks
ios-bridge stream SESSION-ID --quality low
```

### Bandwidth Usage
- **Ultra**: ~10-15 Mbps
- **High**: ~5-8 Mbps  
- **Medium**: ~2-4 Mbps
- **Low**: ~1-2 Mbps

---

## Security Considerations

### Network Security
- iOS Bridge server has **no authentication** by default
- Use on **trusted networks** only (corporate LAN, VPN)
- **Firewall** access to Mac server appropriately

### VPN Setup (Recommended)
```bash
# For remote access, use VPN instead of exposing server to internet
# Mac server: Run on VPN interface only
ios-bridge start-server --host VPN-INTERFACE-IP --port 8000

# Clients connect via VPN
ios-bridge connect http://VPN-MAC-IP:8000 --save
```

---

## FAQ

**Q: Can multiple clients connect to one Mac server?**  
A: Yes! Each client can stream different simulator sessions simultaneously.

**Q: Does the Mac need to stay awake?**  
A: Yes, the Mac must remain awake with the server running. Consider energy saver settings.

**Q: Can I use this over the internet?**  
A: Not recommended without VPN. The server has no authentication and streams are unencrypted.

**Q: What's the maximum number of concurrent clients?**  
A: Limited by Mac hardware and network bandwidth. Typically 2-4 clients work well.

**Q: Do I need Xcode on client machines?**  
A: No! Only the Mac server needs Xcode. Clients only need the iOS Bridge CLI.

**Q: Can I control the same simulator from multiple clients?**  
A: No, each simulator session can only be controlled by one client at a time.

**Q: What happens if network connection drops?**  
A: Desktop app will show connection error. Reconnect automatically when network returns.

---

## Command Reference

### Mac Server Commands
```bash
# Server management
ios-bridge start-server --host 0.0.0.0 --port 8000 [--background]
ios-bridge kill-server [--force]
ios-bridge server-status

# Session management  
ios-bridge create --device "iPhone 15 Pro" --version "17.1"
ios-bridge list
ios-bridge terminate SESSION-ID
```

### Client Commands
```bash
# Connection management
ios-bridge connect http://MAC-IP:8000 --save [--name NAME]
ios-bridge server-status
ios-bridge remote-help

# Session usage
ios-bridge list
ios-bridge stream SESSION-ID [--quality high] [--fullscreen]
ios-bridge screenshot SESSION-ID [--output FILE]
ios-bridge info SESSION-ID
```

---

## Desktop App vs Web Interface Comparison

| Feature | Desktop App | Web Interface |
|---------|-------------|---------------|
| **Installation** | Requires Python + CLI | No installation needed |
| **Performance** | Native desktop performance | Browser-based, excellent performance |
| **Features** | Basic streaming only | **🚀 Advanced feature-rich interface** |
| **Streaming Modes** | WebSocket only | WebSocket + WebRTC |
| **App Management** | Not available | Install/launch IPA files |
| **File Transfer** | Not available | Push/pull files to/from simulator |
| **Deep Links & URLs** | Not available | Open URLs and deep links |
| **Text Input** | Not available | Send text to simulator |
| **Gesture Controls** | Basic touch only | Swipe mode, multi-touch gestures |
| **Mock Location** | Not available | Set custom GPS coordinates |
| **Device Logs** | Not available | Real-time log viewing and filtering |
| **Hardware Buttons** | Not available | Home, Lock, Side button, Volume |
| **System Controls** | Not available | Restart pipeline, status checks |
| **Screenshots** | Save to custom locations | Download via browser |
| **Session Management** | Create, list, terminate sessions | View and stream existing sessions |
| **Auto-updates** | Automatic with CLI updates | Always latest via browser |

**Current Status**: 
- **Web Interface**: ✅ **Feature-complete with advanced controls**
- **Desktop App**: ⚠️ **Basic streaming only** - advanced features coming soon

**Recommendation**: 
- **Web Interface**: **Recommended for all users** - full feature set available
- **Desktop App**: For users who prefer native desktop apps (advanced features in development)

---

**Need help?** Check our [GitHub Issues](https://github.com/AutoFlowLabs/ios-bridge/issues) or run `ios-bridge remote-help`