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