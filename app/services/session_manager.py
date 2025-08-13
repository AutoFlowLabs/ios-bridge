import json
import os
import time
from typing import Dict, Optional, List, Tuple
from pathlib import Path
from app.services.app_installation_service import NativeBridgeInstaller
from app.services.ios_app_analyzer_service import AppInfo
from app.services.ios_sim_manager_service import iOSSimulatorManager, SimulatorSession, SimulatorDevice, InstalledApp
from app.core.logging import logger
from app.config.settings import settings

class SessionManager:
    """Centralized session management with persistent storage"""
    
    def __init__(self, storage_dir: str = None):
        self.ios_manager = iOSSimulatorManager()
        self.active_sessions: Dict[str, SimulatorSession] = {}
        
        # Set up storage directory
        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(settings.STATIC_DIR), "session_storage")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.storage_dir / "sessions.json"
        
        # Load existing sessions on startup
        self._load_sessions()
        
        # Detect and recover orphaned simulators
        self._recover_orphaned_simulators()

    def _recover_orphaned_simulators(self):
        """Detect running simulators not in session DB and create entries for them"""
        try:
            logger.info("Scanning for orphaned simulators...")
            
            # Get all currently running simulators
            success, output = self.ios_manager._run_command([
                'xcrun', 'simctl', 'list', 'devices', '-j'
            ])
            
            if not success:
                logger.error("Failed to get device list for orphaned simulator recovery")
                return
            
            data = json.loads(output)
            running_simulators = []
            
            # Find all running/booted simulators
            for runtime, devices in data.get('devices', {}).items():
                for device in devices:
                    if device.get('state') == 'Booted':
                        running_simulators.append({
                            'udid': device.get('udid'),
                            'name': device.get('name'),
                            'runtime': runtime,
                            'state': device.get('state')
                        })
            
            logger.info(f"Found {len(running_simulators)} running simulators")
            
            # Check which ones are not in our session database
            existing_udids = {session.udid for session in self.active_sessions.values()}
            orphaned_count = 0
            
            for sim in running_simulators:
                udid = sim['udid']
                if udid not in existing_udids:
                    # This is an orphaned simulator - create a session for it
                    self._create_orphaned_session(sim)
                    orphaned_count += 1
            
            if orphaned_count > 0:
                logger.info(f"Recovered {orphaned_count} orphaned simulator sessions")
                # Save the updated sessions
                self._save_sessions()
            else:
                logger.info("No orphaned simulators found")
                
        except Exception as e:
            logger.error(f"Failed to recover orphaned simulators: {e}")

    def _create_orphaned_session(self, sim_info: Dict):
        """Create a session entry for an orphaned simulator"""
        try:
            import uuid
            
            udid = sim_info['udid']
            name = sim_info['name']
            runtime = sim_info['runtime']
            
            # Generate a session ID
            session_id = str(uuid.uuid4())
            
            # Extract device type and iOS version from runtime and name
            ios_version = self._extract_ios_version_from_runtime(runtime)
            device_type = self._extract_device_type_from_name(name)
            
            # Get the PID of the running simulator
            pid = self.ios_manager._get_simulator_pid(udid)
            
            # Create device object
            device = SimulatorDevice(
                name=name,
                identifier=udid,
                runtime=runtime,
                state=sim_info['state'],
                udid=udid
            )
            
            # Create session object
            session = SimulatorSession(
                session_id=session_id,
                device=device,
                udid=udid,
                device_type=device_type,
                ios_version=ios_version,
                created_at=time.time(),  # Use current time as we don't know real creation time
                pid=pid,
                installed_apps={}  # Will be populated if needed
            )
            
            # Add to both managers
            self.active_sessions[session_id] = session
            self.ios_manager.active_sessions[session_id] = session
            
            logger.info(f"Created session {session_id} for orphaned simulator: {device_type} iOS {ios_version} (UDID: {udid})")
            
        except Exception as e:
            logger.error(f"Failed to create session for orphaned simulator {sim_info.get('udid', 'unknown')}: {e}")

    def _extract_ios_version_from_runtime(self, runtime: str) -> str:
        """Extract iOS version from runtime string (e.g., 'com.apple.CoreSimulator.SimRuntime.iOS-18-2' -> '18.2')"""
        try:
            # Runtime format is usually like: com.apple.CoreSimulator.SimRuntime.iOS-18-2
            if 'iOS-' in runtime:
                version_part = runtime.split('iOS-')[-1]
                # Replace dashes with dots: 18-2 -> 18.2
                return version_part.replace('-', '.')
            return "Unknown"
        except:
            return "Unknown"

    def _extract_device_type_from_name(self, name: str) -> str:
        """Extract device type from simulator name"""
        try:
            # Simulator names often contain device type info
            # e.g., "iPhone 15 Pro" or "sim_abc123_iPhone_16"
            
            # Check for common device patterns
            if 'iPhone' in name:
                # Try to extract iPhone model
                import re
                # Look for patterns like "iPhone 15", "iPhone 16 Pro", etc.
                match = re.search(r'iPhone\s+[\w\s]*\d+[\w\s]*', name)
                if match:
                    return match.group().strip()
                return "iPhone"
            elif 'iPad' in name:
                # Try to extract iPad model
                import re
                match = re.search(r'iPad[\w\s]*', name)
                if match:
                    return match.group().strip()
                return "iPad"
            
            # Fallback: return the full name
            return name
        except:
            return "Unknown Device"

    def _serialize_session(self, session: SimulatorSession) -> Dict:
        """Convert SimulatorSession to JSON-serializable dict"""
        return {
            "session_id": session.session_id,
            "device": {
                "name": session.device.name,
                "identifier": session.device.identifier,
                "runtime": session.device.runtime,
                "state": session.device.state,
                "udid": session.device.udid
            },
            "udid": session.udid,
            "device_type": session.device_type,
            "ios_version": session.ios_version,
            "created_at": session.created_at,
            "pid": session.pid,
            "installed_apps": {
                bundle_id: {
                    "bundle_id": app.bundle_id,
                    "app_name": app.app_name,
                    "app_path": app.app_path,
                    "installed_at": app.installed_at
                }
                for bundle_id, app in session.installed_apps.items()
            }
        }
    
    def _deserialize_session(self, data: Dict) -> SimulatorSession:
        """Convert dict back to SimulatorSession object"""
        device = SimulatorDevice(
            name=data["device"]["name"],
            identifier=data["device"]["identifier"],
            runtime=data["device"]["runtime"],
            state=data["device"]["state"],
            udid=data["device"]["udid"]
        )
        
        installed_apps = {}
        for bundle_id, app_data in data.get("installed_apps", {}).items():
            installed_apps[bundle_id] = InstalledApp(
                bundle_id=app_data["bundle_id"],
                app_name=app_data["app_name"],
                app_path=app_data["app_path"],
                installed_at=app_data["installed_at"]
            )
        
        return SimulatorSession(
            session_id=data["session_id"],
            device=device,
            udid=data["udid"],
            device_type=data["device_type"],
            ios_version=data["ios_version"],
            created_at=data["created_at"],
            pid=data.get("pid"),
            installed_apps=installed_apps
        )
    
    def _save_sessions(self):
        """Save all sessions to JSON file"""
        try:
            sessions_data = {}
            for session_id, session in self.active_sessions.items():
                sessions_data[session_id] = self._serialize_session(session)
            
            # Create backup of existing file
            if self.sessions_file.exists():
                backup_file = self.storage_dir / f"sessions_backup_{int(time.time())}.json"
                os.rename(self.sessions_file, backup_file)
                
                # Keep only last 5 backups
                backups = sorted(self.storage_dir.glob("sessions_backup_*.json"))
                if len(backups) > 5:
                    for old_backup in backups[:-5]:
                        old_backup.unlink()
            
            # Write new sessions file
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions_data, f, indent=2)
            
            logger.info(f"Saved {len(sessions_data)} sessions to persistent storage")
            
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")
    
    def _load_sessions(self):
        """Load sessions from JSON file and validate they still exist"""
        try:
            if not self.sessions_file.exists():
                logger.info("No existing sessions file found")
                return
            
            with open(self.sessions_file, 'r') as f:
                sessions_data = json.load(f)
            
            loaded_count = 0
            validated_count = 0
            
            for session_id, session_data in sessions_data.items():
                try:
                    session = self._deserialize_session(session_data)
                    loaded_count += 1
                    
                    # Validate that the simulator still exists and is accessible
                    if self._validate_session(session):
                        self.active_sessions[session_id] = session
                        # Sync with iOS manager
                        self.ios_manager.active_sessions[session_id] = session
                        validated_count += 1
                        logger.info(f"Restored session {session_id}: {session.device_type} iOS {session.ios_version}")
                    else:
                        logger.warning(f"Session {session_id} no longer valid, removing from storage")
                        
                except Exception as e:
                    logger.error(f"Failed to load session {session_id}: {e}")
            
            logger.info(f"Loaded {loaded_count} sessions from storage, {validated_count} are still valid")
            
            # Save the validated sessions back (removes invalid ones)
            if loaded_count != validated_count:
                self._save_sessions()
                
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
    
    def _validate_session(self, session: SimulatorSession) -> bool:
        """Validate that a session's simulator still exists and is accessible"""
        try:
            # Check if the simulator device still exists
            success, output = self.ios_manager._run_command([
                'xcrun', 'simctl', 'list', 'devices', '-j'
            ])
            
            if not success:
                return False
            
            data = json.loads(output)
            
            # Look for our UDID in the device list
            for runtime, devices in data.get('devices', {}).items():
                for device in devices:
                    if device.get('udid') == session.udid:
                        # Update session state
                        session.device.state = device.get('state', 'Unknown')
                        session.pid = self.ios_manager._get_simulator_pid(session.udid)
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to validate session {session.session_id}: {e}")
            return False
    
    def get_available_configurations(self) -> Dict:
        """Get available device types and iOS versions"""
        return self.ios_manager.list_available_configurations()
    
    def create_session(self, device_type: str, ios_version: str) -> str:
        """Create a new simulator session"""
        session_id = self.ios_manager.start_simulator(device_type, ios_version)
        session = self.ios_manager.active_sessions[session_id]
        self.active_sessions[session_id] = session
        
        # Save to persistent storage
        self._save_sessions()
        
        logger.info(f"Created session {session_id}: {device_type} iOS {ios_version}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SimulatorSession]:
        """Get session by ID"""
        return self.active_sessions.get(session_id)
    
    def get_session_udid(self, session_id: str) -> Optional[str]:
        """Get UDID for a session"""
        session = self.get_session(session_id)
        return session.udid if session else None
    
    def list_sessions(self) -> List[Dict]:
        """List all active sessions"""
        sessions = []
        for session_id, session in self.active_sessions.items():
            sessions.append({
                'session_id': session_id,
                'device_type': session.device_type,
                'ios_version': session.ios_version,
                'udid': session.udid,
                'created_at': session.created_at,
                'uptime': time.time() - session.created_at,
                'installed_apps_count': len(session.installed_apps),
                'state': session.device.state,
                'pid': session.pid
            })
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        success = self.ios_manager.kill_simulator(session_id)
        if success and session_id in self.active_sessions:
            del self.active_sessions[session_id]
            # Update persistent storage
            self._save_sessions()
        return success
    
    def delete_all_sessions(self) -> int:
        """Delete all sessions"""
        count = self.ios_manager.kill_all_sessions()
        self.active_sessions.clear()
        # Clear persistent storage
        self._save_sessions()
        return count
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get detailed session information"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        # Get device dimensions (logical points, scaled for desktop UI)
        device_width, device_height = 390, 844  # Default dimensions
        stream_width, stream_height = None, None  # Actual pixel dimensions of the stream
        try:
            from app.services.device_service import DeviceService
            device_service = DeviceService(session.udid)
            # Use synchronous version to avoid asyncio issues (returns scaled point dims)
            device_width, device_height = self._get_device_dimensions_sync(device_service.udid)
            # Also fetch the raw pixel stream dimensions for accurate rendering in Electron
            stream_dims = self._get_stream_dimensions_sync(device_service.udid)
            if stream_dims:
                stream_width, stream_height = stream_dims
        except Exception as e:
            logger.warning(f"Could not get device dimensions for {session_id}: {e}")
            # Fall back to defaults
            pass
        
        return {
            'session_id': session_id,
            'device_type': session.device_type,
            'ios_version': session.ios_version,
            'udid': session.udid,
            'device_name': session.device.name,
            'created_at': session.created_at,
            'uptime': time.time() - session.created_at,
            'pid': session.pid,
            'state': session.device.state,
            # Desktop-scaled logical dimensions (used for coordinate mapping/UI)
            'device_width': device_width,
            'device_height': device_height,
            # Raw stream pixel dimensions for accurate window sizing
            'stream_width': stream_width,
            'stream_height': stream_height,
            'installed_apps': {
                bid: {
                    'name': app.app_name, 
                    'installed_at': app.installed_at,
                    'app_path': app.app_path
                } 
                for bid, app in session.installed_apps.items()
            }
        }
    
    def _get_device_dimensions_sync(self, udid: str) -> Tuple[int, int]:
        """Get device dimensions synchronously - scaled for desktop display (logical points)."""
        try:
            import subprocess
            import re
            
            cmd = ["idb", "describe", "--udid", udid]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0:
                # Parse the screen_dimensions from the output
                # Format: screen_dimensions=ScreenDimensions(width=1179, height=2556, density=3.0, width_points=393, height_points=852)
                screen_dims_match = re.search(r'screen_dimensions=ScreenDimensions\([^)]+width_points=(\d+)[^)]+height_points=(\d+)', result.stdout)
                
                if screen_dims_match:
                    width_points = int(screen_dims_match.group(1))
                    height_points = int(screen_dims_match.group(2))
                    
                    # Scale down for desktop display (typically 0.6-0.8x looks good)
                    desktop_scale = 0.75  # Adjust this value as needed
                    desktop_width = int(width_points * desktop_scale)
                    desktop_height = int(height_points * desktop_scale)
                    
                    logger.info(f"Device {udid} point dimensions: {width_points}x{height_points}, desktop scaled: {desktop_width}x{desktop_height}")
                    return (desktop_width, desktop_height)
                
                # Fallback: try original regex patterns
                width_points_match = re.search(r'width_points=(\d+)', result.stdout)
                height_points_match = re.search(r'height_points=(\d+)', result.stdout)
                
                if width_points_match and height_points_match:
                    width_points = int(width_points_match.group(1))
                    height_points = int(height_points_match.group(1))
                    
                    # Scale down for desktop display
                    desktop_scale = 0.75
                    desktop_width = int(width_points * desktop_scale)
                    desktop_height = int(height_points * desktop_scale)
                    
                    logger.info(f"Device {udid} fallback dimensions: {width_points}x{height_points}, desktop scaled: {desktop_width}x{desktop_height}")
                    return (desktop_width, desktop_height)
                
        except Exception as e:
            logger.warning(f"Error getting device dimensions: {e}")
        
        # Default dimensions for iPhone (scaled for desktop)
        return (294, 633)  # 390*0.75, 844*0.75

    def _get_stream_dimensions_sync(self, udid: str) -> Optional[Tuple[int, int]]:
        """Get the raw stream pixel dimensions (width, height) via idb describe."""
        try:
            import subprocess
            import re
            cmd = ["idb", "describe", "--udid", udid]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                # Look for width and height in pixels within ScreenDimensions
                # Example: ScreenDimensions(width=1179, height=2556, density=3.0, width_points=393, height_points=852)
                px_match = re.search(r'screen_dimensions=ScreenDimensions\([^)]*width=(\d+),\s*height=(\d+)', result.stdout)
                if px_match:
                    width_px = int(px_match.group(1))
                    height_px = int(px_match.group(2))
                    logger.info(f"Stream pixel dimensions for {udid}: {width_px}x{height_px}")
                    return (width_px, height_px)
                # Fallback: try separate matches
                width_px_match = re.search(r'width=(\d+)', result.stdout)
                height_px_match = re.search(r'height=(\d+)', result.stdout)
                if width_px_match and height_px_match:
                    width_px = int(width_px_match.group(1))
                    height_px = int(height_px_match.group(1))
                    logger.info(f"Stream pixel dimensions (fallback) for {udid}: {width_px}x{height_px}")
                    return (width_px, height_px)
        except Exception as e:
            logger.warning(f"Error getting stream dimensions: {e}")
        return None
    
    def refresh_session_states(self) -> int:
        """Refresh the state of all sessions and remove invalid ones"""
        invalid_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if not self._validate_session(session):
                invalid_sessions.append(session_id)
        
        # Remove invalid sessions
        for session_id in invalid_sessions:
            logger.warning(f"Removing invalid session {session_id}")
            del self.active_sessions[session_id]
            # Also remove from iOS manager
            if session_id in self.ios_manager.active_sessions:
                del self.ios_manager.active_sessions[session_id]
        
        if invalid_sessions:
            self._save_sessions()
        
        return len(invalid_sessions)
    
    def _serialize_app_info(self, app_info: AppInfo) -> dict:
        """Convert AppInfo object to serializable dict"""
        if not app_info:
            return None
            
        return {
            'bundle_id': app_info.bundle_id,
            'app_name': app_info.app_name,
            'display_name': app_info.display_name,
            'version': app_info.version,
            'build_version': app_info.build_version,
            'min_os_version': app_info.min_os_version,
            'supported_platforms': app_info.supported_platforms,
            'architectures': app_info.architecture_info.architectures if app_info.architecture_info else [],
            'file_size_mb': round(app_info.file_size / (1024 * 1024), 2) if app_info.file_size else 0,
            'has_info_plist': app_info.has_info_plist
        }
    
    def install_app(self, session_id: str, app_path: str, progress_callback=None) -> dict:
        """
        Install app using NativeBridgeInstaller with comprehensive handling
        """
        # Initialize the installer if not already done
        if not hasattr(self, '_installer'):
            self._installer = NativeBridgeInstaller(self.ios_manager.active_sessions)
        
        # Update installer's session reference (in case sessions changed)
        self._installer.active_sessions = self.ios_manager.active_sessions
        
        try:
            # Use NativeBridgeInstaller for comprehensive app installation
            result = self._installer.install_user_app(session_id, app_path, progress_callback)
            
            # Create response dict - PRESERVE the compatibility and app_info
            response = {
                'success': result.success,
                'message': result.message,
                'compatibility': result.compatibility.value if result.compatibility else 'unknown',
                'app_info': self._serialize_app_info(result.app_info) if result.app_info else None,
                'suggestions': result.suggestions,
                'alternatives': result.alternatives,
                'processing_steps': result.processing_steps
            }
            
            if result.success:
                # Update our session copy from iOS manager
                if session_id in self.ios_manager.active_sessions:
                    self.active_sessions[session_id] = self.ios_manager.active_sessions[session_id]
                self._save_sessions()
                
                # Add success details
                response['installed_app'] = {
                    'bundle_id': result.app_info.bundle_id if result.app_info else None,
                    'app_name': result.app_info.display_name or result.app_info.app_name if result.app_info else None,
                    'installed_at': time.time()
                }

            print(f"Installation result: {response}")        
            return response
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Installation error: {str(e)}",
                'compatibility': 'error',
                'suggestions': [
                    "Please try uploading the app again",
                    "Ensure the app file is not corrupted",
                    "Contact support if the issue persists"
                ],
                'error_details': str(e)
            }
        
        
    def launch_app(self, session_id: str, bundle_id: str) -> bool:
        return self.ios_manager.launch_app(session_id, bundle_id)
    

    def is_app_installed(self, session_id: str, bundle_id: str) -> bool:
        """Check if an app is installed in a session"""
        try:
            apps = self.list_installed_apps(session_id)
            if not apps:
                return False
                
            for app in apps:
                if isinstance(app, dict):
                    app_bundle_id = app.get('bundle_id')
                else:
                    app_bundle_id = getattr(app, 'bundle_id', None)
                
                if app_bundle_id == bundle_id:
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking if app is installed: {e}")
            return False
    
    def uninstall_app(self, session_id: str, bundle_id: str) -> bool:
        success = self.ios_manager.uninstall_app(session_id, bundle_id)
        if success:
            # Update our session copy from iOS manager
            if session_id in self.ios_manager.active_sessions:
                self.active_sessions[session_id] = self.ios_manager.active_sessions[session_id]
            self._save_sessions()
        return success
    
    def list_installed_apps(self, session_id: str) -> List[Dict]:
        return self.ios_manager.list_installed_apps(session_id)
    
    def terminate_app(self, session_id: str, bundle_id: str) -> bool:
        return self.ios_manager.terminate_app(session_id, bundle_id)
    
    def cleanup_storage(self):
        """Clean up old backup files and perform maintenance"""
        try:
            # Remove old backups (keep only last 5)
            backups = sorted(self.storage_dir.glob("sessions_backup_*.json"))
            if len(backups) > 5:
                for old_backup in backups[:-5]:
                    old_backup.unlink()
                    logger.info(f"Removed old backup: {old_backup.name}")
        except Exception as e:
            logger.error(f"Failed to cleanup storage: {e}")
    
    def cleanup_all_recordings(self):
        """Clean up all active recordings on app shutdown"""
        try:
            for session_id, session in self.active_sessions.items():
                if hasattr(session, 'recording_service') and session.recording_service:
                    logger.info(f"Stopping recording for session {session_id}")
                    session.recording_service.force_stop()
        except Exception as e:
            logger.error(f"Failed to cleanup recordings: {e}")

    def recover_orphaned_simulators(self) -> int:
        """Manually trigger orphaned simulator recovery and return count of recovered sessions"""
        initial_count = len(self.active_sessions)
        self._recover_orphaned_simulators()
        recovered_count = len(self.active_sessions) - initial_count
        return recovered_count
    
    def open_url(self, session_id: str, url: str) -> bool:
        """Open a URL on the simulator"""
        success = self.ios_manager.open_url(session_id, url)
        if success:
            logger.info(f"Successfully opened URL '{url}' on session {session_id}")
        else:
            logger.error(f"Failed to open URL '{url}' on session {session_id}")
        return success

    def get_url_scheme_info(self, session_id: str) -> Dict:
        """Get URL scheme information for a session"""
        return self.ios_manager.get_url_scheme_info(session_id)

# Global session manager instance
session_manager = SessionManager()