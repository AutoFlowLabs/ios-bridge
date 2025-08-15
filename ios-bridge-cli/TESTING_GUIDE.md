# iOS Bridge CLI Testing Guide

## 🧪 Step-by-Step Testing Instructions

### Prerequisites
1. **macOS** with Xcode and iOS Simulator installed
2. **Python 3.8+** installed
3. **Node.js and npm** installed
4. **iOS Bridge Server** (your existing server code)

### Step 1: Start the iOS Bridge Server

```bash
# Navigate to your iOS Bridge server directory
cd /Users/himanshukukreja/autoflow/ios-bridge

# Start the server on localhost:8000
python run.py
# OR
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify server is running:
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

### Step 2: Install the CLI Tool

#### Option A: Development Installation
```bash
# Navigate to the CLI directory
cd /Users/himanshukukreja/autoflow/ios-bridge/ios-bridge-cli

# Install in development mode
pip install -e .

# Verify installation
ios-bridge version
```

#### Option B: Build and Install
```bash
cd /Users/himanshukukreja/autoflow/ios-bridge/ios-bridge-cli

# Build everything
python build.py

# Install the built package
pip install dist/ios_bridge_cli-*.whl

# Verify installation
ios-bridge version
```

### Step 3: Test CLI Commands

#### 3.1 Test Connection and List Available Devices
```bash
# Test server connection and list available devices
ios-bridge devices --server http://localhost:8000

# Expected output:
# 📱 Available iOS Device Configurations:
# ------------------------------------------------------------
# Device Types:
#   • iPhone 14
#   • iPhone 14 Plus  
#   • iPhone 14 Pro
#   • iPhone 14 Pro Max
#   • iPad Pro (12.9-inch)
#   ... etc
#
# iOS Versions:
#   • 16.0
#   • 16.1
#   • 18.2
#   ... etc
```

#### 3.2 Create a New Session
```bash
# Create a new iPhone 14 Pro session with iOS 16.0
ios-bridge create "iPhone 14 Pro" "16.0" --server http://localhost:8000 --wait

# Expected output:
# 🚀 Creating iOS simulator session...
#    Device: iPhone 14 Pro
#    iOS Version: 16.0
# ✅ Session created successfully!
#    Session ID: abc123def456ghi789
#    Device: iPhone 14 Pro
#    iOS Version: 16.0
#    UDID: 12345678-1234-1234-1234-123456789ABC
# ⏳ Waiting for session to be ready...
# ✅ Session is ready and accessible!
# 
# 🎮 To stream this session, run:
#    ios-bridge stream abc123def456ghi789
```

**Save the Session ID** from the output - you'll need it for the next steps!

#### 3.3 List Active Sessions
```bash
# List all active sessions
ios-bridge list --server http://localhost:8000

# Expected output:
# 📱 Active iOS Bridge Sessions:
# --------------------------------------------------------------------------------
# Session ID   Device Type          iOS Version  Status    
# --------------------------------------------------------------------------------
# abc123def456 iPhone 14 Pro        16.0         Online    
# 
# 📊 Total: 1 sessions
```

#### 3.4 Get Session Information
```bash
# Get detailed info about your session (replace with your session ID)
ios-bridge info abc123def456ghi789 --server http://localhost:8000

# Expected output:
# 📱 Session Information: abc123def456ghi789
# --------------------------------------------------
# Device Type    : iPhone 14 Pro
# iOS Version    : 16.0
# Device Name    : sim_abc123de_iPhone_14_Pro
# Status         : Online
# UDID           : 12345678-1234-1234-1234-123456789ABC
# Created        : 30.5s ago
# Installed Apps : 0
```

#### 3.5 Test Screenshot
```bash
# Take a screenshot of the session
ios-bridge screenshot abc123def456ghi789 --server http://localhost:8000 --output test-screenshot.png

# Expected output:
# 📸 Taking screenshot of session: abc123def456ghi789
# ✅ Screenshot saved: test-screenshot.png (45.2 KB)

# Verify the screenshot file exists
ls -la test-screenshot.png
```

### Step 4: Test Desktop Streaming

This is the main feature! Test the desktop streaming client:

```bash
# Start desktop streaming (replace with your session ID)
ios-bridge stream abc123def456ghi789 --server http://localhost:8000

# Expected behavior:
# 🚀 Starting iOS Bridge streaming for session: abc123def456ghi789
# 📱 Session info: iPhone 14 Pro iOS 16.0
# 🖥️  Opening desktop streaming window...
# [Electron app window should open showing the iOS simulator]
```

#### Desktop Window Testing Checklist

When the desktop window opens, test these features:

**✅ Video Streaming**
- [ ] iOS simulator screen appears in the window
- [ ] Video updates in real-time (you should see the iOS home screen)
- [ ] FPS counter shows reasonable values (15-60 FPS)

**✅ Touch Controls**
- [ ] Click on the screen → should see touch feedback on iOS simulator
- [ ] Click on an app icon → should launch the app
- [ ] Drag/swipe → should scroll or swipe in the simulator

**✅ Keyboard Input**
- [ ] Click on a text field in iOS simulator
- [ ] Type on your keyboard → text should appear in the simulator

**✅ Device Controls**
- [ ] Click Home button (🏠) → should go to home screen
- [ ] Click Screenshot button (📷) → should take screenshot
- [ ] Click Info button (ℹ️) → should show device info modal
- [ ] Press F1 key → should act as Home button
- [ ] Press F2 key → should take screenshot
- [ ] Press F3 key → should show device info

**✅ Window Controls**
- [ ] Minimize button works
- [ ] Quality dropdown shows options (Low/Medium/High/Ultra)
- [ ] Close button (×) closes window and returns to CLI

**✅ Exit Behavior**
- [ ] Press Ctrl+C in CLI → window should close gracefully
- [ ] CLI should return to prompt
- [ ] Session should still exist (test with `ios-bridge list`)

### Step 5: Test Session Termination

```bash
# Terminate the session when done testing (replace with your session ID)
ios-bridge terminate abc123def456ghi789 --server http://localhost:8000

# Expected output (with confirmation prompt):
# ⚠️  Are you sure you want to terminate session abc123def456... (iPhone 14 Pro iOS 16.0)? [y/N]: y
# 🛑 Terminating session: abc123def456ghi789
# ✅ Session abc123def456ghi789 terminated successfully

# Verify session is gone
ios-bridge list --server http://localhost:8000
# Should show no sessions or empty list
```

## 🐛 Troubleshooting Common Issues

### Issue 1: "ios-bridge command not found"
```bash
# Solution: Make sure CLI is installed
pip install -e .
# OR
pip install dist/ios_bridge_cli-*.whl

# Check if it's in your PATH
which ios-bridge
```

### Issue 2: "Connection error: Cannot connect to iOS Bridge server"
```bash
# Solution: Verify server is running
curl http://localhost:8000/health

# Check if server process is running
ps aux | grep python | grep ios-bridge
```

### Issue 3: "Node.js/npm not found" or Electron build errors
```bash
# Solution: Install Node.js
brew install node  # On macOS
# OR download from https://nodejs.org/

# Verify installation
node --version
npm --version

# Clear npm cache if needed
npm cache clean --force
```

### Issue 4: Session creation fails
```bash
# Solution: Check available configurations
ios-bridge devices --server http://localhost:8000

# Make sure Xcode and iOS Simulator are installed
xcode-select --install

# Check if simctl works
xcrun simctl list devices
```

### Issue 5: Desktop window doesn't open or shows errors
```bash
# Solution: Run with verbose logging
ios-bridge --verbose stream <session_id> --server http://localhost:8000

# Check if Electron dependencies are installed
cd ~/.local/lib/python*/site-packages/ios_bridge_cli/electron_app
npm install
```

### Issue 6: Video not streaming or black screen
```bash
# Solution: Check WebSocket connections
# In browser dev tools, check for WebSocket connection errors

# Verify session is accessible
ios-bridge info <session_id> --server http://localhost:8000

# Try different quality setting
ios-bridge stream <session_id> --quality low
```

## 🧪 Advanced Testing Scenarios

### Test Multiple Sessions
```bash
# Create multiple sessions for testing
ios-bridge create "iPhone 14" "16.0" --server http://localhost:8000
ios-bridge create "iPad Pro (12.9-inch)" "16.1" --server http://localhost:8000

# List all sessions
ios-bridge list --server http://localhost:8000

# Stream multiple sessions (each opens separate window)
ios-bridge stream <session_id_1> --server http://localhost:8000 &
ios-bridge stream <session_id_2> --server http://localhost:8000 &
```

### Test Different Quality Settings
```bash
# Test different quality modes
ios-bridge stream <session_id> --quality low
ios-bridge stream <session_id> --quality medium  
ios-bridge stream <session_id> --quality high
ios-bridge stream <session_id> --quality ultra
```

### Test Window Options
```bash
# Test fullscreen mode
ios-bridge stream <session_id> --fullscreen

# Test always-on-top mode
ios-bridge stream <session_id> --always-on-top
```

## ✅ Success Criteria

Your iOS Bridge CLI is working correctly if:

1. **✅ All CLI commands work** without errors
2. **✅ Desktop window opens** and shows iOS simulator screen
3. **✅ Video streams in real-time** with reasonable FPS
4. **✅ Touch input works** - clicks translate to taps on simulator
5. **✅ Keyboard input works** - typing appears in simulator text fields
6. **✅ Device controls work** - Home, Screenshot, Info buttons function
7. **✅ Graceful shutdown** - Ctrl+C closes window and preserves session
8. **✅ Session management** - create, list, info, terminate all work

## 📞 Getting Help

If you encounter issues:

1. **Check logs** with `--verbose` flag
2. **Verify prerequisites** (Python, Node.js, Xcode)
3. **Test server connectivity** with `curl`
4. **Check WebSocket connections** in browser dev tools
5. **Restart components** (server, CLI, simulators)

The CLI should provide a smooth, responsive desktop experience for controlling your iOS Bridge simulator sessions! 🎉