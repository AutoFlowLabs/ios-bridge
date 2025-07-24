import json
import os
import time
from typing import Dict, Optional, List
from pathlib import Path
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
            'installed_apps': {
                bid: {
                    'name': app.app_name, 
                    'installed_at': app.installed_at,
                    'app_path': app.app_path
                } 
                for bid, app in session.installed_apps.items()
            }
        }
    
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
    
    # Delegate app management methods (with persistent storage updates)
    def install_ipa(self, session_id: str, ipa_path: str) -> bool:
        success = self.ios_manager.install_ipa(session_id, ipa_path)
        if success:
            # Update our session copy from iOS manager
            if session_id in self.ios_manager.active_sessions:
                self.active_sessions[session_id] = self.ios_manager.active_sessions[session_id]
            self._save_sessions()
        return success
    
    def launch_app(self, session_id: str, bundle_id: str) -> bool:
        return self.ios_manager.launch_app(session_id, bundle_id)
    
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

# Global session manager instance
session_manager = SessionManager()