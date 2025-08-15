# iOS Bridge Desktop App - Development Guide

This guide covers the development workflow for the iOS Bridge Electron desktop application.

## 🚀 Quick Start

### Prerequisites
- Node.js (v16 or higher)
- npm
- iOS Bridge server running

### Setup Development Environment

1. **Navigate to the electron app directory:**
   ```bash
   cd ios-bridge-cli/ios_bridge_cli/electron_app
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development mode:**
   ```bash
   npm run dev
   ```

## 🛠️ Development Commands

### Basic Commands

```bash
# Start development mode with live reload
npm run dev

# Build the app for production
npm run build

# Package the app for distribution
npm run pack

# Run linting
npm run lint
```

### Development Mode with Configuration Overrides

The development mode supports command line arguments to override config.json values:

#### Session ID Override
```bash
# Override session ID from command line
npm run dev -- --session-id=your-session-id-here

# Example with real session ID
npm run dev -- --session-id=bddf902f-4ccd-4712-8c60-d05a80bacc27
```

#### Server Configuration Override
```bash
# Override server host and port
npm run dev -- --session-id=abc123 --server-host=192.168.0.101 --server-port=8000

# Connect to remote server
npm run dev -- --session-id=abc123 --server-host=your-server.com --server-port=443
```

#### Streaming Quality Override
```bash
# Override streaming quality
npm run dev -- --session-id=abc123 --quality=ultra

# Available quality options: low, medium, high, ultra
npm run dev -- --session-id=abc123 --quality=low
```

#### UI Mode Overrides
```bash
# Enable fullscreen mode
npm run dev -- --session-id=abc123 --fullscreen

# Enable always on top
npm run dev -- --session-id=abc123 --always-on-top

# Combine multiple options
npm run dev -- --session-id=abc123 --fullscreen --always-on-top --quality=high
```

### Complete Override Example
```bash
npm run dev -- \
  --session-id=bddf902f-4ccd-4712-8c60-d05a80bacc27 \
  --server-host=192.168.0.101 \
  --server-port=8000 \
  --quality=ultra \
  --fullscreen \
  --always-on-top
```

## 📋 Available Override Options

| Option | Description | Type | Example |
|--------|-------------|------|---------|
| `--session-id` | Override the iOS session ID | String | `--session-id=abc123` |
| `--server-host` | Override server hostname/IP | String | `--server-host=192.168.0.101` |
| `--server-port` | Override server port | Number | `--server-port=8000` |
| `--quality` | Override streaming quality | String | `--quality=ultra` |
| `--fullscreen` | Enable fullscreen mode | Flag | `--fullscreen` |
| `--always-on-top` | Keep window always on top | Flag | `--always-on-top` |

### Quality Options
- **`low`** - Low quality, faster performance, lower bandwidth
- **`medium`** - Balanced quality and performance
- **`high`** - High quality streaming (default)
- **`ultra`** - Maximum quality, higher bandwidth

## 🔧 Development Workflow

### 1. Get Available Sessions
```bash
# List all active iOS simulator sessions
ios-bridge list
```

### 2. Start Development with Session
```bash
# Copy a session ID from the list and start development
npm run dev -- --session-id=YOUR_SESSION_ID
```

### 3. Development Features Available

#### Live Reloading
- Modify `src/renderer.js`, `src/main.js`, or other files
- Changes are automatically reloaded in the app
- No need to restart the development server

#### Chrome DevTools
- Press `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Option+I` (macOS)
- Access full Chrome DevTools for debugging
- View console logs, network requests, element inspection

#### Enhanced Logging
Development mode includes detailed console logging:
- WebSocket connection status
- WebRTC signaling messages
- ICE candidate information
- Streaming quality metrics
- Error messages and debugging info

### 4. Testing Different Modes

#### Test WebSocket Streaming
```bash
npm run dev -- --session-id=abc123 --quality=high
# App starts in WebSocket mode by default
```

#### Test WebRTC Streaming
```bash
npm run dev -- --session-id=abc123 --quality=ultra
# Click the "🚀 WebRTC Stream" button in the app
```

#### Test Remote Server Connection
```bash
npm run dev -- --session-id=abc123 --server-host=192.168.0.101
# Test connecting to remote iOS Bridge server
```

## 📁 Project Structure

```
electron_app/
├── src/
│   ├── main.js           # Main Electron process
│   ├── renderer.js       # Renderer process (UI logic)
│   ├── preload.js        # Preload script (IPC bridge)
│   ├── renderer.html     # HTML template
│   └── styles.css        # Styles
├── assets/
│   └── icons/            # App icons for different platforms
├── config.json           # Default configuration
├── package.json          # Node.js dependencies and scripts
└── DEVELOPMENT.md        # This file
```

## 🐛 Debugging Tips

### Common Development Issues

#### "Missing session ID or server URL" Error
```bash
# Ensure you provide a session ID
npm run dev -- --session-id=your-session-id

# Or check that config.json has valid sessionId and server settings
```

#### Connection Errors
```bash
# Verify iOS Bridge server is running
curl http://localhost:8000/api/sessions/

# Check if session ID exists
ios-bridge list | grep your-session-id
```

#### WebRTC Not Working
1. Check browser console for ICE candidate logs
2. Verify server supports WebRTC endpoints
3. Check network connectivity for remote connections

### Debug Console Commands

In Chrome DevTools console, you can access:
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

## 🔄 Hot Reload Development

### Supported File Types
- **JavaScript files** (`src/*.js`) - Auto reload on change
- **HTML files** (`src/*.html`) - Auto reload on change  
- **CSS files** (`src/*.css`) - Auto reload on change
- **JSON files** (`config.json`) - Requires restart

### Development Best Practices

1. **Keep config.json as base template** - Use command line overrides for testing
2. **Use Chrome DevTools extensively** - Essential for debugging WebRTC and WebSocket issues
3. **Test both streaming modes** - WebSocket and WebRTC have different behaviors
4. **Test different network scenarios** - localhost vs remote server connections
5. **Monitor console logs** - Development mode provides detailed logging

## 🚀 Production Considerations

### Building for Production
```bash
# Build optimized version
npm run build

# Package for distribution
npm run pack
```

### Configuration Differences
- **Development**: Uses `config.json` + command line overrides
- **Production**: Uses configuration passed from CLI tool
- **Development**: Has detailed logging and DevTools
- **Production**: Minimal logging, no DevTools access

### Testing Production Build
```bash
# Build and test production version
npm run build
npm run pack

# Test with real CLI tool
ios-bridge stream your-session-id
```

## 📚 Additional Resources

- [Electron Documentation](https://www.electronjs.org/docs)
- [WebRTC API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API)
- [WebSocket API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [iOS Bridge CLI Documentation](../../../README.md)

## 🤝 Contributing

When developing new features:

1. **Start development mode** with your test session
2. **Make changes** to relevant files
3. **Test both streaming modes** (WebSocket and WebRTC)
4. **Test different configurations** using command line overrides
5. **Verify production build** works correctly
6. **Update this documentation** if adding new features

## ⚠️ Important Notes

- **Backward Compatibility**: Command line overrides are backward compatible and won't break production usage
- **Config Precedence**: Command line arguments override config.json values
- **Session Validation**: Session ID must exist in the iOS Bridge server
- **Network Requirements**: WebRTC requires network connectivity for remote connections