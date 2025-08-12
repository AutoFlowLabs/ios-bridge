# iOS Bridge CLI - Complete Testing Guide

## 🚀 **New Server Management Features Added!**

The iOS Bridge CLI now includes built-in server management commands, making testing much easier!

## ✅ **Complete Testing Workflow**

### Step 1: Install the CLI
```bash
cd /Users/himanshukukreja/autoflow/ios-bridge/ios-bridge-cli
pip install -e .

# Verify installation
ios-bridge version
ios-bridge --help
```

### Step 2: Start the iOS Bridge Server
```bash
# Start server in background (recommended for testing)
ios-bridge start-server --background

# Expected output:
# 🚀 Starting iOS Bridge server on 0.0.0.0:8000...
# ✅ Server started in background (PID: 12345)
# 🌐 Server URL: http://localhost:8000
# 📋 To stop: ios-bridge kill-server
```

**Alternative server options:**
```bash
# Start in foreground (shows server logs)
ios-bridge start-server

# Start on different port
ios-bridge start-server --port 9000 --background

# Specify server path manually
ios-bridge start-server --server-path /path/to/ios-bridge --background
```

### Step 3: Verify Server is Running
```bash
ios-bridge server-status

# Expected output:
# 📱 iOS Bridge Server Status
# ----------------------------------------
# 🟢 Found 1 server process(es) running:
#   1. PID 12345: python run.py --host 0.0.0.0 --port 8000
# 🌐 Testing connection to http://localhost:8000...
# ✅ Server is responding to HTTP requests
# 📱 Available: 70 device types, 1 iOS versions
# 🎮 Active sessions: 0
```

### Step 4: Test Session Management
```bash
# 1. List available devices
ios-bridge devices

# 2. Create a new session (save the session ID!)
ios-bridge create "iPhone 14 Pro" "18.2" --wait
# Example output: Session ID: 3c775724-b488-4201-8e93-756df722820a

# 3. List active sessions
ios-bridge list

# 4. Get session details
ios-bridge info 3c775724-b488-4201-8e93-756df722820a
```

### Step 5: Test Desktop Streaming
```bash
# Start desktop streaming (replace with your session ID)
ios-bridge stream 3c775724-b488-4201-8e93-756df722820a

# Expected behavior:
# 🚀 Starting iOS Bridge streaming for session: 3c775724-b488-4201-8e93-756df722820a
# 📱 Session info: iPhone 14 Pro iOS 18.2
# 🖥️  Opening desktop streaming window...
# [Desktop window opens with iOS simulator]
```

### Step 6: Test Desktop Window Features

When the desktop window opens, test these:

**✅ Video Streaming**
- [ ] iOS simulator screen appears and updates in real-time
- [ ] FPS counter shows reasonable values (15-60 FPS)

**✅ Touch Controls**
- [ ] Click on home screen icons → should launch apps
- [ ] Drag/swipe → should scroll in iOS apps
- [ ] Click on text fields → should show iOS keyboard

**✅ Keyboard Input**
- [ ] Open iOS Notes app or similar
- [ ] Click on a text field
- [ ] Type on your keyboard → text appears in iOS app

**✅ Device Controls**
- [ ] Click Home button (🏠) → goes to iOS home screen
- [ ] Click Screenshot button (📷) → takes screenshot
- [ ] Click Info button (ℹ️) → shows device info modal
- [ ] Press F1 → acts as Home button
- [ ] Press F2 → takes screenshot
- [ ] Press F3 → shows device info

**✅ Quality & Window Controls**
- [ ] Quality dropdown → change between Low/Medium/High/Ultra
- [ ] Minimize button → minimizes window
- [ ] Close button (×) → closes window

**✅ Graceful Exit**
- [ ] Press Ctrl+C in CLI → closes desktop window
- [ ] CLI returns to prompt
- [ ] Session remains active (verify with `ios-bridge list`)

### Step 7: Test Screenshot Feature
```bash
# Take a screenshot
ios-bridge screenshot 3c775724-b488-4201-8e93-756df722820a --output test.png

# Verify screenshot was saved
ls -la test.png
```

### Step 8: Clean Up
```bash
# Terminate the session
ios-bridge terminate 3c775724-b488-4201-8e93-756df722820a

# Stop the server
ios-bridge kill-server

# Verify server is stopped
ios-bridge server-status
```

## 🎯 **Testing Scenarios**

### Scenario 1: Quick Test (2 minutes)
```bash
ios-bridge start-server --background
ios-bridge create "iPhone 14 Pro" "18.2" --wait
# Copy session ID from output
ios-bridge stream <session_id>
# Test touch and keyboard in desktop window
# Press Ctrl+C to exit
ios-bridge terminate <session_id>
ios-bridge kill-server
```

### Scenario 2: Multiple Sessions
```bash
ios-bridge start-server --background
ios-bridge create "iPhone 14 Pro" "18.2" --wait
ios-bridge create "iPad Pro (12.9-inch) (6th generation)" "18.2" --wait
ios-bridge list
# Stream both sessions (each opens separate window)
ios-bridge stream <session_id_1> &
ios-bridge stream <session_id_2> &
```

### Scenario 3: Different Quality Settings
```bash
ios-bridge start-server --background
ios-bridge create "iPhone 14 Pro" "18.2" --wait
ios-bridge stream <session_id> --quality low
ios-bridge stream <session_id> --quality ultra --fullscreen
```

### Scenario 4: Background Server Management
```bash
# Start multiple servers on different ports
ios-bridge start-server --port 8000 --background
ios-bridge start-server --port 8001 --background

# Check status
ios-bridge server-status

# Kill specific server
ios-bridge kill-server  # Interactive selection

# Kill all servers
ios-bridge kill-server --force --all
```

## 🐛 **Common Issues & Solutions**

### Issue 1: "iOS Bridge server not found"
```bash
# Solution: Specify server path manually
ios-bridge start-server --server-path /Users/himanshukukreja/autoflow/ios-bridge
```

### Issue 2: "Port already in use"
```bash
# Solution: Use different port or kill existing process
ios-bridge start-server --port 8001 --background
# OR
ios-bridge kill-server --force
```

### Issue 3: Desktop window doesn't open
```bash
# Solution: Check Electron dependencies
cd ~/.local/lib/python*/site-packages/ios_bridge_cli/electron_app
npm install
```

### Issue 4: No devices available
```bash
# Solution: Check if Xcode/iOS Simulator is installed
xcrun simctl list devices
xcode-select --install
```

## 🎊 **Success Criteria**

Your iOS Bridge CLI is working perfectly if:

1. ✅ **Server commands work** - `start-server`, `kill-server`, `server-status`
2. ✅ **Session management works** - `create`, `list`, `info`, `terminate`
3. ✅ **Desktop streaming works** - Window opens with real-time video
4. ✅ **Touch input works** - Clicks translate to iOS simulator taps
5. ✅ **Keyboard input works** - Typing appears in iOS apps
6. ✅ **Device controls work** - Home, Screenshot, Info buttons
7. ✅ **Graceful shutdown works** - Ctrl+C closes window but preserves session

## 🚀 **Complete Command Reference**

### Server Management
```bash
ios-bridge start-server [--background] [--port 8000] [--server-path PATH]
ios-bridge kill-server [--force] [--all]
ios-bridge server-status
```

### Session Management
```bash
ios-bridge devices
ios-bridge create "DEVICE_TYPE" "IOS_VERSION" [--wait]
ios-bridge list
ios-bridge info <session_id>
ios-bridge terminate <session_id> [--force]
```

### Streaming & Control
```bash
ios-bridge stream <session_id> [--quality LEVEL] [--fullscreen] [--always-on-top]
ios-bridge screenshot <session_id> [--output FILE]
```

### Utility
```bash
ios-bridge version
ios-bridge --help
```

---

## 🎉 **You're Ready!**

The iOS Bridge CLI is now a **complete, self-contained solution** that:

- **Manages the server** for you (start/stop/status)
- **Creates and manages sessions** easily
- **Provides desktop streaming** with full touch/keyboard control
- **Works like scrcpy** but for iOS simulators

Just run `ios-bridge start-server --background` and start creating sessions! 🚀