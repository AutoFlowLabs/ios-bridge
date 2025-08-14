# iOS Bridge CLI Installation Guide

Complete guide for installing and using the iOS Bridge CLI with integrated desktop app across all platforms.

## Table of Contents

1. [Quick Installation](#quick-installation)
2. [Platform-Specific Instructions](#platform-specific-instructions) 
3. [First Time Usage](#first-time-usage)
4. [Advanced Installation](#advanced-installation)
5. [Development Installation](#development-installation)
6. [Troubleshooting](#troubleshooting)
7. [Uninstallation](#uninstallation)

---

## Quick Installation

### ⚡ One-Command Install (Recommended)

```bash
pip install ios-bridge-cli
```

**That's it!** 🎉 

The CLI includes:
- ✅ Command-line interface for iOS device control
- ✅ Auto-downloading desktop app (no additional setup needed)
- ✅ All dependencies bundled
- ✅ Cross-platform support (macOS/Windows/Linux)

### First Launch

```bash
# Start with desktop interface (automatically downloads desktop app)
ios-bridge desktop

# Or start with web interface
ios-bridge stream
```

**First time desktop usage will show:**
```
🔍 iOS Bridge Desktop not found or outdated
🏗️ Downloading iOS Bridge Desktop for macOS...
████████████████████████████████████████ 25.4MB / 25.4MB
✅ iOS Bridge Desktop installed successfully
🚀 Starting iOS Bridge Desktop
```

---

## Platform-Specific Instructions

### 🍎 macOS

#### Prerequisites
- **macOS 10.15** (Catalina) or later
- **Python 3.8+** (check with `python3 --version`)
- **Xcode Command Line Tools**: `xcode-select --install`

#### Installation
```bash
# Install Python CLI
pip3 install ios-bridge-cli

# First desktop app usage (auto-downloads)
ios-bridge desktop
```

**Note:** Desktop app will be cached in `~/Library/Caches/ios-bridge/` for future use.

#### macOS Security
When first launching the desktop app, macOS may show a security warning:

1. **If you see "Cannot be opened because it is from an unidentified developer":**
   - Go to **System Preferences → Security & Privacy**
   - Click **"Allow"** next to the blocked app
   - Or run: `xattr -d com.apple.quarantine ~/Library/Caches/ios-bridge/desktop-apps/*/iOS\ Bridge.app`

### 🪟 Windows

#### Prerequisites
- **Windows 10** or later (Windows 11 recommended)
- **Python 3.8+** from [python.org](https://python.org) 
  - ✅ Make sure to check "Add Python to PATH" during installation

#### Installation
```bash
# Open Command Prompt or PowerShell
pip install ios-bridge-cli

# First desktop app usage (auto-downloads)
ios-bridge desktop
```

**Note:** Desktop app will be cached in `%LOCALAPPDATA%/ios-bridge/cache/` for future use.

#### Windows Defender
Windows may scan the downloaded desktop app:
- This is normal and safe
- First launch may take extra time due to scanning
- Consider adding the cache folder to Windows Defender exclusions for faster launches

### 🐧 Linux

#### Prerequisites
- **Ubuntu 20.04+**, **Fedora 34+**, or equivalent
- **Python 3.8+**: `sudo apt install python3 python3-pip` (Ubuntu)

#### Installation
```bash
# Install CLI
pip3 install ios-bridge-cli

# First desktop app usage (auto-downloads)
ios-bridge desktop
```

**Note:** Desktop app will be cached in `~/.cache/ios-bridge/` for future use.

#### Linux Permissions
Make downloaded app executable (usually automatic):
```bash
chmod +x ~/.cache/ios-bridge/desktop-apps/*/ios-bridge-desktop
```

---

## First Time Usage

### 1. Connect iOS Device
```bash
# List available devices
ios-bridge list

# Should show something like:
# iPhone 15 Pro (17.1) - 00008110-001234567890ABCD
# iPad Pro (17.1) - 00008020-001234567890EFGH
```

### 2. Start Streaming

**Desktop App (Recommended):**
```bash
ios-bridge desktop
```

**Web Interface:**
```bash
ios-bridge stream
# Open browser to: http://localhost:8000
```

**Select specific device:**
```bash
ios-bridge desktop --device "iPhone 15 Pro"
```

### 3. Usage Examples

```bash
# Desktop mode with specific device and quality
ios-bridge desktop --device "iPhone 15 Pro" --quality high

# Web mode on custom port
ios-bridge stream --port 9000

# Help and options
ios-bridge --help
ios-bridge desktop --help
```

---

## Advanced Installation

### Virtual Environment (Recommended for Development)

```bash
# Create isolated environment
python3 -m venv ios-bridge-env
source ios-bridge-env/bin/activate  # On Windows: ios-bridge-env\Scripts\activate

# Install in virtual environment
pip install ios-bridge-cli

# Use as normal
ios-bridge desktop
```

### Global Installation with pipx

```bash
# Install pipx if not available
pip install pipx

# Install iOS Bridge CLI globally
pipx install ios-bridge-cli

# Use from anywhere
ios-bridge desktop
```

### Upgrade to Latest Version

```bash
# Upgrade CLI
pip install --upgrade ios-bridge-cli

# Desktop app will auto-update to match CLI version
ios-bridge desktop  # Downloads new version if needed
```

---

## Development Installation

For developers who want to contribute or modify the code:

### From Source
```bash
# Clone repository
git clone https://github.com/your-username/ios-bridge.git
cd ios-bridge/ios-bridge-cli

# Install in development mode
pip install -e .

# Install Node.js dependencies for bundled Electron app
cd ios_bridge_cli/electron_app
npm install

# Run in development mode (uses bundled source)
ios-bridge desktop  # Automatically uses development mode
```

### Development vs Production Behavior

**Development Mode (from source):**
- Uses bundled Electron source code
- Requires Node.js and npm
- Enables live development
- Auto-detected when running from source directory

**Production Mode (from PyPI):**
- Downloads pre-built desktop apps
- No Node.js requirement
- Cached for performance
- Auto-updates with CLI version

---

## Troubleshooting

### Desktop App Download Issues

**Problem:** Desktop app fails to download
```bash
# Check internet connection
curl -I https://github.com

# Clear cache and retry
python3 -c "from ios_bridge_cli.app_manager import ElectronAppManager; ElectronAppManager().clear_cache()"
ios-bridge desktop

# Use verbose mode for debugging
ios-bridge desktop --verbose
```

**Problem:** "No Node.js found" error in development mode
```bash
# Install Node.js from nodejs.org, then:
cd ios_bridge_cli/electron_app
npm install
```

### iOS Device Connection Issues

**Problem:** No devices found
```bash
# Check idb installation
python3 -c "import subprocess; subprocess.run(['idb', 'list-targets'])"

# Install idb if missing
pip install fb-idb

# Check iOS device connection
idb list-targets
```

**Problem:** Device not responding
```bash
# Restart iOS device
# Reconnect USB cable
# Trust computer on iOS device when prompted

# Check device status
ios-bridge list --verbose
```

### Permission Issues

**macOS:** Gatekeeper blocking app
```bash
sudo xattr -r -d com.apple.quarantine ~/Library/Caches/ios-bridge/
```

**Linux:** Executable permissions
```bash
chmod +x ~/.cache/ios-bridge/desktop-apps/*/ios-bridge-desktop
```

**Windows:** Antivirus blocking
- Add iOS Bridge cache folder to antivirus exclusions
- Temporarily disable real-time protection during first download

### Cache Issues

**Clear all cached data:**
```bash
# Clear desktop app cache
python3 -c "from ios_bridge_cli.app_manager import ElectronAppManager; ElectronAppManager().clear_cache()"

# Clear pip cache
pip cache purge

# Reinstall
pip install --force-reinstall ios-bridge-cli
```

### Getting Help

**Check app status:**
```bash
ios-bridge --version
python3 -c "from ios_bridge_cli.app_manager import ElectronAppManager; print(ElectronAppManager().get_app_info())"
```

**Enable verbose logging:**
```bash
ios-bridge desktop --verbose
ios-bridge stream --verbose
```

**Report issues:**
- GitHub Issues: [https://github.com/your-username/ios-bridge/issues](https://github.com/your-username/ios-bridge/issues)
- Include iOS Bridge version, platform, and error messages
- Use `--verbose` flag and include full output

---

## Uninstallation

### Complete Removal

```bash
# Uninstall CLI
pip uninstall ios-bridge-cli

# Remove cached desktop apps (optional)
# macOS
rm -rf ~/Library/Caches/ios-bridge/

# Windows
rmdir /s "%LOCALAPPDATA%\ios-bridge"

# Linux
rm -rf ~/.cache/ios-bridge/
```

### Keep Desktop Apps (for reinstallation)

```bash
# Only uninstall CLI, keep cached apps
pip uninstall ios-bridge-cli

# Reinstalling will reuse cached desktop apps
pip install ios-bridge-cli
```

---

## FAQ

**Q: Do I need Node.js installed?**
A: No, not for normal usage. The CLI downloads pre-built desktop apps automatically.

**Q: How much disk space does it use?**
A: CLI: ~5MB, Desktop app cache: ~25-30MB per platform, total: ~35MB

**Q: Can I use it offline?**
A: Yes, after first download. Desktop apps are cached locally.

**Q: How do I update?**
A: `pip install --upgrade ios-bridge-cli` - desktop apps auto-update to match.

**Q: Does it work with iOS Simulator?**
A: Yes, it works with both physical devices and iOS Simulator.

**Q: Is it safe?**
A: Yes, it's open source. Desktop apps are signed and distributed via GitHub releases.

---

**Need help?** Check our [GitHub Issues](https://github.com/your-username/ios-bridge/issues) or start with `ios-bridge --help`