"""
Electron app manager with auto-download functionality for desktop streaming interface
"""
import os
import subprocess
import time
import json
import tempfile
import shutil
import signal
from packaging import version
import platform
from typing import Dict, Optional, Any
from pathlib import Path
import requests
import zipfile
import tarfile

from .exceptions import ElectronAppError


class ElectronAppManager:
    """Manages the Electron desktop application with auto-download functionality"""
    
    # GitHub release configuration
    GITHUB_REPO = "AutoFlowLabs/ios-bridge"  # Update with your repo
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}"
    
    # App binary names by platform
    APP_BINARIES = {
        "Darwin": {
            "arm64": "ios-bridge-desktop-mac-arm64.zip",
            "x86_64": "ios-bridge-desktop-mac-x64.zip"
        },
        "Windows": {
            "AMD64": "ios-bridge-desktop-windows-x64.zip",
            "x86_64": "ios-bridge-desktop-windows-x64.zip"
        },
        "Linux": {
            "x86_64": "ios-bridge-desktop-linux-x64.zip",
            "aarch64": "ios-bridge-desktop-linux-arm64.zip"
        }
    }
    
    def __init__(self, verbose: bool = False, dev_mode: bool = False):
        self.verbose = verbose
        self.dev_mode = dev_mode  # Use bundled app for development
        self.process: Optional[subprocess.Popen] = None
        self.config_file: Optional[str] = None
        self.app_cache_dir = self._get_cache_dir()
        self.current_version = self._get_current_cli_version()
    
    def _get_cache_dir(self) -> Path:
        """Get the cache directory for downloaded apps"""
        if platform.system() == "Darwin":
            cache_dir = Path.home() / "Library" / "Caches" / "ios-bridge"
        elif platform.system() == "Windows":
            cache_dir = Path.home() / "AppData" / "Local" / "ios-bridge" / "cache"
        else:  # Linux
            cache_dir = Path.home() / ".cache" / "ios-bridge"
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def _get_current_cli_version(self) -> str:
        """Get the current CLI version"""
        try:
            from . import __version__
            return __version__
        except ImportError:
            return "1.0.0"  # Fallback version
    
    def _get_platform_info(self) -> tuple[str, str]:
        """Get platform and architecture information"""
        system = platform.system()
        machine = platform.machine().lower()
        
        # Normalize architecture names
        arch_map = {
            "arm64": "arm64",
            "aarch64": "aarch64", 
            "x86_64": "x86_64",
            "amd64": "AMD64",
            "intel": "x86_64"
        }
        
        arch = arch_map.get(machine, machine)
        return system, arch
    
    def _get_app_binary_name(self) -> str:
        """Get the binary name for current platform"""
        system, arch = self._get_platform_info()
        
        if system not in self.APP_BINARIES:
            raise ElectronAppError(f"Unsupported platform: {system}")
        
        platform_binaries = self.APP_BINARIES[system]
        if arch not in platform_binaries:
            # Try fallback architectures
            if system == "Darwin" and arch not in platform_binaries:
                arch = "arm64" if arch in ["arm64", "aarch64"] else "x86_64"
            elif system == "Windows" and arch not in platform_binaries:
                arch = "AMD64"
            elif system == "Linux" and arch not in platform_binaries:
                arch = "x86_64"
        
        if arch not in platform_binaries:
            raise ElectronAppError(f"Unsupported architecture {arch} for {system}")
        
        return platform_binaries[arch]
    
    def _get_app_executable_path(self) -> Path:
        """Get the path to the executable app"""
        # First try to find any existing version
        desktop_apps_dir = self.app_cache_dir / "desktop-apps"
        if desktop_apps_dir.exists():
            for version_dir in desktop_apps_dir.iterdir():
                if version_dir.is_dir() and version_dir.name.startswith("v"):
                    app_path = self._get_app_path_for_version(version_dir)
                    if app_path.exists():
                        return app_path
        
        # Fallback to current version
        app_dir = self.app_cache_dir / "desktop-apps" / f"v{self.current_version}"
        return self._get_app_path_for_version(app_dir)
    
    def _get_app_path_for_version(self, app_dir: Path) -> Path:
        """Get app path for a specific version directory"""
        system = platform.system()
        
        if system == "Darwin":
            # Try different possible locations for macOS
            possible_paths = [
                app_dir / "iOS Bridge.app",
                app_dir / "mac-arm64" / "iOS Bridge.app",
                app_dir / "mac-x64" / "iOS Bridge.app",
            ]
        elif system == "Windows":
            # Try different possible locations for Windows
            possible_paths = [
                app_dir / "iOS Bridge.exe", 
                app_dir / "win-unpacked" / "iOS Bridge.exe",
                app_dir / "win-ia32-unpacked" / "iOS Bridge.exe",
            ]
        else:  # Linux
            # Try different possible locations for Linux
            possible_paths = [
                app_dir / "ios-bridge-desktop",
                app_dir / "linux-unpacked" / "ios-bridge-desktop",
                app_dir / "linux-x64-unpacked" / "ios-bridge-desktop",
            ]
        
        # Return the first path that exists
        for path in possible_paths:
            if path.exists():
                return path
        
        # Return the default if none exist
        return possible_paths[0]
    
    def _app_exists_and_valid(self) -> bool:
        """Check if the app exists and is valid"""
        app_path = self._get_app_executable_path()
        
        if self.verbose:
            print(f"🔍 Checking app at: {app_path}")
        
        if not app_path.exists():
            if self.verbose:
                print(f"🔍 App not found at: {app_path}")
            return False
        
        # Check if executable is actually executable
        if not os.access(app_path, os.X_OK):
            if self.verbose:
                print(f"🔍 App not executable: {app_path}")
            return False
        
        if self.verbose:
            print(f"✅ App executable found at: {app_path}")
        
        # Check version file exists (but don't require exact match)
        version_file = app_path.parent / ".version"
        if self.verbose:
            print(f"🔍 Looking for version file at: {version_file}")
            print(f"🔍 Directory contents: {list(app_path.parent.iterdir()) if app_path.parent.exists() else 'Directory does not exist'}")
        
        if not version_file.exists():
            if self.verbose:
                print(f"🔍 No version file at: {version_file}")
            return False
        
        try:
            with open(version_file, 'r') as f:
                cached_version = f.read().strip()
            
            if self.verbose:
                print(f"🔍 Read version from file: '{cached_version}'")
            
            # Check if we have a valid version and if it's up to date
            if not cached_version or len(cached_version.split('.')) < 2:
                if self.verbose:
                    print(f"🔍 Invalid version format: '{cached_version}'")
                return False
            
            # Check if there's a newer version available
            try:
                latest_release = self._get_latest_release()
                latest_version = latest_release.get("tag_name", f"v{self.current_version}").lstrip("v")
                
                if version.parse(cached_version) < version.parse(latest_version):
                    if self.verbose:
                        print(f"🔄 App version {cached_version} is outdated. Latest: {latest_version}")
                    return False
                
                if self.verbose:
                    print(f"✅ Found valid app version: {cached_version} (latest: {latest_version})")
                return True
                
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Could not check for updates: {e}")
                    print(f"✅ Using cached app version: {cached_version}")
                # If we can't check for updates, use the cached version
                return True
        except Exception as e:
            if self.verbose:
                print(f"🔍 Could not read version file: {e}")
            return False
    
    def _download_with_progress(self, url: str, dest_path: Path, description: str):
        """Download file with progress indicator"""
        if self.verbose:
            print(f"🏗️ {description}...")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(dest_path, 'wb') as f:
            if total_size > 0 and self.verbose:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        percent = int(50 * downloaded / total_size)
                        print(f"\r{'█' * percent}{'░' * (50 - percent)} {downloaded / 1024 / 1024:.1f}MB / {total_size / 1024 / 1024:.1f}MB", end='', flush=True)
                print()  # New line after progress
            else:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        
        if self.verbose:
            print(f"✅ Download completed: {dest_path}")
    
    def _extract_app(self, archive_path: Path, extract_to: Path, version: str = None):
        """Extract downloaded app archive"""
        if self.verbose:
            print(f"📦 Extracting {archive_path.name}...")
        
        extract_to.mkdir(parents=True, exist_ok=True)
        
        if archive_path.suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        elif archive_path.suffix in ['.tar', '.gz', '.tgz']:
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(extract_to)
        else:
            raise ElectronAppError(f"Unsupported archive format: {archive_path.suffix}")
        
        # Write version file to the same location where we'll look for it later
        version_to_write = version or self.current_version
        
        # Write version file to extraction root
        version_file_root = extract_to / ".version"
        with open(version_file_root, 'w') as f:
            f.write(version_to_write)
        if self.verbose:
            print(f"📝 Version file written to root: {version_file_root}")
        
        # Write version file to all possible platform-specific subdirectories
        # This ensures _app_exists_and_valid can find it regardless of extraction structure
        system = platform.system()
        
        possible_subdirs = []
        if system == "Darwin":
            possible_subdirs = ["mac-arm64", "mac-x64"]
        elif system == "Windows":
            possible_subdirs = ["win-unpacked", "win-ia32-unpacked"]
        else:  # Linux
            possible_subdirs = ["linux-unpacked", "linux-x64-unpacked"]
        
        for subdir in possible_subdirs:
            subdir_path = extract_to / subdir
            if subdir_path.exists() or True:  # Create even if doesn't exist yet
                subdir_path.mkdir(parents=True, exist_ok=True)
                version_file_sub = subdir_path / ".version"
                with open(version_file_sub, 'w') as f:
                    f.write(version_to_write)
                if self.verbose:
                    print(f"📝 Version file written to subdir: {version_file_sub}")
        
        # Make Linux/macOS executables executable
        system, _ = self._get_platform_info()
        if system in ["Linux", "Darwin"]:
            # Find and make executables executable
            for item in extract_to.rglob("*"):
                if item.is_file() and (
                    item.name.startswith("ios-bridge-desktop") or
                    item.suffix == ".app" or
                    "iOS Bridge" in str(item)
                ):
                    try:
                        import stat
                        current_permissions = item.stat().st_mode
                        item.chmod(current_permissions | stat.S_IEXEC | stat.S_IXUSR | stat.S_IXGRP)
                        if self.verbose:
                            print(f"🔧 Made executable: {item}")
                    except Exception as e:
                        if self.verbose:
                            print(f"⚠️  Could not make {item} executable: {e}")
        
        if self.verbose:
            print(f"✅ Extraction completed")
    
    def _get_latest_release(self) -> dict:
        """Get the latest release information from GitHub"""
        try:
            # Try to get the latest release from GitHub API
            api_url = f"{self.GITHUB_API_URL}/releases/latest"
            if self.verbose:
                print(f"🔗 Fetching latest release from: {api_url}")
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            if self.verbose:
                print(f"✅ Found latest release: {release_data.get('tag_name', 'Unknown')}")
            
            return release_data
        except requests.RequestException as e:
            if self.verbose:
                print(f"⚠️  Failed to fetch latest release from GitHub API: {e}")
                print(f"🔗 Attempted URL: {self.GITHUB_API_URL}/releases/latest")
            
            # Fallback to current CLI version
            fallback_version = self.current_version
            if self.verbose:
                print(f"🔄 Using fallback version: v{fallback_version}")
            
            return {
                "tag_name": f"v{fallback_version}",
                "assets": [
                    {
                        "name": self._get_app_binary_name(),
                        "browser_download_url": f"https://github.com/{self.GITHUB_REPO}/releases/download/v{fallback_version}/{self._get_app_binary_name()}"
                    }
                ]
            }
    
    def _download_app(self):
        """Download the appropriate Electron app for the current platform"""
        try:
            release = self._get_latest_release()
            binary_name = self._get_app_binary_name()
            
            # Get version from release
            release_version = release.get("tag_name", f"v{self.current_version}").lstrip("v")
            
            # Find the asset for our platform
            asset_url = None
            for asset in release.get("assets", []):
                if asset["name"] == binary_name:
                    asset_url = asset["browser_download_url"]
                    break
            
            if not asset_url:
                raise ElectronAppError(f"No release found for {binary_name}")
            
            # Download to temporary location
            download_dir = self.app_cache_dir / "downloads"
            download_dir.mkdir(exist_ok=True)
            
            archive_path = download_dir / binary_name
            self._download_with_progress(
                asset_url, 
                archive_path, 
                f"Downloading iOS Bridge Desktop for {platform.system()}"
            )
            
            # Extract to app directory using the actual release version
            app_dir = self.app_cache_dir / "desktop-apps" / f"v{release_version}"
            if app_dir.exists():
                shutil.rmtree(app_dir)
            
            self._extract_app(archive_path, app_dir, release_version)
            
            # Make executable on Unix systems
            if platform.system() in ["Linux", "Darwin"]:
                app_path = self._get_app_executable_path()
                if app_path.exists():
                    if platform.system() == "Darwin":
                        # For macOS .app bundles, make the executable inside executable
                        executable = app_path / "Contents" / "MacOS" / "iOS Bridge"
                        if executable.exists():
                            executable.chmod(0o755)
                    else:
                        # For Linux binaries
                        app_path.chmod(0o755)
            
            # Clean up download
            archive_path.unlink(missing_ok=True)
            
            if self.verbose:
                print(f"✅ iOS Bridge Desktop installed successfully")
            
        except Exception as e:
            raise ElectronAppError(f"Failed to download Electron app: {e}")
    
    def _ensure_app_exists(self):
        """Ensure the Electron app exists, download if necessary"""
        if not self._app_exists_and_valid():
            if self.verbose:
                print("🔍 iOS Bridge Desktop not found or outdated")
            self._download_app()
    
    def _fallback_to_bundled_app(self):
        """Fallback to bundled Electron app if download fails"""
        package_dir = Path(__file__).parent
        electron_app_path = package_dir / "electron_app"
        
        if not electron_app_path.exists():
            raise ElectronAppError("No bundled Electron app available and download failed")
        
        if self.verbose:
            print("📦 Using bundled Electron app (requires Node.js)")
        
        # Install dependencies if needed
        if not (electron_app_path / "node_modules").exists():
            if self.verbose:
                print("📦 Installing Electron dependencies...")
            try:
                subprocess.run(
                    ["npm", "install"],
                    cwd=electron_app_path,
                    check=True,
                    capture_output=not self.verbose
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise ElectronAppError("Failed to install dependencies. Please install Node.js and npm")
        
        return str(electron_app_path)
    
    def start(self, config: Dict[str, Any]) -> int:
        """Start the Electron app with the given configuration"""
        try:
            # In development mode, always use bundled app
            if self.dev_mode:
                if self.verbose:
                    print("🔧 Development mode: using bundled Electron app")
                app_path = self._fallback_to_bundled_app()
                use_downloaded = False
            else:
                # Production mode: try to download app, fallback to bundled
                try:
                    self._ensure_app_exists()
                    app_path = self._get_app_executable_path()
                    use_downloaded = True
                except ElectronAppError as e:
                    if self.verbose:
                        print(f"⚠️  Download failed: {e}")
                    
                    # In production mode, don't fallback to bundled app
                    # because it requires Node.js/electron which users might not have
                    raise ElectronAppError(
                        f"Failed to download Electron app and no bundled fallback available in production mode.\n"
                        f"Please check your internet connection or use the web interface at your server URL.\n"
                        f"Original error: {e}"
                    )
            
            # Create temporary config file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False,
                prefix='ios_bridge_config_'
            ) as f:
                json.dump(config, f, indent=2)
                self.config_file = f.name
            
            # Launch the app
            if use_downloaded:
                args = self._get_downloaded_app_args(app_path, self.config_file)
            else:
                args = ["electron", str(app_path), "--config", self.config_file]
            
            if self.verbose:
                print(f"🚀 Starting iOS Bridge Desktop: {' '.join(str(arg) for arg in args[:2])}")
            
            # Start the process
            stdout_target = None if self.verbose else subprocess.DEVNULL
            stderr_target = None  # Always show stderr for critical errors
            
            self.process = subprocess.Popen(
                args,
                cwd=str(app_path.parent) if use_downloaded else app_path,
                stdout=stdout_target,
                stderr=stderr_target,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Wait for the process to complete
            try:
                return_code = self.process.wait()
            except KeyboardInterrupt:
                if self.verbose:
                    print("\n🛑 Ctrl+C detected, stopping iOS Bridge Desktop...")
                self.stop()
                
                # Give the process time to cleanup before forcing exit
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if self.verbose:
                        print("🛑 Force terminating desktop app...")
                    self.process.kill()
                
                return 0
            
            if return_code != 0 and self.verbose:
                print(f"iOS Bridge Desktop exited with code {return_code}")
            
            return return_code
            
        except Exception as e:
            raise ElectronAppError(f"Failed to start iOS Bridge Desktop: {e}")
        finally:
            self._cleanup()
    
    def _get_downloaded_app_args(self, app_path: Path, config_file: str) -> list:
        """Get command line arguments for downloaded app"""
        system = platform.system()
        
        if system == "Darwin":
            # macOS .app bundle - execute the binary directly instead of using 'open'
            # This ensures proper argument passing like on Linux
            binary_path = app_path / "Contents" / "MacOS" / "iOS Bridge"
            return [str(binary_path), "--config", config_file]
        elif system == "Windows":
            # Windows .exe
            return [str(app_path), "--config", config_file]
        else:  # Linux
            # Linux executable
            return [str(app_path), "--config", config_file]
    
    def stop(self):
        """Stop the Electron app"""
        if self.process:
            try:
                pid = self.process.pid
                
                # Try graceful termination first
                self.process.terminate()
                
                # Wait for termination
                try:
                    self.process.wait(timeout=2)
                    if self.verbose:
                        print("✅ iOS Bridge Desktop stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    if self.verbose:
                        print("⚡ Force stopping iOS Bridge Desktop...")
                    
                    # Kill the process group if possible
                    try:
                        if hasattr(os, 'killpg'):
                            os.killpg(os.getpgid(pid), signal.SIGTERM)
                            time.sleep(0.5)
                            try:
                                os.killpg(os.getpgid(pid), signal.SIGKILL)
                            except ProcessLookupError:
                                pass  # Process already terminated
                        else:
                            self.process.kill()
                        self.process.wait()
                    except ProcessLookupError:
                        # Process already terminated
                        pass
                    
                    if self.verbose:
                        print("✅ iOS Bridge Desktop stopped")
                    
            except Exception as e:
                if self.verbose:
                    print(f"Error stopping iOS Bridge Desktop: {e}")
            finally:
                self.process = None
        
        self._cleanup()
    
    def _cleanup(self):
        """Clean up temporary files"""
        if self.config_file and os.path.exists(self.config_file):
            try:
                os.unlink(self.config_file)
                self.config_file = None
            except Exception as e:
                if self.verbose:
                    print(f"Error cleaning up config file: {e}")
    
    def is_running(self) -> bool:
        """Check if the Electron app is running"""
        return self.process is not None and self.process.poll() is None
    
    def get_app_info(self) -> dict:
        """Get information about the installed app"""
        return {
            "version": self.current_version,
            "cache_dir": str(self.app_cache_dir),
            "app_exists": self._app_exists_and_valid(),
            "app_path": str(self._get_app_executable_path()),
            "platform": f"{platform.system()} {platform.machine()}"
        }
    
    def clear_cache(self):
        """Clear the app cache"""
        if self.app_cache_dir.exists():
            shutil.rmtree(self.app_cache_dir)
            self.app_cache_dir.mkdir(parents=True, exist_ok=True)
            if self.verbose:
                print("✅ App cache cleared")