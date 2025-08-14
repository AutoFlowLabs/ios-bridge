# iOS Bridge Desktop App

A desktop streaming client for iOS Bridge that provides a native desktop experience for iOS device streaming.

## Quick Start

### Development Mode
```bash
npm run dev
```
This opens the app with developer tools enabled.

### Production Mode
```bash
npm run start
```
This opens the app in production mode.

## Configuration

The app uses a `config.json` file to configure the connection and display settings:

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

1. Start the iOS Bridge server:
   ```bash
   ios-bridge stream
   ```

2. Update `config.json` with the correct server details

3. Start the desktop app:
   ```bash
   npm run start
   ```

The desktop app will automatically connect to the server and begin streaming the iOS device.

## Troubleshooting

**App shows "No config file specified"**
- Ensure you're running `npm run start` which includes the `--config config.json` parameter

**Connection errors**
- Verify the iOS Bridge server is running
- Check that serverHost and serverPort in config.json match your server settings
- Ensure the device is connected and streaming

**Window sizing issues**
- The app automatically scales to fit your screen
- Device dimensions are read from the config file
- Use View menu to toggle fullscreen or always-on-top

## Development

To contribute or modify the desktop app:

1. Install dependencies: `npm install`
2. Run in development mode: `npm run dev`
3. Developer tools will open automatically
4. Make changes to files in `src/`
5. Reload with Cmd/Ctrl+R to see changes