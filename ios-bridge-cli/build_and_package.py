#!/usr/bin/env python3
"""
Cross-platform build and packaging script for iOS Bridge CLI
Handles Python package building, Electron app packaging, and distribution preparation
"""

import os
import sys
import platform
import subprocess
import shutil
import json
from pathlib import Path
import argparse
from typing import List, Dict, Any

class BuildManager:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.electron_app_dir = project_root / "ios_bridge_cli" / "electron_app"
        self.dist_dir = project_root / "dist"
        self.platform_name = platform.system().lower()
        self.arch = platform.machine().lower()
        
        # Create dist directory
        self.dist_dir.mkdir(exist_ok=True)
        
        print(f"🏗️ Build Manager initialized")
        print(f"📁 Project root: {self.project_root}")
        print(f"💻 Platform: {self.platform_name} ({self.arch})")
    
    def check_dependencies(self) -> bool:
        """Check if all required tools are installed"""
        required_tools = {
            'python': ['python', '--version'],
            'node': ['node', '--version'],
            'npm': ['npm', '--version'],
        }
        
        missing = []
        for tool, cmd in required_tools.items():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                version = result.stdout.strip()
                print(f"✅ {tool}: {version}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing.append(tool)
                print(f"❌ {tool} not found")
        
        if missing:
            print(f"\n❌ Missing dependencies: {', '.join(missing)}")
            print("Please install the missing tools and try again.")
            return False
        
        return True
    
    def install_node_dependencies(self) -> bool:
        """Install Node.js dependencies for Electron app"""
        print("\n📦 Installing Node.js dependencies...")
        
        try:
            # Change to electron app directory
            original_cwd = os.getcwd()
            os.chdir(self.electron_app_dir)
            
            # Install dependencies
            subprocess.run(['npm', 'install'], check=True)
            print("✅ Node.js dependencies installed")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Node.js dependencies: {e}")
            return False
            
        finally:
            os.chdir(original_cwd)
    
    def build_python_package(self) -> bool:
        """Build Python package"""
        print("\n🐍 Building Python package...")
        
        try:
            # Clean previous builds
            for pattern in ['build', 'dist', '*.egg-info']:
                for path in self.project_root.glob(pattern):
                    if path.is_dir():
                        shutil.rmtree(path)
                        print(f"🧹 Cleaned {path}")
            
            # Build package
            subprocess.run([
                sys.executable, '-m', 'build', 
                '--wheel', '--sdist', str(self.project_root)
            ], check=True, cwd=self.project_root)
            
            print("✅ Python package built successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build Python package: {e}")
            return False
    
    def build_electron_app(self, platforms: List[str] = None) -> bool:
        """Build Electron app for specified platforms"""
        print("\n⚡ Building Electron app...")
        
        if platforms is None:
            platforms = [self.platform_name]
        
        try:
            # Change to electron app directory
            original_cwd = os.getcwd()
            os.chdir(self.electron_app_dir)
            
            # Build for each platform
            for platform_target in platforms:
                print(f"🏗️ Building for {platform_target}...")
                
                build_cmd = ['npm', 'run']
                if platform_target == 'darwin':
                    build_cmd.append('build-mac')
                elif platform_target == 'win32':
                    build_cmd.append('build-win')
                elif platform_target == 'linux':
                    build_cmd.append('build-linux')
                else:
                    print(f"⚠️ Unknown platform: {platform_target}")
                    continue
                
                subprocess.run(build_cmd, check=True)
                print(f"✅ Built for {platform_target}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build Electron app: {e}")
            return False
            
        finally:
            os.chdir(original_cwd)
    
    def copy_electron_builds(self) -> bool:
        """Copy Electron builds to main dist directory"""
        print("\n📦 Copying Electron builds...")
        
        electron_dist = self.electron_app_dir / "dist"
        if not electron_dist.exists():
            print("❌ No Electron builds found")
            return False
        
        try:
            # Create platform-specific directories
            platform_dist = self.dist_dir / "electron" / self.platform_name
            platform_dist.mkdir(parents=True, exist_ok=True)
            
            # Copy all files from electron dist
            for item in electron_dist.iterdir():
                target = platform_dist / item.name
                if item.is_dir():
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)
                print(f"📁 Copied {item.name}")
            
            print("✅ Electron builds copied")
            return True
            
        except Exception as e:
            print(f"❌ Failed to copy Electron builds: {e}")
            return False
    
    def create_installer_scripts(self) -> bool:
        """Create platform-specific installer scripts"""
        print("\n📝 Creating installer scripts...")
        
        scripts_dir = self.dist_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        # macOS installer script
        macos_script = scripts_dir / "install-macos.sh"
        macos_script.write_text('''#!/bin/bash
set -e

echo "🍎 iOS Bridge CLI Installer for macOS"
echo "======================================"

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.8+ is required but not installed."
    echo "Please install Python from https://python.org"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Found Python $python_version"

# Install iOS Bridge CLI
echo "📦 Installing iOS Bridge CLI..."
pip3 install --upgrade ios-bridge-cli

# Install Electron app (if available)
if [ -d "./electron/darwin" ]; then
    echo "⚡ Installing Electron app..."
    sudo cp -R ./electron/darwin/*.app /Applications/
    echo "✅ Electron app installed to /Applications"
fi

echo ""
echo "🎉 Installation complete!"
echo "Run 'ios-bridge --help' to get started."
''')
        macos_script.chmod(0o755)
        
        # Windows installer script
        windows_script = scripts_dir / "install-windows.bat"
        windows_script.write_text('''@echo off
echo 🪟 iOS Bridge CLI Installer for Windows
echo =======================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 3.8+ is required but not installed.
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found

REM Install iOS Bridge CLI
echo 📦 Installing iOS Bridge CLI...
pip install --upgrade ios-bridge-cli

REM Install Electron app (if available)
if exist "electron\\win32" (
    echo ⚡ Electron app available in electron\\win32
    echo Please run the installer from that directory
)

echo.
echo 🎉 Installation complete!
echo Run 'ios-bridge --help' to get started.
pause
''')
        
        # Linux installer script
        linux_script = scripts_dir / "install-linux.sh"
        linux_script.write_text('''#!/bin/bash
set -e

echo "🐧 iOS Bridge CLI Installer for Linux"
echo "====================================="

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.8+ is required but not installed."
    echo "Install with: sudo apt install python3 python3-pip (Ubuntu/Debian)"
    echo "Install with: sudo yum install python3 python3-pip (RHEL/CentOS)"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Found Python $python_version"

# Install iOS Bridge CLI
echo "📦 Installing iOS Bridge CLI..."
pip3 install --upgrade ios-bridge-cli

# Install Electron app (if available)
if [ -d "./electron/linux" ]; then
    echo "⚡ Installing Electron app..."
    # Copy to user applications directory
    mkdir -p ~/.local/share/applications
    if [ -f "./electron/linux"/*.AppImage ]; then
        cp ./electron/linux/*.AppImage ~/ios-bridge-desktop.AppImage
        chmod +x ~/ios-bridge-desktop.AppImage
        echo "✅ Electron app installed as ~/ios-bridge-desktop.AppImage"
    fi
fi

echo ""
echo "🎉 Installation complete!"
echo "Run 'ios-bridge --help' to get started."
''')
        linux_script.chmod(0o755)
        
        print("✅ Installer scripts created")
        return True
    
    def create_release_package(self) -> bool:
        """Create final release packages"""
        print("\n📦 Creating release packages...")
        
        try:
            release_dir = self.dist_dir / "release"
            release_dir.mkdir(exist_ok=True)
            
            # Get version from pyproject.toml
            import tomllib
            with open(self.project_root / "pyproject.toml", "rb") as f:
                config = tomllib.load(f)
                version = config["project"]["version"]
            
            # Create platform-specific packages
            platforms = ['macos', 'windows', 'linux']
            
            for platform_name in platforms:
                platform_release = release_dir / f"ios-bridge-cli-{version}-{platform_name}"
                platform_release.mkdir(exist_ok=True)
                
                # Copy Python wheel (universal)
                python_dist = self.project_root / "dist"
                if python_dist.exists():
                    for wheel in python_dist.glob("*.whl"):
                        shutil.copy2(wheel, platform_release)
                        print(f"📁 Added {wheel.name}")
                
                # Copy Electron app if exists
                electron_platform = "darwin" if platform_name == "macos" else platform_name
                electron_path = self.dist_dir / "electron" / electron_platform
                if electron_path.exists():
                    electron_dest = platform_release / "electron"
                    if electron_dest.exists():
                        shutil.rmtree(electron_dest)
                    shutil.copytree(electron_path, electron_dest)
                    print(f"📁 Added Electron app for {platform_name}")
                
                # Copy installer script
                scripts_dir = self.dist_dir / "scripts"
                if platform_name == "macos":
                    script_name = "install-macos.sh"
                elif platform_name == "windows":
                    script_name = "install-windows.bat"
                else:
                    script_name = "install-linux.sh"
                
                script_path = scripts_dir / script_name
                if script_path.exists():
                    shutil.copy2(script_path, platform_release / "install" + script_path.suffix)
                
                # Create README for the package
                readme_content = f"""# iOS Bridge CLI v{version} - {platform_name.title()}

## Installation

### Quick Install
Run the installer script:
- macOS/Linux: `chmod +x install.sh && ./install.sh`
- Windows: `install.bat`

### Manual Install
1. Install Python 3.8+
2. Install CLI: `pip install ios-bridge-cli-{version}-py3-none-any.whl`
3. Install Electron app from the `electron/` directory

## Usage
After installation, run:
```
ios-bridge --help
```

## Support
- GitHub: https://github.com/AutoFlowLabs/ios-bridge-cli
- Documentation: https://github.com/AutoFlowLabs/ios-bridge-cli/wiki
"""
                (platform_release / "README.md").write_text(readme_content)
                
                print(f"✅ Created {platform_name} package")
            
            print("✅ Release packages created")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create release packages: {e}")
            return False
    
    def generate_checksums(self) -> bool:
        """Generate checksums for release files"""
        print("\n🔐 Generating checksums...")
        
        try:
            import hashlib
            
            release_dir = self.dist_dir / "release"
            if not release_dir.exists():
                print("❌ No release directory found")
                return False
            
            checksums = {}
            
            for item in release_dir.rglob("*"):
                if item.is_file() and item.suffix in ['.whl', '.dmg', '.exe', '.AppImage', '.deb', '.rpm']:
                    # Calculate SHA256
                    sha256_hash = hashlib.sha256()
                    with open(item, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(chunk)
                    
                    rel_path = str(item.relative_to(release_dir))
                    checksums[rel_path] = sha256_hash.hexdigest()
                    print(f"🔐 {rel_path}: {sha256_hash.hexdigest()[:16]}...")
            
            # Write checksums file
            checksums_file = release_dir / "checksums.txt"
            with open(checksums_file, "w") as f:
                f.write("# iOS Bridge CLI Release Checksums (SHA256)\\n\\n")
                for file_path, checksum in sorted(checksums.items()):
                    f.write(f"{checksum}  {file_path}\\n")
            
            print(f"✅ Checksums written to {checksums_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to generate checksums: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Build and package iOS Bridge CLI")
    parser.add_argument("--python-only", action="store_true", help="Build Python package only")
    parser.add_argument("--electron-only", action="store_true", help="Build Electron app only")
    parser.add_argument("--platforms", nargs="+", choices=["darwin", "win32", "linux"], 
                       help="Platforms to build for")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent
    
    print("🚀 iOS Bridge CLI Build & Package Tool")
    print("=" * 50)
    
    # Initialize build manager
    build_manager = BuildManager(project_root)
    
    # Check dependencies
    if not build_manager.check_dependencies():
        return 1
    
    # Install Node.js dependencies if not skipped
    if not args.skip_deps and not args.python_only:
        if not build_manager.install_node_dependencies():
            return 1
    
    # Build Python package
    if not args.electron_only:
        if not build_manager.build_python_package():
            return 1
    
    # Build Electron app
    if not args.python_only:
        platforms = args.platforms or [platform.system().lower()]
        if not build_manager.build_electron_app(platforms):
            return 1
        
        if not build_manager.copy_electron_builds():
            return 1
    
    # Create installer scripts
    if not build_manager.create_installer_scripts():
        return 1
    
    # Create release packages
    if not build_manager.create_release_package():
        return 1
    
    # Generate checksums
    if not build_manager.generate_checksums():
        return 1
    
    print(f"\\n🎉 Build complete!")
    print(f"📁 Release packages: {build_manager.dist_dir / 'release'}")
    print(f"\\n📋 Next steps:")
    print(f"1. Test the packages on target platforms")
    print(f"2. Upload to GitHub releases")
    print(f"3. Publish Python package to PyPI: twine upload dist/*.whl")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())