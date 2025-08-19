"""
iOS Bridge API client for session management and communication
"""
import requests
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from .exceptions import IOSBridgeError, SessionNotFoundError, ConnectionError


class IOSBridgeClient:
    """Client for communicating with iOS Bridge server"""
    
    def __init__(self, server_url: str, timeout: int = 10, verbose: bool = False):
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.verbose = verbose
        self.session = requests.Session()
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to the iOS Bridge server"""
        try:
            response = self._get('/health')
            if not response.get('status') == 'healthy':
                raise ConnectionError("Server is not healthy")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Cannot connect to iOS Bridge server at {self.server_url}: {e}")
    
    def _get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make GET request to the server"""
        url = urljoin(self.server_url, endpoint.lstrip('/'))
        
        try:
            if self.verbose:
                print(f"GET {url}")
            
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            raise IOSBridgeError(f"Invalid JSON response: {e}")
    
    def _post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request to the server"""
        url = urljoin(self.server_url, endpoint.lstrip('/'))
        
        try:
            if self.verbose:
                print(f"POST {url}")
            
            if data:
                kwargs['json'] = data
            
            response = self.session.post(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            raise IOSBridgeError(f"Invalid JSON response: {e}")
    
    def _download(self, endpoint: str, output_path: str) -> bool:
        """Download file from server"""
        url = urljoin(self.server_url, endpoint.lstrip('/'))
        
        try:
            if self.verbose:
                print(f"DOWNLOAD {url} -> {output_path}")
            
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
        except requests.exceptions.RequestException as e:
            if self.verbose:
                print(f"Download failed: {e}")
            return False
        except IOError as e:
            if self.verbose:
                print(f"File write error: {e}")
            return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a session"""
        try:
            response = self._get(f'/api/sessions/{session_id}')
            
            if response.get('success'):
                return response.get('session')
            else:
                return None
        except ConnectionError:
            raise
        except Exception as e:
            if self.verbose:
                print(f"Error getting session info: {e}")
            return None
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions"""
        try:
            response = self._get('/api/sessions/')
            
            if response.get('success'):
                return response.get('sessions', [])
            else:
                return []
        except ConnectionError:
            raise
        except Exception as e:
            if self.verbose:
                print(f"Error listing sessions: {e}")
            return []
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get session status and health"""
        try:
            response = self._get(f'/status/{session_id}')
            return response
        except ConnectionError:
            raise
        except Exception as e:
            if self.verbose:
                print(f"Error getting session status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def take_screenshot(self, session_id: str, output_path: str) -> bool:
        """Take a screenshot and save to file"""
        try:
            return self._download(f'/api/sessions/{session_id}/screenshot', output_path)
        except Exception as e:
            if self.verbose:
                print(f"Error taking screenshot: {e}")
            return False
    
    def get_webrtc_quality_url(self, session_id: str, quality: str) -> str:
        """Get WebRTC quality control URL"""
        return f"{self.server_url}/webrtc/quality/{session_id}/{quality}"
    
    def get_websocket_urls(self, session_id: str) -> Dict[str, str]:
        """Get WebSocket URLs for a session"""
        ws_base = self.server_url.replace('http://', 'ws://').replace('https://', 'wss://')
        
        return {
            'video': f"{ws_base}/ws/{session_id}/video",
            'control': f"{ws_base}/ws/{session_id}/control", 
            'webrtc': f"{ws_base}/ws/{session_id}/webrtc",
            'screenshot': f"{ws_base}/ws/{session_id}/screenshot",
            'logs': f"{ws_base}/ws/{session_id}/logs"
        }
    
    def validate_session(self, session_id: str) -> bool:
        """Validate that a session exists and is accessible"""
        try:
            session_info = self.get_session_info(session_id)
            status = self.get_session_status(session_id)
            
            return (session_info is not None and 
                   status.get('simulator_accessible', False))
        except Exception:
            return False
    
    def get_configurations(self) -> Dict[str, List[str]]:
        """Get available device types and iOS versions"""
        try:
            response = self._get('/api/sessions/configurations')
            
            if response.get('success'):
                return response.get('configurations', {})
            else:
                return {}
        except Exception as e:
            if self.verbose:
                print(f"Error getting configurations: {e}")
            return {}
    
    def create_session(self, device_type: str, ios_version: str) -> Optional[Dict[str, Any]]:
        """Create a new simulator session"""
        try:
            data = {
                'device_type': device_type,
                'ios_version': ios_version
            }
            
            # Send as form data to match your API
            response = self.session.post(
                urljoin(self.server_url, '/api/sessions/create'),
                data=data,  # Send as form data, not JSON
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('success'):
                return {
                    'session_id': result.get('session_id'),
                    'session_info': result.get('session_info')
                }
            else:
                return None
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            raise IOSBridgeError(f"Invalid JSON response: {e}")
        except Exception as e:
            if self.verbose:
                print(f"Error creating session: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete/terminate a simulator session"""
        try:
            response = self.session.delete(
                urljoin(self.server_url, f'/api/sessions/{session_id}'),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('success', False)
        except Exception as e:
            if self.verbose:
                print(f"Error deleting session: {e}")
            return False
    
    def install_app(self, session_id: str, app_path: str, launch_after_install: bool = False, progress_callback=None) -> Dict[str, Any]:
        """Install an app (IPA or ZIP) on a simulator session"""
        import os
        from pathlib import Path
        
        try:
            # Validate file exists
            if not os.path.exists(app_path):
                raise IOSBridgeError(f"App file not found: {app_path}")
            
            file_path = Path(app_path)
            
            # Validate file extension
            if file_path.suffix.lower() not in ['.ipa', '.zip']:
                raise IOSBridgeError(f"Unsupported file type: {file_path.suffix}. Only .ipa and .zip files are supported.")
            
            # Determine field name and endpoint based on file type and launch option
            if file_path.suffix.lower() == '.ipa':
                field_name = 'ipa_file'
            else:
                field_name = 'app_bundle'
            
            endpoint = 'install-and-launch' if launch_after_install else 'install'
            url = urljoin(self.server_url, f'/api/sessions/{session_id}/apps/{endpoint}')
            
            if self.verbose:
                print(f"Installing {file_path.name} on session {session_id}...")
                print(f"POST {url}")
            
            # Get file size for progress tracking
            file_size = os.path.getsize(app_path)
            
            # Simple progress simulation for upload
            if progress_callback:
                import threading
                import time
                
                upload_complete = False
                
                def simulate_progress():
                    # Simulate upload progress
                    progress_steps = [10, 25, 40, 60, 80, 95]
                    for step in progress_steps:
                        if upload_complete:
                            break
                        time.sleep(0.3)  # Small delay between steps
                        progress_callback(int(file_size * step / 100), file_size, step)
                
                # Start progress simulation
                progress_thread = threading.Thread(target=simulate_progress, daemon=True)
                progress_thread.start()
            
            try:
                # Prepare file upload
                with open(app_path, 'rb') as f:
                    files = {field_name: (file_path.name, f, 'application/octet-stream')}
                    
                    response = self.session.post(
                        url,
                        files=files,
                        timeout=120  # Longer timeout for file upload
                    )
                
                # Mark upload as complete and finalize progress
                if progress_callback:
                    upload_complete = True
                    progress_callback(file_size, file_size, 100)
                
            except Exception as e:
                if progress_callback:
                    upload_complete = True
                raise
            
            response.raise_for_status()
            result = response.json()
            
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'app_info': result.get('app_info'),
                'installed_app': result.get('installed_app'),
                'launched_app': result.get('launched_app') if launch_after_install else None
            }
            
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.text
                    return {
                        'success': False,
                        'message': f"HTTP {e.response.status_code}: {error_detail}",
                        'error_code': e.response.status_code
                    }
                except:
                    pass
            
            return {
                'success': False,
                'message': f"Network error: {str(e)}",
                'error_code': 'network_error'
            }
        except IOSBridgeError:
            raise
        except Exception as e:
            return {
                'success': False,
                'message': f"Unexpected error: {str(e)}",
                'error_code': 'unexpected_error'
            }