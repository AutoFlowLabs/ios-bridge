# iOS Bridge CLI Installation Guide

Complete guide for installing and using the iOS Bridge CLI across all platforms.

## Table of Contents

1. [Quick Installation](#quick-installation)
2. [Platform-Specific Instructions](#platform-specific-instructions)
3. [Manual Installation](#manual-installation)
4. [Development Installation](#development-installation)
5. [Troubleshooting](#troubleshooting)
6. [Uninstallation](#uninstallation)

---

## Quick Installation

### One-Command Install

```bash
# Install from PyPI (Python package only)
pip install ios-bridge-cli

# For full installation with desktop app, see platform-specific instructions below
```

### With Desktop App

Download the latest release from [GitHub Releases](https://github.com/your-org/ios-bridge/releases) and follow platform-specific instructions.

---

## Platform-Specific Instructions

### 🍎 macOS

#### Prerequisites
- macOS 10.15 (Catalina) or later
- Python 3.8+ (recommended: [python.org](https://python.org) installer)
- Xcode Command Line Tools: `xcode-select --install`

#### Installation Options

**Option 1: Package Installer (Recommended)**
1. Download `ios-bridge-cli-macos.tar.gz` from releases
2. Extract: `tar -xzf ios-bridge-cli-macos.tar.gz`
3. Run installer: `cd ios-bridge-cli-macos && chmod +x install.sh && ./install.sh`

**Option 2: Homebrew (if available)**
```bash
# Add tap (when published)
brew tap your-org/ios-bridge
brew install ios-bridge-cli
```

**Option 3: Python + Manual Desktop App**
```bash
# Install CLI
pip3 install ios-bridge-cli

# Download and install desktop app
# Drag iOS Bridge.app to Applications folder
```

#### Verification
```bash
ios-bridge --version
open -a "iOS Bridge"  # Launch desktop app
```

---

### 🪟 Windows

#### Prerequisites
- Windows 10 or later
- Python 3.8+ ([python.org](https://python.org) - check "Add to PATH")
- Microsoft Visual C++ Redistributable

#### Installation Options

**Option 1: Package Installer (Recommended)**
1. Download `ios-bridge-cli-windows.zip` from releases
2. Extract the ZIP file
3. Run `install.bat` as Administrator

**Option 2: Python + Manual Desktop App**
```cmd
# Install CLI
pip install ios-bridge-cli

# Download and run desktop app installer
# Or extract portable version
```

#### Verification
```cmd
ios-bridge --version
# Desktop app will be in Start Menu or run the .exe directly
```

---

### 🐧 Linux

#### Prerequisites
- Ubuntu 18.04+ / Debian 10+ / CentOS 8+ / Fedora 32+
- Python 3.8+
- Basic development tools

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv build-essential
```

**CentOS/RHEL/Fedora:**
```bash
sudo dnf install python3 python3-pip python3-devel gcc gcc-c++
# or on older systems: sudo yum install python3 python3-pip python3-devel gcc gcc-c++
```

#### Installation Options

**Option 1: Package Installer (Recommended)**
1. Download `ios-bridge-cli-linux.tar.gz` from releases
2. Extract: `tar -xzf ios-bridge-cli-linux.tar.gz`
3. Run installer: `cd ios-bridge-cli-linux && chmod +x install.sh && ./install.sh`

**Option 2: Python + Manual Desktop App**
```bash
# Install CLI
pip3 install ios-bridge-cli

# Make AppImage executable and run
chmod +x ios-bridge-desktop.AppImage
./ios-bridge-desktop.AppImage
```

#### Verification
```bash
ios-bridge --version
./ios-bridge-desktop.AppImage  # Or installed AppImage path
```

---

## Manual Installation

### Python Package Only

```bash
# Create virtual environment (recommended)
python3 -m venv ios-bridge-env
source ios-bridge-env/bin/activate  # Linux/macOS
# or
ios-bridge-env\Scripts\activate  # Windows

# Install
pip install ios-bridge-cli

# Verify
ios-bridge --help
```

### From Source

```bash
# Clone repository
git clone https://github.com/your-org/ios-bridge.git
cd ios-bridge/ios-bridge-cli

# Install in development mode
pip install -e .

# Build desktop app (requires Node.js)
cd ios_bridge_cli/electron_app
npm install
npm run build
```

---

## Development Installation

### For Contributors

```bash
# Clone and setup development environment
git clone https://github.com/your-org/ios-bridge.git
cd ios-bridge/ios-bridge-cli

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Setup Electron development
cd ios_bridge_cli/electron_app
npm install

# Run in development mode
npm run dev
```

### Building from Source

```bash
# Build Python package
python -m build

# Build Electron app for all platforms
python build_and_package.py

# Build for specific platform
python build_and_package.py --platforms darwin win32 linux
```

---

## Configuration

### First-Time Setup

1. **Launch the application:**
   ```bash
   ios-bridge
   ```

2. **Configure server connection:**
   ```bash
   ios-bridge connect ws://your-server:8000
   ```

3. **Desktop app configuration:**
   - Launch desktop app
   - Enter server URL in connection dialog
   - Save connection for future use

### Environment Variables

```bash
# Server configuration
export IOS_BRIDGE_SERVER_URL="ws://localhost:8000"
export IOS_BRIDGE_API_KEY="your-api-key"

# Desktop app settings
export IOS_BRIDGE_WINDOW_WIDTH=1200
export IOS_BRIDGE_WINDOW_HEIGHT=800
export IOS_BRIDGE_LOG_LEVEL=INFO
```

### Configuration File

Create `~/.config/ios-bridge/config.json`:
```json
{
  "server_url": "ws://localhost:8000",
  "auto_connect": true,
  "window_settings": {
    "width": 1200,
    "height": 800,
    "always_on_top": false
  },
  "streaming": {
    "quality": "high",
    "fps": 60,
    "mode": "websocket"
  }
}
```

---

## Usage Examples

### CLI Usage

```bash
# Show help
ios-bridge --help

# Connect to server
ios-bridge connect ws://192.168.1.100:8000

# List available sessions
ios-bridge list-sessions

# Connect to specific session
ios-bridge connect-session abc123

# Launch desktop app
ios-bridge desktop
```

### Desktop App Usage

1. **Launch app:** Click iOS Bridge icon or run executable
2. **Connect:** Enter server URL (e.g., `ws://192.168.1.100:8000`)
3. **Select session:** Choose from available iOS simulator sessions
4. **Stream:** Interact with iOS simulator in real-time

### Advanced Usage

```bash
# Custom quality settings
ios-bridge connect ws://server:8000 --quality high --fps 60

# WebRTC mode for lower latency
ios-bridge connect ws://server:8000 --mode webrtc

# Export session recording
ios-bridge export-recording session_id output.mp4

# Batch operations
ios-bridge batch-install apps/*.ipa --session all
```

---

## Troubleshooting

### Common Issues

#### 1. Python Installation Issues

**Problem:** `ios-bridge: command not found`
```bash
# Check Python installation
python3 --version
pip3 --version

# Add pip install location to PATH
export PATH="$HOME/.local/bin:$PATH"  # Linux/macOS
# or check Windows PATH includes Python Scripts directory
```

#### 2. Desktop App Won't Launch

**macOS:**
```bash
# Check security settings
xattr -d com.apple.quarantine "/Applications/iOS Bridge.app"
# or allow in System Preferences > Security & Privacy
```

**Windows:**
```cmd
# Run as Administrator
# Check Windows Defender exclusions
# Verify Visual C++ Redistributable installed
```

**Linux:**
```bash
# Install additional dependencies
sudo apt install libglib2.0-0 libgtk-3-0 libx11-xcb1 libxcb-dri3-0

# Check permissions
chmod +x ios-bridge-desktop.AppImage
```

#### 3. Connection Issues

```bash
# Test server connectivity
curl -I http://your-server:8000/health

# Check firewall settings
# Verify server is running
# Check WebSocket support
```

#### 4. Performance Issues

```bash
# Lower quality settings
ios-bridge connect ws://server:8000 --quality medium --fps 30

# Try different streaming mode
ios-bridge connect ws://server:8000 --mode websocket

# Check system resources
ios-bridge system-info
```

### Log Files

**Locations:**
- macOS: `~/Library/Logs/ios-bridge/`
- Windows: `%APPDATA%/ios-bridge/logs/`
- Linux: `~/.local/share/ios-bridge/logs/`

**Viewing logs:**
```bash
# CLI logs
ios-bridge --verbose

# Desktop app logs
tail -f ~/Library/Logs/ios-bridge/main.log
```

### Getting Help

1. **Check documentation:** [GitHub Wiki](https://github.com/your-org/ios-bridge/wiki)
2. **Search issues:** [GitHub Issues](https://github.com/your-org/ios-bridge/issues)
3. **Report bugs:** Include logs, OS version, and steps to reproduce
4. **Community support:** Join Discord/Slack community

---

## Uninstallation

### Python Package

```bash
pip uninstall ios-bridge-cli
```

### Desktop Applications

**macOS:**
```bash
# Remove application
rm -rf "/Applications/iOS Bridge.app"

# Remove user data
rm -rf ~/Library/Application\ Support/ios-bridge
rm -rf ~/Library/Logs/ios-bridge
rm -rf ~/Library/Preferences/com.iosbridge.desktop.plist
```

**Windows:**
```cmd
# Uninstall via Control Panel > Programs
# or manually delete installation directory

# Remove user data
rmdir /s "%APPDATA%\ios-bridge"
```

**Linux:**
```bash
# Remove AppImage
rm ios-bridge-desktop.AppImage

# Remove user data
rm -rf ~/.local/share/ios-bridge
rm -rf ~/.config/ios-bridge
```

---

## Next Steps

After installation:

1. **Read the [Usage Guide](USAGE.md)** for detailed feature documentation
2. **Check [Server Setup](../README.md#server-setup)** for backend configuration
3. **Explore [Examples](examples/)** for integration patterns
4. **Join the community** for support and updates

---

## Support

- 📚 **Documentation:** [GitHub Wiki](https://github.com/your-org/ios-bridge/wiki)
- 🐛 **Bug Reports:** [GitHub Issues](https://github.com/your-org/ios-bridge/issues)
- 💬 **Community:** [Discord](https://discord.gg/ios-bridge) | [Slack](https://ios-bridge.slack.com)
- 📧 **Email:** support@iosbridge.dev