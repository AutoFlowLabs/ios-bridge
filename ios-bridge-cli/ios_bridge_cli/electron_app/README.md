# iOS Bridge Desktop App

A desktop streaming client for iOS Bridge that provides a native desktop experience for iOS device streaming.

## ⚠️ Important: How This App Works

The Electron desktop app is designed to work as a **client** that connects to the iOS Bridge CLI server. It's **not meant to run standalone** - it requires the iOS Bridge server to be running first.

### Normal Workflow (Production)
1. User runs `ios-bridge stream <session-id>` 
2. CLI starts the server and creates a streaming session
3. CLI automatically launches this Electron app with proper configuration
4. Electron app connects to the CLI server and displays the iOS device stream

### Development/Testing Workflow
- **For full integration testing:** Run `ios-bridge stream <session-id>` - this will start the server and launch the app automatically
- **For standalone UI testing:** Use the static `config.json` (see below) and run `npm run dev`
- **Expected behavior when testing standalone:** You'll see "Connection error: Missing session ID or server URL" - this is normal without a running server

## Quick Start

### Recommended: Full Integration Testing
```bash
# This is the proper way to test the app
ios-bridge stream <session-id>
```

### Standalone UI Testing (Limited Functionality)
```bash
npm run dev  # With developer tools
npm run start  # Production mode
```

## Configuration

### Production Configuration (Automatic)
In production, the iOS Bridge CLI automatically:
- Creates a temporary config file with real session information  
- Launches the Electron app with `electron . --config /tmp/ios_bridge_config_xxx.json`
- Passes live server details, session ID, and device information

### Development Configuration (Manual)
For standalone UI testing, the app uses this static `config.json` file:

```json
{
    "sessionId": "demo-session",
    "sessionInfo": {
        "device_type": "iPhone 15 Pro",
        "device_width": 393,
        "device_height": 852,
        "stream_width": 393,
        "stream_height": 852,
        "scale_factor": 3.0
    },
    "serverPort": 8888,
    "serverHost": "localhost",
    "fullscreen": false,
    "alwaysOnTop": false,
    "streaming": {
        "protocol": "websocket",
        "fps": 30,
        "quality": "high"
    }
}
```

### Configuration Options

- **sessionId**: Unique identifier for the streaming session
- **sessionInfo**: Device information and dimensions
- **serverPort**: Port where the iOS Bridge server is running
- **serverHost**: Host where the iOS Bridge server is running
- **fullscreen**: Start in fullscreen mode
- **alwaysOnTop**: Keep window always on top
- **streaming**: Streaming protocol and quality settings

## Building for Distribution

### Build for current platform
```bash
npm run build
```

### Build for specific platforms
```bash
npm run build-mac    # macOS (DMG + ZIP)
npm run build-win    # Windows (NSIS + Portable)
npm run build-linux  # Linux (AppImage + DEB + RPM)
```

## Keyboard Shortcuts

- **F1**: Home Button
- **F2**: Screenshot
- **F3**: Device Info
- **F4**: Toggle Keyboard
- **F5**: Lock Device
- **F6**: Start Recording
- **F7**: Stop Recording
- **F11**: Toggle Fullscreen
- **F12**: Toggle Developer Tools
- **Cmd/Ctrl+Q**: Quit App
- **Cmd/Ctrl+R**: Reload
- **Cmd/Ctrl+Shift+R**: Force Reload

## Connection Requirements

Before starting the desktop app, ensure:

1. iOS Bridge CLI server is running
2. Device is connected and available
3. Server configuration matches the config.json settings

## Usage with iOS Bridge CLI

### Recommended (Automatic Integration)
```bash
# This starts the server AND launches the desktop app automatically
ios-bridge stream <session-id>

# Or use the web interface only
ios-bridge stream <session-id> --web-only
```

### Manual Testing (Advanced)
1. Start the iOS Bridge server:
   ```bash
   ios-bridge stream
   ```

2. Update `config.json` with the correct server details and session ID from the CLI output

3. Start the desktop app:
   ```bash
   npm run start
   ```

## Troubleshooting

**App shows "Connection error: Missing session ID or server URL"**
- This is **normal** when running the app standalone without a server
- Solution: Run `ios-bridge stream <session-id>` instead for full integration
- For testing: Ensure the iOS Bridge server is running first

**App shows "No config file specified"**
- Ensure you're running `npm run start` which includes the `--config config.json` parameter
- The CLI automatically handles this in production

**Connection errors when using with CLI**
- Verify the iOS Bridge server is running with `ios-bridge stream`
- Check that no firewall is blocking localhost connections
- Ensure an iOS device/simulator is connected and available

**Window sizing issues**
- The app automatically scales to fit your screen
- Device dimensions are read from the config file
- Use View menu to toggle fullscreen or always-on-top

## Development

### Quick Development Start
```bash
# Setup
npm install

# Basic development mode
npm run dev

# Development with session override
npm run dev -- --session-id=your-session-id

# Development with multiple overrides
npm run dev -- --session-id=abc123 --server-host=192.168.0.101 --quality=ultra --fullscreen
```

### Development Features
- ✅ **Live reloading** when files change
- ✅ **Chrome DevTools** for debugging (Ctrl+Shift+I or F12)
- ✅ **Command line overrides** for testing different configurations
- ✅ **Enhanced logging** and debugging
- ✅ **WebRTC and WebSocket testing**

### Command Line Overrides
Override any config.json value from command line:

| Option | Description | Example |
|--------|-------------|---------|
| `--session-id` | Override session ID | `--session-id=abc123` |
| `--server-host` | Override server hostname | `--server-host=192.168.0.101` |
| `--server-port` | Override server port | `--server-port=8000` |
| `--quality` | Override streaming quality | `--quality=ultra` |
| `--fullscreen` | Start in fullscreen | `--fullscreen` |
| `--always-on-top` | Keep window on top | `--always-on-top` |

**Quality options:** `low`, `medium`, `high`, `ultra`

### Development Workflow
1. **Get available sessions:** `ios-bridge list`
2. **Start development:** `npm run dev -- --session-id=YOUR_SESSION`
3. **Open DevTools:** Press `F12` or `Ctrl+Shift+I`
4. **Test WebSocket mode:** Default streaming mode
5. **Test WebRTC mode:** Click "🚀 WebRTC Stream" button
6. **Make changes:** Files auto-reload on save
7. **Test production:** `npm run build` then `ios-bridge stream <session-id>`

### Documentation
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Comprehensive development guide
- **[DEV-COMMANDS.md](DEV-COMMANDS.md)** - Quick command reference

### Contributing
1. Install dependencies: `npm install`
2. Run in development mode: `npm run dev -- --session-id=YOUR_SESSION`
3. Developer tools open automatically with enhanced logging
4. Make changes to files in `src/`
5. Changes reload automatically - no manual refresh needed