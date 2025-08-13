#!/usr/bin/env python3
"""
Build script for iOS Bridge CLI
Builds the Electron app and prepares the Python package for distribution
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """Run a command and return the result"""
    print(f"🔨 Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd, 
            check=check, 
            capture_output=True, 
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return e


def check_dependencies():
    """Check if required dependencies are installed"""
    dependencies = [
        ("node", "Node.js is required. Install from https://nodejs.org/"),
        ("npm", "npm is required (comes with Node.js)"),
        ("python", "Python 3.8+ is required"),
    ]
    
    missing = []
    
    for dep, message in dependencies:
        try:
            subprocess.run([dep, "--version"], capture_output=True, check=True)
            print(f"✅ {dep} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ {dep} is not installed or not in PATH")
            missing.append(message)
    
    if missing:
        print("\n❌ Missing dependencies:")
        for msg in missing:
            print(f"   - {msg}")
        sys.exit(1)


def build_electron_app():
    """Build the Electron desktop app"""
    print("\n📦 Building Electron app...")
    
    electron_path = Path(__file__).parent / "ios_bridge_cli" / "electron_app"
    
    if not electron_path.exists():
        print(f"❌ Electron app directory not found: {electron_path}")
        sys.exit(1)
    
    # Install dependencies
    run_command(["npm", "install"], cwd=electron_path)
    
    # Build for current platform
    current_platform = platform.system().lower()
    
    build_commands = {
        "darwin": ["npm", "run", "build-mac"],
        "windows": ["npm", "run", "build-win"],
        "linux": ["npm", "run", "build-linux"]
    }
    
    build_cmd = build_commands.get(current_platform, ["npm", "run", "build"])
    run_command(build_cmd, cwd=electron_path)
    
    print("✅ Electron app built successfully")


def build_python_package():
    """Build the Python package"""
    print("\n📦 Building Python package...")
    
    # Clean previous builds
    build_dirs = ["build", "dist", "*.egg-info"]
    for pattern in build_dirs:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                print(f"🧹 Cleaning {path}")
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
    
    # Build package
    run_command([sys.executable, "-m", "build"])
    
    print("✅ Python package built successfully")


def test_installation():
    """Test the built package"""
    print("\n🧪 Testing installation...")
    
    # Find the built wheel
    dist_path = Path("dist")
    wheels = list(dist_path.glob("*.whl"))
    
    if not wheels:
        print("❌ No wheel file found in dist/")
        return
    
    wheel_file = wheels[0]
    print(f"📦 Testing wheel: {wheel_file}")
    
    # Install in a test environment
    test_cmd = [
        sys.executable, "-m", "pip", "install", 
        str(wheel_file), "--force-reinstall", "--user"
    ]
    
    result = run_command(test_cmd, check=False)
    
    if result.returncode == 0:
        print("✅ Package installed successfully")
        
        # Test CLI command
        test_result = run_command(["ios-bridge", "version"], check=False)
        if test_result.returncode == 0:
            print("✅ CLI command works correctly")
        else:
            print("❌ CLI command failed")
    else:
        print("❌ Package installation failed")


def main():
    """Main build process"""
    print("🏗️  iOS Bridge CLI Build Script")
    print("=" * 40)
    
    # Check dependencies
    check_dependencies()
    
    # Build Electron app
    build_electron_app()
    
    # Build Python package
    build_python_package()
    
    # Test installation
    test_installation()
    
    print("\n🎉 Build completed successfully!")
    print("\n📦 Distribution files:")
    dist_path = Path("dist")
    if dist_path.exists():
        for file in dist_path.glob("*"):
            print(f"   - {file}")
    
    print("\n📚 Installation:")
    print("   pip install dist/ios_bridge_cli-*.whl")
    
    print("\n🚀 Usage:")
    print("   ios-bridge stream <session_id> --server http://localhost:8000")


if __name__ == "__main__":
    main()