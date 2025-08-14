# iOS Bridge CLI Installation Guide

## Quick Installation

```bash
pip install ios-bridge-cli
```

## Prerequisites

1. **Python 3.8+**
   ```bash
   python --version  # Should be 3.8 or higher
   ```

2. **Node.js and npm** (for Electron app)
   ```bash
   node --version
   npm --version
   ```
   Install from: https://nodejs.org/

3. **Running iOS Bridge Server**
   - The CLI connects to an existing iOS Bridge server instance
   - Default server URL: `http://localhost:8000`

## Installation Methods

### Method 1: Install from PyPI (Recommended)

```bash
pip install ios-bridge-cli
```

### Method 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/AutoFlowLabs/ios-bridge-cli
cd ios-bridge-cli

# Install in development mode
pip install -e .

# Or build and install
python build.py
pip install dist/ios_bridge_cli-*.whl
```

### Method 3: Install from Wheel

```bash
# Download the latest wheel from releases
pip install ios_bridge_cli-1.0.0-py3-none-any.whl
```

## Verification

After installation, verify the CLI is working:

```bash
# Check version
ios-bridge version

# List available sessions (requires running server)
ios-bridge list --server http://localhost:8000

# Test connection
ios-bridge info <session_id> --server http://localhost:8000
```

## First Run

On first run, the CLI will:

1. **Download Electron dependencies** (if not already present)
2. **Build the desktop app** (may take a few minutes)
3. **Launch the streaming window**

```bash
# Start streaming a session
ios-bridge stream abc123 --server http://localhost:8000
```

## Configuration

### Server URL

Specify your iOS Bridge server URL:

```bash
ios-bridge stream <session_id> --server https://your-server.com:8443
```

### Quality Settings

Choose video quality:

```bash
ios-bridge stream <session_id> --quality ultra  # low, medium, high, ultra
```

### Window Options

```bash
ios-bridge stream <session_id> --fullscreen     # Start in fullscreen
ios-bridge stream <session_id> --always-on-top  # Keep window on top
```

## Troubleshooting

### Common Issues

#### 1. "ios-bridge command not found"

```bash
# Check if installed
pip show ios-bridge-cli

# Reinstall
pip install --force-reinstall ios-bridge-cli

# Check PATH
echo $PATH
```

#### 2. "Node.js/npm not found"

Install Node.js from https://nodejs.org/ and ensure it's in your PATH.

#### 3. "Connection failed"

```bash
# Check if iOS Bridge server is running
curl http://localhost:8000/health

# Check firewall settings
# Ensure ports 8000 and WebSocket ports are accessible
```

#### 4. "Electron app build failed"

```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
cd ~/.local/lib/python*/site-packages/ios_bridge_cli/electron_app
rm -rf node_modules package-lock.json
npm install
```

#### 5. "Session not found"

```bash
# List available sessions
ios-bridge list --server http://localhost:8000

# Check session ID format
ios-bridge info <full-session-id> --server http://localhost:8000
```

### Debug Mode

Run with verbose output:

```bash
ios-bridge --verbose stream <session_id>
```

### Logs

Check logs:

- **macOS**: `~/Library/Logs/iOS Bridge Desktop/`
- **Linux**: `~/.local/share/iOS Bridge Desktop/logs/`
- **Windows**: `%APPDATA%/iOS Bridge Desktop/logs/`

## Uninstallation

```bash
pip uninstall ios-bridge-cli
```

## Development Setup

```bash
# Clone repository
git clone https://github.com/AutoFlowLabs/ios-bridge-cli
cd ios-bridge-cli

# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Build Electron app
cd ios_bridge_cli/electron_app
npm install
npm run build

# Run in development mode
ios-bridge --verbose stream <session_id>
```

## System Requirements

- **Operating System**: macOS 10.14+, Linux (Ubuntu 18.04+), Windows 10+
- **Python**: 3.8 or higher
- **RAM**: 2GB minimum, 4GB recommended
- **Network**: Stable connection to iOS Bridge server
- **Display**: 1024x768 minimum resolution

## Support

- **Documentation**: https://github.com/AutoFlowLabs/ios-bridge-cli
- **Issues**: https://github.com/AutoFlowLabs/ios-bridge-cli/issues
- **Discussions**: https://github.com/AutoFlowLabs/ios-bridge-cli/discussions