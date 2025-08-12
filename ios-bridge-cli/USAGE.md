# iOS Bridge CLI Usage Guide

## Basic Usage

### 1. List Available Sessions

```bash
# List all active iOS simulator sessions
ios-bridge list

# List with JSON output
ios-bridge list --format json

# Specify server URL
ios-bridge list --server http://your-server:8000
```

Example output:
```
📱 Active iOS Bridge Sessions:
--------------------------------------------------------------------------------
Session ID   Device Type          iOS Version  Status    
--------------------------------------------------------------------------------
a1b2c3d4e5f6 iPhone 14 Pro Max   16.0         Online    
f6e5d4c3b2a1 iPad Pro (12.9-inch) 16.1         Online    

📊 Total: 2 sessions
```

### 2. Get Session Information

```bash
# Show detailed session info
ios-bridge info a1b2c3d4e5f6

# With custom server
ios-bridge info a1b2c3d4e5f6 --server http://localhost:8000
```

Example output:
```
📱 Session Information: a1b2c3d4e5f6
--------------------------------------------------
Device Type    : iPhone 14 Pro Max
iOS Version    : 16.0
Device Name    : sim_a1b2c3d4_iPhone_14_Pro_Max
Status         : Online
UDID           : 12345678-1234-1234-1234-123456789ABC
Created        : 3600.0s ago
Installed Apps : 5

📦 Installed Apps:
  • MyApp (com.example.myapp)
  • TestApp (com.test.app)
```

### 3. Start Desktop Streaming

```bash
# Basic streaming
ios-bridge stream a1b2c3d4e5f6

# With quality settings
ios-bridge stream a1b2c3d4e5f6 --quality ultra

# Fullscreen mode
ios-bridge stream a1b2c3d4e5f6 --fullscreen

# Always on top
ios-bridge stream a1b2c3d4e5f6 --always-on-top

# Custom server
ios-bridge stream a1b2c3d4e5f6 --server https://ios-bridge.company.com:8443
```

### 4. Take Screenshots

```bash
# Save screenshot to default file (screenshot.png)
ios-bridge screenshot a1b2c3d4e5f6

# Custom output file
ios-bridge screenshot a1b2c3d4e5f6 --output ~/Desktop/ios-screenshot.png

# With custom server
ios-bridge screenshot a1b2c3d4e5f6 --server http://localhost:8000 --output device.png
```

## Desktop Controls

Once the desktop window opens, you can use these controls:

### Mouse Controls
- **Click**: Tap on device screen
- **Click and drag**: Swipe gesture
- **Right-click**: Context menu (future feature)

### Keyboard Shortcuts
- **F1**: Home button
- **F2**: Take screenshot  
- **F3**: Show device info
- **F11**: Toggle fullscreen
- **Ctrl+Q** / **Cmd+Q**: Quit application
- **Ctrl+L** / **Cmd+L**: Lock device
- **Escape**: Close modals
- **Any key**: Send text input to device

### Window Controls
- **Home button** (🏠): Send home button press
- **Screenshot button** (📷): Take and save screenshot
- **Info button** (ℹ️): Show device information modal
- **Settings button** (⚙️): Video quality settings
- **Minimize** (-): Minimize window
- **Close** (×): Close window and exit

### Quality Settings
- **Low**: 30fps, 1x resolution, 70% quality
- **Medium**: 45fps, 1.5x resolution, 85% quality  
- **High**: 60fps, 2x resolution, 95% quality
- **Ultra**: 60fps, 2.5x resolution, 98% quality

## Advanced Usage

### Environment Variables

```bash
# Default server URL
export IOS_BRIDGE_SERVER=http://localhost:8000

# Default quality
export IOS_BRIDGE_QUALITY=high

# Enable debug logging
export IOS_BRIDGE_DEBUG=1
```

### Configuration File

Create `~/.ios-bridge-cli.json`:

```json
{
  "server": "http://localhost:8000",
  "quality": "high",
  "fullscreen": false,
  "alwaysOnTop": false,
  "autoReconnect": true,
  "logLevel": "info"
}
```

### Batch Operations

```bash
# Stream multiple sessions (opens multiple windows)
for session in $(ios-bridge list --format json | jq -r '.[].session_id'); do
    ios-bridge stream "$session" &
done
```

### Scripting Integration

```python
#!/usr/bin/env python3
import subprocess
import json

# Get list of sessions
result = subprocess.run([
    'ios-bridge', 'list', '--format', 'json'
], capture_output=True, text=True)

sessions = json.loads(result.stdout)

# Stream the first available session
if sessions:
    session_id = sessions[0]['session_id']
    subprocess.run(['ios-bridge', 'stream', session_id])
else:
    print("No sessions available")
```

## Integration Examples

### CI/CD Pipeline

```yaml
# GitHub Actions example
- name: Test iOS App
  run: |
    # Start iOS Bridge session (assuming server is running)
    SESSION_ID=$(curl -X POST http://ios-bridge-server:8000/api/sessions/ \
      -H "Content-Type: application/json" \
      -d '{"device_type": "iPhone 14", "ios_version": "16.0"}' | jq -r '.session_id')
    
    # Install app (using your existing API)
    curl -X POST http://ios-bridge-server:8000/api/sessions/$SESSION_ID/install \
      -F "file=@MyApp.ipa"
    
    # Take screenshots during testing
    ios-bridge screenshot $SESSION_ID --output test-before.png
    
    # Run your tests here...
    
    ios-bridge screenshot $SESSION_ID --output test-after.png
    
    # Cleanup session
    curl -X DELETE http://ios-bridge-server:8000/api/sessions/$SESSION_ID
```

### Automated Testing

```bash
#!/bin/bash
# automated-test.sh

SESSION_ID="$1"
if [ -z "$SESSION_ID" ]; then
    echo "Usage: $0 <session_id>"
    exit 1
fi

# Verify session exists
if ! ios-bridge info "$SESSION_ID" >/dev/null 2>&1; then
    echo "Session $SESSION_ID not found or not accessible"
    exit 1
fi

# Take initial screenshot
ios-bridge screenshot "$SESSION_ID" --output "test-start.png"

echo "✅ Session verified and ready for testing"
echo "Use: ios-bridge stream $SESSION_ID"
```

### Remote Testing Setup

```bash
# SSH tunnel for remote iOS Bridge server
ssh -L 8000:localhost:8000 user@ios-bridge-server.com

# Now use local port
ios-bridge list --server http://localhost:8000
```

## Error Handling

### Common Error Messages

```bash
# Session not found
❌ Session abc123 not found
# Solution: Check session ID and server connectivity

# Connection error  
🔌 Connection error: Cannot connect to iOS Bridge server at http://localhost:8000
# Solution: Verify server is running and accessible

# Electron app error
💥 Failed to start Electron app: electron not found
# Solution: Install Node.js and Electron dependencies
```

### Debugging

```bash
# Enable verbose logging
ios-bridge --verbose stream <session_id>

# Check server connectivity
curl http://localhost:8000/health

# Verify WebSocket connections
# Check browser dev tools or use wscat to test WebSocket endpoints
```

## Performance Tips

### Optimize Video Quality

- Use **Low** quality for slow networks
- Use **High** quality for local connections
- Use **Ultra** quality only for high-end systems

### Network Optimization

```bash
# For slow connections, use lower quality
ios-bridge stream <session_id> --quality low

# For local testing, use maximum quality
ios-bridge stream <session_id> --quality ultra
```

### System Resources

- Close unnecessary applications to free up memory
- Use hardware acceleration when available
- Monitor CPU usage during streaming

## Troubleshooting

### Connection Issues

```bash
# Test server connectivity
curl -v http://localhost:8000/health

# Check WebSocket connectivity
wscat -c ws://localhost:8000/ws/<session_id>/video

# Verify session is active
ios-bridge info <session_id>
```

### Video Issues

- **Black screen**: Check session accessibility
- **Lag**: Reduce quality setting
- **Choppy video**: Close other applications, check CPU usage
- **No video**: Verify WebSocket connection

### Input Issues

- **Touch not working**: Check if session allows input
- **Keyboard not working**: Click on video area to focus
- **Wrong coordinates**: Check device resolution scaling

For more troubleshooting, see [INSTALL.md](INSTALL.md#troubleshooting).