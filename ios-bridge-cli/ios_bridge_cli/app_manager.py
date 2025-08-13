"""
Electron app manager for the desktop streaming interface
"""
import os
import sys
import subprocess
import time
import json
import tempfile
import shutil
import psutil
from typing import Dict, Optional, Any
from pathlib import Path

from .exceptions import ElectronAppError


class ElectronAppManager:
    """Manages the Electron desktop application"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.process: Optional[subprocess.Popen] = None
        self.config_file: Optional[str] = None
        self.app_path = self._get_app_path()
    
    def _get_app_path(self) -> str:
        """Get the path to the bundled Electron app"""
        # Get the package directory
        package_dir = Path(__file__).parent
        
        # Always use the electron_app directory as the source
        # Don't look for dist directory as it might create circular paths
        electron_app_path = package_dir / "electron_app"
        
        return str(electron_app_path)
    
    def _ensure_app_exists(self):
        """Ensure the Electron app exists, install dependencies if necessary"""
        app_source_path = Path(self.app_path)
        
        # Check if we have package.json and node_modules
        if not (app_source_path / "package.json").exists():
            if self.verbose:
                print("📦 Electron app template not found, creating...")
            self._create_app_template()
        
        if not (app_source_path / "node_modules").exists():
            if self.verbose:
                print("📦 Installing Electron dependencies...")
            self._install_dependencies()
    
    def _install_dependencies(self):
        """Install npm dependencies"""
        try:
            app_source_path = Path(self.app_path)
            env = os.environ.copy()
            
            subprocess.run(
                ["npm", "install"],
                cwd=app_source_path,
                check=True,
                env=env,
                capture_output=not self.verbose
            )
            
        except subprocess.CalledProcessError as e:
            raise ElectronAppError(f"Failed to install dependencies: {e}")
        except FileNotFoundError:
            raise ElectronAppError("npm not found. Please install Node.js and npm")
    
    def _build_app(self):
        """Build the Electron app"""
        try:
            app_source_path = Path(self.app_path)
            
            # Check if we have package.json
            if not (app_source_path / "package.json").exists():
                # Copy the template app files first
                self._create_app_template()
            
            # Install dependencies and build
            env = os.environ.copy()
            
            if self.verbose:
                print("📦 Installing Electron dependencies...")
            
            subprocess.run(
                ["npm", "install"],
                cwd=app_source_path,
                check=True,
                env=env,
                capture_output=not self.verbose
            )
            
            if self.verbose:
                print("🏗️ Building Electron app...")
            
            # First ensure dist directory doesn't already exist to prevent nested builds
            dist_path = app_source_path / "dist"
            if dist_path.exists():
                if self.verbose:
                    print("🧹 Cleaning existing dist directory...")
                shutil.rmtree(dist_path)
            
            subprocess.run(
                ["npm", "run", "build"],
                cwd=app_source_path,
                check=True,
                env=env,
                capture_output=not self.verbose
            )
            
        except subprocess.CalledProcessError as e:
            raise ElectronAppError(f"Failed to build Electron app: {e}")
        except FileNotFoundError:
            raise ElectronAppError("npm not found. Please install Node.js and npm")
    
    def _create_app_template(self):
        """Create the Electron app template if it doesn't exist"""
        app_source_path = Path(self.app_path)
        
        # Copy electron app files from package
        package_dir = Path(__file__).parent
        electron_src = package_dir / "electron_app"
        
        if electron_src.exists():
            if self.verbose:
                print(f"📂 Copying Electron app template to {app_source_path}")
            
            # Create directory if it doesn't exist
            app_source_path.mkdir(parents=True, exist_ok=True)
            
            # Copy all files
            for item in electron_src.rglob('*'):
                if item.is_file():
                    rel_path = item.relative_to(electron_src)
                    dest_path = app_source_path / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
        else:
            raise ElectronAppError("Electron app template not found in package")
    
    def start(self, config: Dict[str, Any]) -> int:
        """Start the Electron app with the given configuration"""
        try:
            self._ensure_app_exists()
            
            # Create temporary config file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False,
                prefix='ios_bridge_config_'
            ) as f:
                json.dump(config, f, indent=2)
                self.config_file = f.name
            
            # Always run in development mode to ensure source changes take effect
            executable = "electron"
            args = [str(executable), str(self.app_path), "--config", self.config_file]
            
            if self.verbose:
                print(f"🚀 Starting Electron app: {' '.join(args)}")
            
            # Start the process - always show output for debugging
            self.process = subprocess.Popen(
                args,
                cwd=self.app_path,
                stdout=None,  # Always show stdout
                stderr=None   # Always show stderr
            )
            
            # Wait for the process to complete
            return_code = self.process.wait()
            
            if return_code != 0 and self.verbose:
                stdout, stderr = self.process.communicate()
                if stderr:
                    print(f"Electron app error: {stderr.decode()}")
            
            return return_code
            
        except FileNotFoundError:
            raise ElectronAppError(
                "Electron not found. Please install Electron globally: npm install -g electron"
            )
        except Exception as e:
            raise ElectronAppError(f"Failed to start Electron app: {e}")
        finally:
            self._cleanup()
    
    def stop(self):
        """Stop the Electron app"""
        if self.process:
            try:
                # Gracefully terminate
                self.process.terminate()
                
                # Wait for termination
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    self.process.kill()
                    self.process.wait()
                
                if self.verbose:
                    print("✅ Electron app stopped")
                    
            except Exception as e:
                if self.verbose:
                    print(f"Error stopping Electron app: {e}")
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