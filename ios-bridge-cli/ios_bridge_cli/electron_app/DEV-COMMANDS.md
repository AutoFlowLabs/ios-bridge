# iOS Bridge Desktop App - Development Commands Quick Reference

## 🚀 Basic Development Commands

```bash
# Setup
npm install

# Start development mode
npm run dev

# Build for production
npm run build

# Package for distribution
npm run pack
```

## 🎯 Session ID Override Examples

```bash
# Get available sessions first
ios-bridge list

# Basic override
npm run dev -- --session-id=bddf902f-4ccd-4712-8c60-d05a80bacc27

# With quality
npm run dev -- --session-id=abc123 --quality=ultra

# With server override
npm run dev -- --session-id=abc123 --server-host=192.168.0.101

# Full example
npm run dev -- \
  --session-id=bddf902f-4ccd-4712-8c60-d05a80bacc27 \
  --server-host=192.168.0.101 \
  --server-port=8000 \
  --quality=high \
  --fullscreen
```

## 🔧 All Override Options

| Option | Values | Example |
|--------|--------|---------|
| `--session-id` | Any valid session ID | `--session-id=abc123` |
| `--server-host` | hostname/IP | `--server-host=192.168.0.101` |
| `--server-port` | port number | `--server-port=8000` |
| `--quality` | low, medium, high, ultra | `--quality=ultra` |
| `--fullscreen` | flag | `--fullscreen` |
| `--always-on-top` | flag | `--always-on-top` |

## 🐛 Common Development Scenarios

### Test Different Sessions
```bash
# List sessions
ios-bridge list

# Test session 1
npm run dev -- --session-id=SESSION_1

# Test session 2  
npm run dev -- --session-id=SESSION_2
```

### Test Remote Server
```bash
# Connect to remote Mac server
npm run dev -- --session-id=abc123 --server-host=192.168.0.101
```

### Test Different Qualities
```bash
# Test low quality
npm run dev -- --session-id=abc123 --quality=low

# Test ultra quality
npm run dev -- --session-id=abc123 --quality=ultra
```

### Test WebRTC Mode
```bash
# Start in WebSocket mode (default)
npm run dev -- --session-id=abc123 --quality=high

# Then click "🚀 WebRTC Stream" button in the app
```

## 🔍 Debugging

### Chrome DevTools
- Press `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Option+I` (macOS)
- View console logs, network requests, elements

### Console Commands (in DevTools)
```javascript
// Check current config
window.config

// Force reconnect
window.renderer.connect()

// Check WebSocket status  
window.renderer.websockets

// Switch streaming mode
window.renderer.toggleStreamMode()
```

## 📁 File Structure for Development

```
src/
├── main.js           # Main process - modify for window/config logic
├── renderer.js       # Renderer process - modify for UI/streaming logic  
├── preload.js        # IPC bridge - modify for main<->renderer communication
├── renderer.html     # HTML template
└── styles.css        # Styles

config.json           # Base configuration (don't modify, use overrides)
```

## ⚡ Hot Reload

Files that auto-reload on change:
- ✅ `src/renderer.js`
- ✅ `src/main.js` 
- ✅ `src/styles.css`
- ✅ `src/renderer.html`
- ❌ `config.json` (requires restart)
- ❌ `package.json` (requires restart)

## 🎬 Testing Workflow

1. **Start development mode:**
   ```bash
   npm run dev -- --session-id=YOUR_SESSION
   ```

2. **Open DevTools:** `Ctrl+Shift+I`

3. **Test WebSocket mode:** Default mode

4. **Test WebRTC mode:** Click WebRTC button

5. **Make code changes:** Files auto-reload

6. **Test production build:**
   ```bash
   npm run build
   ios-bridge stream YOUR_SESSION  # Test with real CLI
   ```