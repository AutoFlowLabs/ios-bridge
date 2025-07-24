import re
import subprocess
import json
import tempfile
import uuid
import time
import threading
import os
import shutil
import plistlib
from typing import Dict, List, Optional, Tuple, Union
from typing import List, Dict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import zipfile

@dataclass
class SimulatorDevice:
    """Represents an iOS simulator device"""
    name: str
    identifier: str
    runtime: str
    state: str
    udid: str

@dataclass
class InstalledApp:
    """Represents an installed app on simulator"""
    bundle_id: str
    app_name: str
    app_path: str
    installed_at: float
    app_type: str = "user"  # Add this field with default value

@dataclass
class SimulatorSession:
    """Represents a simulator session"""
    session_id: str
    device: SimulatorDevice
    udid: str
    device_type: str
    ios_version: str
    created_at: float
    pid: Optional[int] = None
    installed_apps: Dict[str, InstalledApp] = field(default_factory=dict)

class SimulatorState(Enum):
    SHUTDOWN = "Shutdown"
    BOOTED = "Booted"
    BOOTING = "Booting"
    SHUTTING_DOWN = "Shutting Down"

class iOSSimulatorManager:
    def __init__(self):
        self.active_sessions: Dict[str, SimulatorSession] = {}
        self.available_device_types = self._get_available_device_types()
        self.available_runtimes = self._get_available_runtimes()
        
    def _run_command(self, command: List[str]) -> Tuple[bool, str]:
        """Execute a shell command and return success status and output"""
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()
    
    def _get_available_device_types(self) -> Dict[str, str]:
        """Get all available device types"""
        success, output = self._run_command(['xcrun', 'simctl', 'list', 'devicetypes', '-j'])
        if not success:
            raise Exception(f"Failed to get device types: {output}")
        
        data = json.loads(output)
        device_types = {}
        
        for device_type in data.get('devicetypes', []):
            name = device_type.get('name', '')
            identifier = device_type.get('identifier', '')
            if 'iPhone' in name or 'iPad' in name:
                device_types[name] = identifier
                
        return device_types
    
    def _get_available_runtimes(self) -> Dict[str, str]:
        """Get all available iOS runtimes"""
        success, output = self._run_command(['xcrun', 'simctl', 'list', 'runtimes', '-j'])
        if not success:
            raise Exception(f"Failed to get runtimes: {output}")
        
        data = json.loads(output)
        runtimes = {}
        
        for runtime in data.get('runtimes', []):
            if runtime.get('isAvailable', False):
                name = runtime.get('name', '')
                identifier = runtime.get('identifier', '')
                if 'iOS' in name:
                    version = name.replace('iOS ', '')
                    runtimes[version] = identifier
                    
        return runtimes
    
    def list_available_configurations(self) -> Dict:
        """List all available device types and iOS versions"""
        return {
            'device_types': list(self.available_device_types.keys()),
            'ios_versions': list(self.available_runtimes.keys())
        }
    
    def _create_simulator_device(self, device_name: str, device_type: str, ios_version: str) -> str:
        """Create a new simulator device and return its UDID"""
        if device_type not in self.available_device_types:
            raise ValueError(f"Device type '{device_type}' not available")
        
        if ios_version not in self.available_runtimes:
            raise ValueError(f"iOS version '{ios_version}' not available")
        
        device_type_id = self.available_device_types[device_type]
        runtime_id = self.available_runtimes[ios_version]
        
        command = [
            'xcrun', 'simctl', 'create',
            device_name,
            device_type_id,
            runtime_id
        ]
        
        success, udid = self._run_command(command)
        if not success:
            raise Exception(f"Failed to create simulator: {udid}")
        
        return udid.strip()
    
    def _boot_simulator(self, udid: str) -> bool:
        """Boot a simulator device"""
        command = ['xcrun', 'simctl', 'boot', udid]
        success, output = self._run_command(command)
        
        if success:
            self._wait_for_boot(udid)
            subprocess.Popen(['open', '-a', 'Simulator', '--args', '-CurrentDeviceUDID', udid])
            return True
        else:
            print(f"Failed to boot simulator: {output}")
            return False
    
    def _wait_for_boot(self, udid: str, timeout: int = 60) -> bool:
        """Wait for simulator to fully boot"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            success, output = self._run_command(['xcrun', 'simctl', 'list', 'devices', '-j'])
            if success:
                data = json.loads(output)
                for runtime, devices in data.get('devices', {}).items():
                    for device in devices:
                        if device.get('udid') == udid:
                            if device.get('state') == 'Booted':
                                return True
            time.sleep(2)
        return False
    
    def _get_simulator_pid(self, udid: str) -> Optional[int]:
        """Get the process ID of a running simulator"""
        try:
            command = ['pgrep', '-f', f'CurrentDeviceUDID {udid}']
            success, output = self._run_command(command)
            if success and output:
                return int(output.split('\n')[0])
        except:
            pass
        return None
    
    def _extract_bundle_info_from_ipa(self, ipa_path: str) -> Tuple[str, str]:
        """Extract bundle ID and app name from IPA file"""
        import tempfile
        import zipfile
        
        if not os.path.exists(ipa_path):
            raise FileNotFoundError(f"IPA file not found: {ipa_path}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract IPA
            with zipfile.ZipFile(ipa_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find the app bundle
            payload_dir = os.path.join(temp_dir, 'Payload')
            if not os.path.exists(payload_dir):
                raise Exception("Invalid IPA file: No Payload directory found")
            
            app_dirs = [d for d in os.listdir(payload_dir) if d.endswith('.app')]
            if not app_dirs:
                raise Exception("Invalid IPA file: No .app bundle found")
            
            app_bundle = os.path.join(payload_dir, app_dirs[0])
            info_plist_path = os.path.join(app_bundle, 'Info.plist')
            
            if not os.path.exists(info_plist_path):
                raise Exception("Invalid IPA file: No Info.plist found")
            
            # Read Info.plist
            with open(info_plist_path, 'rb') as f:
                plist_data = plistlib.load(f)
            
            bundle_id = plist_data.get('CFBundleIdentifier', '')
            app_name = plist_data.get('CFBundleDisplayName') or plist_data.get('CFBundleName', '')
            
            if not bundle_id:
                raise Exception("Could not extract bundle ID from IPA")
            
            return bundle_id, app_name
    

    def _modify_app_for_simulator(self, app_bundle_path: str) -> bool:
        """
        Modify app bundle to make it compatible with iOS Simulator
        This removes problematic entitlements and modifies Info.plist
        """
        try:
            print("   🔧 Modifying app for simulator compatibility...")
            
            # Path to Info.plist
            info_plist_path = os.path.join(app_bundle_path, 'Info.plist')
            if not os.path.exists(info_plist_path):
                print(f"   ❌ Info.plist not found in app bundle")
                return False
            
            # Read and modify Info.plist
            with open(info_plist_path, 'rb') as f:
                plist_data = plistlib.load(f)
            
            # Remove problematic keys that can cause launch issues
            problematic_keys = [
                'UIDeviceFamily',  # Sometimes causes issues
                'UISupportedInterfaceOrientations~ipad',  # iPad specific
                'CFBundleURLTypes',  # URL schemes can cause issues
                'NSAppTransportSecurity',  # Network security
            ]
            
            # Modify UIDeviceFamily to support both iPhone and iPad
            if 'UIDeviceFamily' in plist_data:
                plist_data['UIDeviceFamily'] = [1, 2]  # iPhone and iPad
            
            # Ensure simulator-friendly settings
            plist_data['LSRequiresIPhoneOS'] = True
            
            # Remove or modify problematic orientations
            if 'UISupportedInterfaceOrientations' in plist_data:
                # Ensure basic orientations are supported
                orientations = plist_data['UISupportedInterfaceOrientations']
                if isinstance(orientations, list) and len(orientations) == 0:
                    plist_data['UISupportedInterfaceOrientations'] = [
                        'UIInterfaceOrientationPortrait'
                    ]
            
            # Write modified Info.plist
            with open(info_plist_path, 'wb') as f:
                plistlib.dump(plist_data, f)
            
            # Remove entitlements file if it exists
            entitlements_path = os.path.join(app_bundle_path, 'Entitlements.plist')
            if os.path.exists(entitlements_path):
                os.remove(entitlements_path)
                print("   🗑️  Removed Entitlements.plist")
            
            # Remove code signature (required for simulator)
            self._remove_code_signature(app_bundle_path)
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error modifying app: {str(e)}")
            return False
    
    def _remove_code_signature(self, app_bundle_path: str) -> bool:
        """Remove code signature from app bundle"""
        try:
            code_signature_path = os.path.join(app_bundle_path, '_CodeSignature')
            if os.path.exists(code_signature_path):
                shutil.rmtree(code_signature_path)
                print("   🗑️  Removed code signature")
            
            # Remove embedded mobileprovision
            mobileprovision_files = [
                'embedded.mobileprovision',
                'Embedded.mobileprovision'
            ]
            
            for mp_file in mobileprovision_files:
                mp_path = os.path.join(app_bundle_path, mp_file)
                if os.path.exists(mp_path):
                    os.remove(mp_path)
                    print(f"   🗑️  Removed {mp_file}")
            
            return True
        except Exception as e:
            print(f"   ❌ Error removing code signature: {str(e)}")
            return False
    
    def _resign_for_simulator(self, app_bundle_path: str) -> bool:
        """Re-sign app bundle for iOS Simulator (if codesign is available)"""
        try:
            # Check if codesign is available
            result = subprocess.run(['which', 'codesign'], capture_output=True, text=True)
            if result.returncode != 0:
                print("   ⚠️  codesign not available, skipping re-signing")
                return True
            
            print("   🔐 Re-signing app for simulator...")
            
            # Remove existing signature
            command = ['codesign', '--remove-signature', app_bundle_path]
            subprocess.run(command, capture_output=True, check=False)
            
            # Re-sign with ad-hoc signature
            command = [
                'codesign', 
                '--force', 
                '--sign', '-',  # Ad-hoc signature
                '--preserve-metadata=entitlements',
                '--deep',
                app_bundle_path
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ Successfully re-signed app")
                return True
            else:
                print(f"   ⚠️  Re-signing failed (continuing anyway): {result.stderr}")
                return True  # Continue even if re-signing fails
                
        except Exception as e:
            print(f"   ⚠️  Re-signing error (continuing anyway): {str(e)}")
            return True  # Continue even if re-signing fails
    
    def install_ipa(self, session_id: str, ipa_path: str, modify_for_simulator: bool = True) -> bool:
        """
        Install an IPA file to a simulator session with enhanced compatibility
        
        Args:
            session_id: The session ID of the target simulator
            ipa_path: Path to the IPA file to install
            modify_for_simulator: Whether to modify the app for simulator compatibility
            
        Returns:
            bool: Success status
        """
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            print(f"📱 Installing IPA to simulator session: {session_id[:8]}...")
            
            # Extract bundle info from IPA first
            bundle_id, app_name = self._extract_bundle_info_from_ipa(ipa_path)
            print(f"   App: {app_name} ({bundle_id})")
            
            # Create a temporary directory for modification
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract IPA
                print("   📦 Extracting IPA...")
                with zipfile.ZipFile(ipa_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find the .app bundle
                payload_dir = os.path.join(temp_dir, 'Payload')
                if not os.path.exists(payload_dir):
                    raise Exception("Invalid IPA file: No Payload directory found")
                
                app_dirs = [d for d in os.listdir(payload_dir) if d.endswith('.app')]
                if not app_dirs:
                    raise Exception("Invalid IPA file: No .app bundle found")
                
                app_bundle_path = os.path.join(payload_dir, app_dirs[0])
                
                # Modify app for simulator compatibility if requested
                if modify_for_simulator:
                    modification_success = self._modify_app_for_simulator(app_bundle_path)
                    if modification_success:
                        self._resign_for_simulator(app_bundle_path)
                
                # Try installing the modified .app bundle
                print(f"   💾 Installing modified app bundle...")
                command = ['xcrun', 'simctl', 'install', session.udid, app_bundle_path]
                success, output = self._run_command(command)
                
                if success:
                    # Add to installed apps tracking
                    installed_app = InstalledApp(
                        bundle_id=bundle_id,
                        app_name=app_name,
                        app_path=ipa_path,
                        installed_at=time.time(),
                        app_type="modified" if modify_for_simulator else "user"
                    )
                    session.installed_apps[bundle_id] = installed_app
                    
                    print(f"✅ Successfully installed {app_name}")
                    print(f"   Bundle ID: {bundle_id}")
                    print(f"   Type: {'Modified for simulator' if modify_for_simulator else 'Original'}")
                    return True
                else:
                    print(f"❌ Failed to install modified app: {output}")
                    
                    # Fallback: Try original IPA
                    if modify_for_simulator:
                        print("   🔄 Trying original IPA without modifications...")
                        return self.install_ipa(session_id, ipa_path, modify_for_simulator=False)
                    else:
                        return False
                        
        except Exception as e:
            print(f"❌ Error installing IPA: {str(e)}")
            return False
    
    def launch_app(self, session_id: str, bundle_id: str, wait_for_launch: bool = True, launch_args: Optional[List[str]] = None) -> bool:
        """
        Launch an installed app on the simulator with enhanced error handling
        
        Args:
            session_id: The session ID of the target simulator
            bundle_id: Bundle identifier of the app to launch
            wait_for_launch: Whether to wait and verify the launch
            launch_args: Optional launch arguments for the app
            
        Returns:
            bool: Success status
        """
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            print(f"🚀 Launching app: {bundle_id}")
            
            # First, check if app is installed
            if not self._is_app_installed(session.udid, bundle_id):
                print(f"❌ App {bundle_id} is not installed on this simulator")
                return False
            
            # Prepare launch command
            command = ['xcrun', 'simctl', 'launch']
            
            # Add wait flag if needed
            if wait_for_launch:
                command.append('--wait-for-debugger')
            
            command.extend([session.udid, bundle_id])
            
            # Add launch arguments if provided
            if launch_args:
                command.extend(launch_args)
            
            # Remove wait-for-debugger and try simple launch first
            simple_command = ['xcrun', 'simctl', 'launch', session.udid, bundle_id]
            if launch_args:
                simple_command.extend(launch_args)
            
            success, output = self._run_command(simple_command)
            
            if success:
                print(f"✅ Successfully launched app")
                if wait_for_launch:
                    # Give the app some time to start
                    time.sleep(2)
                    # Verify it's still running
                    if self._is_app_running(session.udid, bundle_id):
                        print(f"✅ App is running successfully")
                        return True
                    else:
                        print(f"⚠️  App launched but may have crashed")
                        return False
                return True
            else:
                print(f"❌ Failed to launch app: {output}")
                
                # Try alternative launch methods
                return self._try_alternative_launch_methods(session, bundle_id, launch_args)
                
        except Exception as e:
            print(f"❌ Error launching app: {str(e)}")
            return False
    
    def _is_app_installed(self, udid: str, bundle_id: str) -> bool:
        """Check if an app is installed on the simulator"""
        try:
            command = ['xcrun', 'simctl', 'get_app_container', udid, bundle_id]
            success, output = self._run_command(command)
            return success and output.strip() != ""
        except:
            return False
    
    def _is_app_running(self, udid: str, bundle_id: str) -> bool:
        """Check if an app is currently running on the simulator"""
        try:
            # This is a bit tricky - we can check the process list
            command = ['xcrun', 'simctl', 'spawn', udid, 'ps', 'aux']
            success, output = self._run_command(command)
            if success:
                # Look for the app's executable name in the process list
                app_name = bundle_id.split('.')[-1]  # Simple heuristic
                return app_name.lower() in output.lower()
            return False
        except:
            return False
    
    def _try_alternative_launch_methods(self, session: SimulatorSession, bundle_id: str, launch_args: Optional[List[str]] = None) -> bool:
        """Try alternative methods to launch the app"""
        
        print("   🔄 Trying alternative launch methods...")
        
        # Method 1: Launch with openurl
        try:
            print("   📱 Trying URL-based launch...")
            url_scheme = f"{bundle_id.split('.')[-1]}://"  # Simple heuristic
            command = ['xcrun', 'simctl', 'openurl', session.udid, url_scheme]
            success, output = self._run_command(command)
            if success:
                print("   ✅ URL-based launch succeeded")
                return True
        except:
            pass
        
        # Method 2: Try launching with different flags
        try:
            print("   🔧 Trying launch with different parameters...")
            command = ['xcrun', 'simctl', 'launch', '--console', session.udid, bundle_id]
            if launch_args:
                command.extend(launch_args)
            success, output = self._run_command(command)
            if success:
                print("   ✅ Console launch succeeded")
                return True
        except:
            pass
        
        # Method 3: Reset app's data and try again
        try:
            print("   🔄 Resetting app data and retrying...")
            # Get app container and clear it
            container_command = ['xcrun', 'simctl', 'get_app_container', session.udid, bundle_id, 'data']
            success, container_path = self._run_command(container_command)
            if success:
                # Clear app data
                data_path = container_path.strip()
                if os.path.exists(data_path):
                    for item in os.listdir(data_path):
                        item_path = os.path.join(data_path, item)
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                
                # Try launching again
                command = ['xcrun', 'simctl', 'launch', session.udid, bundle_id]
                success, output = self._run_command(command)
                if success:
                    print("   ✅ Launch after data reset succeeded")
                    return True
        except:
            pass
        
        print("   ❌ All alternative launch methods failed")
        return False
    
    def open_simulator_app(self, session_id: str, bundle_id: str) -> bool:
        """
        Alternative method: Open the simulator and simulate tapping the app icon
        This is useful when normal launch methods fail
        """
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            print(f"📱 Opening simulator and navigating to app: {bundle_id}")
            
            # Make sure Simulator.app is focused and showing our device
            command = ['open', '-a', 'Simulator', '--args', '-CurrentDeviceUDID', session.udid]
            subprocess.run(command, check=False)
            
            # Wait for simulator to focus
            time.sleep(2)
            
            # Get app container to verify it's installed
            if not self._is_app_installed(session.udid, bundle_id):
                print(f"❌ App {bundle_id} is not installed")
                return False
            
            print("✅ App is installed. You can now manually tap the app icon in the simulator.")
            print("   The simulator should be visible and focused on your screen.")
            return True
            
        except Exception as e:
            print(f"❌ Error opening simulator: {str(e)}")
            return False
    
    def get_app_logs(self, session_id: str, bundle_id: str, lines: int = 100) -> str:
        """Get recent logs for an app"""
        if session_id not in self.active_sessions:
            return "Session not found"
        
        session = self.active_sessions[session_id]
        
        try:
            # Get device logs filtered by bundle ID
            command = [
                'xcrun', 'simctl', 'spawn', session.udid, 
                'log', 'show', '--predicate', f'process == "{bundle_id}"', 
                '--last', f'{lines}m'
            ]
            success, output = self._run_command(command)
            
            if success:
                return output
            else:
                return f"Failed to get logs: {output}"
                
        except Exception as e:
            return f"Error getting logs: {str(e)}"
    
    def debug_app_installation(self, session_id: str, bundle_id: str) -> Dict:
        """Debug information for app installation issues"""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        debug_info = {}
        
        try:
            # Check if app is installed
            debug_info["is_installed"] = self._is_app_installed(session.udid, bundle_id)
            
            # Get app container path
            command = ['xcrun', 'simctl', 'get_app_container', session.udid, bundle_id]
            success, container_path = self._run_command(command)
            debug_info["container_path"] = container_path if success else "Not available"
            
            # Check app bundle structure
            if success and os.path.exists(container_path.strip()):
                app_path = container_path.strip()
                debug_info["app_exists"] = os.path.exists(app_path)
                if os.path.exists(app_path):
                    debug_info["app_contents"] = os.listdir(app_path)
                    
                    # Check Info.plist
                    info_plist = os.path.join(app_path, 'Info.plist')
                    debug_info["has_info_plist"] = os.path.exists(info_plist)
            
            # Check if app is running
            debug_info["is_running"] = self._is_app_running(session.udid, bundle_id)
            
            # Get recent logs
            debug_info["recent_logs"] = self.get_app_logs(session_id, bundle_id, 50)
            
            return debug_info
            
        except Exception as e:
            return {"error": str(e)}




    
    def uninstall_app(self, session_id: str, bundle_id: str) -> bool:
        """
        Uninstall an app from a simulator session
        
        Args:
            session_id: The session ID of the target simulator
            bundle_id: Bundle identifier of the app to uninstall
            
        Returns:
            bool: Success status
        """
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            print(f"🗑️  Uninstalling app from simulator session: {session_id[:8]}...")
            print(f"   Bundle ID: {bundle_id}")
            
            # First check if the app exists
            apps = self.list_installed_apps(session_id)
            app_exists = any(app['bundle_id'] == bundle_id for app in apps)
            
            if not app_exists:
                print(f"⚠️  App with bundle ID {bundle_id} not found on simulator")
                # Still try to uninstall in case it exists but wasn't listed
            
            # Uninstall the app
            command = ['xcrun', 'simctl', 'uninstall', session.udid, bundle_id]
            success, output = self._run_command(command)
            
            if success:
                # Remove from installed apps tracking
                if bundle_id in session.installed_apps:
                    app_name = session.installed_apps[bundle_id].app_name
                    del session.installed_apps[bundle_id]
                    print(f"✅ Successfully uninstalled {app_name}")
                else:
                    print(f"✅ Successfully uninstalled app with bundle ID: {bundle_id}")
                return True
            else:
                # Check if the error is because app doesn't exist
                if "not installed" in output.lower() or "not found" in output.lower():
                    print(f"⚠️  App was not installed: {bundle_id}")
                    # Remove from tracking if it was there
                    if bundle_id in session.installed_apps:
                        del session.installed_apps[bundle_id]
                    return True
                else:
                    print(f"❌ Failed to uninstall app: {output}")
                    return False
                
        except Exception as e:
            print(f"❌ Error uninstalling app: {str(e)}")
            return False



     
    def terminate_app(self, session_id: str, bundle_id: str) -> bool:
        """Terminate a running app on the simulator"""
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            print(f"🛑 Terminating app: {bundle_id}")
            command = ['xcrun', 'simctl', 'terminate', session.udid, bundle_id]
            success, output = self._run_command(command)
            
            if success:
                print(f"✅ Successfully terminated app")
                return True
            else:
                print(f"❌ Failed to terminate app: {output}")
                return False
                
        except Exception as e:
            print(f"❌ Error terminating app: {str(e)}")
            return False
    
    def push_file(self, session_id: str, local_path: str, device_path: str, bundle_id: Optional[str] = None) -> bool:
        """
        Push a file from host to simulator (similar to adb push)
        
        Args:
            session_id: The session ID of the target simulator
            local_path: Path to the local file on host machine
            device_path: Destination path on the simulator
            bundle_id: Optional bundle ID for app-specific operations
            
        Returns:
            bool: Success status
        """
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            if not os.path.exists(local_path):
                print(f"❌ Local file not found: {local_path}")
                return False
            
            print(f"📤 Pushing file to simulator...")
            print(f"   From: {local_path}")
            print(f"   To: {device_path}")
            
            # Different approaches based on destination
            if bundle_id:
                # Push to app's container
                command = ['xcrun', 'simctl', 'addmedia', session.udid, local_path]
                if device_path.startswith('/Documents') or 'Documents' in device_path:
                    # For app documents
                    success, output = self._push_to_app_container(session.udid, bundle_id, local_path, device_path)
                else:
                    success, output = self._run_command(command)
            else:
                # Push to simulator file system
                success, output = self._push_to_simulator_filesystem(session.udid, local_path, device_path)
            
            if success:
                print(f"✅ Successfully pushed file to simulator")
                return True
            else:
                print(f"❌ Failed to push file: {output}")
                return False
                
        except Exception as e:
            print(f"❌ Error pushing file: {str(e)}")
            return False
    
    def _push_to_app_container(self, udid: str, bundle_id: str, local_path: str, device_path: str) -> Tuple[bool, str]:
        """Push file to app's container directory"""
        try:
            # Get app container path
            command = ['xcrun', 'simctl', 'get_app_container', udid, bundle_id]
            success, container_path = self._run_command(command)
            
            if not success:
                return False, f"Could not get app container: {container_path}"
            
            # Construct full destination path
            if device_path.startswith('/'):
                device_path = device_path[1:]  # Remove leading slash
            
            full_dest_path = os.path.join(container_path.strip(), device_path)
            dest_dir = os.path.dirname(full_dest_path)
            
            # Create destination directory if it doesn't exist
            os.makedirs(dest_dir, exist_ok=True)
            
            # Copy the file
            shutil.copy2(local_path, full_dest_path)
            
            return True, f"File copied to {full_dest_path}"
            
        except Exception as e:
            return False, str(e)
    
    def _push_to_simulator_filesystem(self, udid: str, local_path: str, device_path: str) -> Tuple[bool, str]:
        """Push file to simulator's file system"""
        try:
            # Get simulator data path
            success, output = self._run_command(['xcrun', 'simctl', 'getenv', udid, 'SIMULATOR_ROOT'])
            
            if success:
                sim_root = output.strip()
            else:
                # Fallback: construct simulator path
                sim_root = f"~/Library/Developer/CoreSimulator/Devices/{udid}/data"
                sim_root = os.path.expanduser(sim_root)
            
            # Handle different destination types
            if device_path.startswith('/'):
                # Absolute path in simulator
                if device_path.startswith('/tmp') or device_path.startswith('/var/tmp'):
                    full_dest_path = os.path.join(sim_root, 'tmp', os.path.basename(local_path))
                elif device_path.startswith('/Documents'):
                    full_dest_path = os.path.join(sim_root, 'Documents', os.path.basename(local_path))
                else:
                    full_dest_path = os.path.join(sim_root, device_path.lstrip('/'))
            else:
                # Relative path, put in tmp
                full_dest_path = os.path.join(sim_root, 'tmp', device_path)
            
            # Create destination directory
            dest_dir = os.path.dirname(full_dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            
            # Copy the file
            shutil.copy2(local_path, full_dest_path)
            
            return True, f"File copied to {full_dest_path}"
            
        except Exception as e:
            return False, str(e)
    
    def pull_file(self, session_id: str, device_path: str, local_path: str, bundle_id: Optional[str] = None) -> bool:
        """
        Pull a file from simulator to host (similar to adb pull)
        
        Args:
            session_id: The session ID of the target simulator
            device_path: Path to the file on simulator
            local_path: Destination path on host machine
            bundle_id: Optional bundle ID for app-specific operations
            
        Returns:
            bool: Success status
        """
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            print(f"📥 Pulling file from simulator...")
            print(f"   From: {device_path}")
            print(f"   To: {local_path}")
            
            if bundle_id:
                success, output = self._pull_from_app_container(session.udid, bundle_id, device_path, local_path)
            else:
                success, output = self._pull_from_simulator_filesystem(session.udid, device_path, local_path)
            
            if success:
                print(f"✅ Successfully pulled file from simulator")
                return True
            else:
                print(f"❌ Failed to pull file: {output}")
                return False
                
        except Exception as e:
            print(f"❌ Error pulling file: {str(e)}")
            return False
    
    def _pull_from_app_container(self, udid: str, bundle_id: str, device_path: str, local_path: str) -> Tuple[bool, str]:
        """Pull file from app's container directory"""
        try:
            # Get app container path
            command = ['xcrun', 'simctl', 'get_app_container', udid, bundle_id]
            success, container_path = self._run_command(command)
            
            if not success:
                return False, f"Could not get app container: {container_path}"
            
            # Construct full source path
            if device_path.startswith('/'):
                device_path = device_path[1:]
            
            full_source_path = os.path.join(container_path.strip(), device_path)
            
            if not os.path.exists(full_source_path):
                return False, f"File not found: {full_source_path}"
            
            # Create local destination directory if needed
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # Copy the file
            shutil.copy2(full_source_path, local_path)
            
            return True, f"File copied from {full_source_path}"
            
        except Exception as e:
            return False, str(e)
    
    def _pull_from_simulator_filesystem(self, udid: str, device_path: str, local_path: str) -> Tuple[bool, str]:
        """Pull file from simulator's file system"""
        try:
            # Get simulator data path
            sim_root = os.path.expanduser(f"~/Library/Developer/CoreSimulator/Devices/{udid}/data")
            
            # Construct full source path
            if device_path.startswith('/'):
                full_source_path = os.path.join(sim_root, device_path.lstrip('/'))
            else:
                full_source_path = os.path.join(sim_root, 'tmp', device_path)
            
            if not os.path.exists(full_source_path):
                return False, f"File not found: {full_source_path}"
            
            # Create local destination directory if needed
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # Copy the file
            shutil.copy2(full_source_path, local_path)
            
            return True, f"File copied from {full_source_path}"
            
        except Exception as e:
            return False, str(e)
    

    def _parse_plist_output(self, plist_str: str) -> dict:
        try:
            # Remove surrounding whitespace
            content = plist_str.strip()

            # Fix dictionary braces
            content = content.replace('=', ':')
            content = content.replace(';', ',')

            # Replace Apple-style parentheses with brackets for arrays
            content = content.replace('(', '[').replace(')', ']')

            # Use regex to quote unquoted keys (basic version)
            content = re.sub(r'([,{]\s*)([A-Za-z0-9_.\-]+)(\s*):', r'\1"\2"\3:', content)

            # Use regex to quote unquoted string values (basic version)
            content = re.sub(r':\s*([A-Za-z0-9_\-./]+)(\s*[,\}])', r': "\1"\2', content)

            # Now it should resemble JSON
            return json.loads(content)

        except Exception as e:
            print(f"❌ Failed to parse plist output: {e}")
            return {}


    def list_installed_apps(self, session_id: str) -> List[Dict]:
        """List all installed apps on a simulator using shell pipe to convert plist to JSON"""
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return []

        session = self.active_sessions[session_id]

        try:
            # Run the full piped command using shell=True
            import subprocess
            
            full_command = f"xcrun simctl listapps '{session.udid}' | plutil -convert json -o - -- -"
            
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            
            json_output = result.stdout

            # Parse the JSON
            try:
                apps_data = json.loads(json_output)
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON: {e}")
                return []

            # Extract app information
            apps_list = []
            for bundle_id, app_info in apps_data.items():
                app_name = app_info.get('CFBundleDisplayName') or app_info.get('CFBundleName', 'Unknown')
                apps_list.append({
                    'bundle_id': bundle_id,
                    'app_name': app_name,
                    'app_type': app_info.get('ApplicationType', 'Unknown'),
                    'path': app_info.get('Path', ''),
                })

            return apps_list

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to run command: {e.stderr}")
            return []
        except Exception as e:
            print(f"❌ Error listing apps: {str(e)}")
            return []

          
    def get_app_container_path(self, session_id: str, bundle_id: str) -> Optional[str]:
        """Get the container path for a specific app"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        try:
            command = ['xcrun', 'simctl', 'get_app_container', session.udid, bundle_id]
            success, output = self._run_command(command)
            
            if success:
                return output.strip()
            else:
                return None
                
        except Exception as e:
            return None
    
    def add_photos(self, session_id: str, *photo_paths: str) -> bool:
        """Add photos to simulator's photo library"""
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            print(f"📷 Adding photos to simulator photo library...")
            
            for photo_path in photo_paths:
                if not os.path.exists(photo_path):
                    print(f"❌ Photo not found: {photo_path}")
                    continue
                
                command = ['xcrun', 'simctl', 'addmedia', session.udid, photo_path]
                success, output = self._run_command(command)
                
                if success:
                    print(f"✅ Added photo: {os.path.basename(photo_path)}")
                else:
                    print(f"❌ Failed to add photo {photo_path}: {output}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding photos: {str(e)}")
            return False
    
    def add_videos(self, session_id: str, *video_paths: str) -> bool:
        """Add videos to simulator's photo library"""
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            print(f"🎥 Adding videos to simulator photo library...")
            
            for video_path in video_paths:
                if not os.path.exists(video_path):
                    print(f"❌ Video not found: {video_path}")
                    continue
                
                command = ['xcrun', 'simctl', 'addmedia', session.udid, video_path]
                success, output = self._run_command(command)
                
                if success:
                    print(f"✅ Added video: {os.path.basename(video_path)}")
                else:
                    print(f"❌ Failed to add video {video_path}: {output}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding videos: {str(e)}")
            return False

    # [Previous methods remain the same: start_simulator, kill_simulator, etc.]
    def start_simulator(self, device_type: str, ios_version: str) -> str:
        """Start a new iOS simulator session"""
        session_id = str(uuid.uuid4())
        device_name = f"sim_{session_id[:8]}_{device_type.replace(' ', '_')}"
        
        try:
            print(f"Creating simulator: {device_name}")
            udid = self._create_simulator_device(device_name, device_type, ios_version)
            
            print(f"Booting simulator with UDID: {udid}")
            boot_success = self._boot_simulator(udid)
            
            if boot_success:
                time.sleep(3)
                pid = self._get_simulator_pid(udid)
                
                session = SimulatorSession(
                    session_id=session_id,
                    device=SimulatorDevice(
                        name=device_name,
                        identifier=udid,
                        runtime=self.available_runtimes[ios_version],
                        state="Booted",
                        udid=udid
                    ),
                    udid=udid,
                    device_type=device_type,
                    ios_version=ios_version,
                    created_at=time.time(),
                    pid=pid
                )
                
                self.active_sessions[session_id] = session
                print(f"✅ Simulator started successfully!")
                print(f"Session ID: {session_id}")
                print(f"Device: {device_type} (iOS {ios_version})")
                print(f"UDID: {udid}")
                
                return session_id
            else:
                self._run_command(['xcrun', 'simctl', 'delete', udid])
                raise Exception("Failed to boot simulator")
                
        except Exception as e:
            print(f"❌ Error starting simulator: {str(e)}")
            raise
    
    def kill_simulator(self, session_id: str) -> bool:
        """Kill a simulator session"""
        if session_id not in self.active_sessions:
            print(f"❌ Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            print(f"Shutting down simulator session: {session_id}")
            
            success, output = self._run_command(['xcrun', 'simctl', 'shutdown', session.udid])
            if not success:
                print(f"Warning: Failed to shutdown simulator: {output}")
            
            if session.pid:
                try:
                    subprocess.run(['kill', '-9', str(session.pid)], check=False)
                except:
                    pass
            
            success, output = self._run_command(['xcrun', 'simctl', 'delete', session.udid])
            if not success:
                print(f"Warning: Failed to delete simulator device: {output}")
            
            del self.active_sessions[session_id]
            
            print(f"✅ Simulator session {session_id} killed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error killing simulator session: {str(e)}")
            return False
    
    def list_active_sessions(self) -> List[Dict]:
        """List all active simulator sessions"""
        sessions = []
        for session_id, session in self.active_sessions.items():
            sessions.append({
                'session_id': session_id,
                'device_type': session.device_type,
                'ios_version': session.ios_version,
                'udid': session.udid,
                'created_at': session.created_at,
                'uptime': time.time() - session.created_at,
                'installed_apps_count': len(session.installed_apps)
            })
        return sessions
    
    def kill_all_sessions(self) -> int:
        """Kill all active simulator sessions"""
        session_ids = list(self.active_sessions.keys())
        killed_count = 0
        
        for session_id in session_ids:
            if self.kill_simulator(session_id):
                killed_count += 1
        
        print(f"✅ Killed {killed_count} simulator sessions")
        return killed_count
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get detailed information about a specific session"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        return {
            'session_id': session_id,
            'device_type': session.device_type,
            'ios_version': session.ios_version,
            'udid': session.udid,
            'device_name': session.device.name,
            'created_at': session.created_at,
            'uptime': time.time() - session.created_at,
            'pid': session.pid,
            'installed_apps': {bid: {'name': app.app_name, 'installed_at': app.installed_at} 
                            for bid, app in session.installed_apps.items()}
        }



