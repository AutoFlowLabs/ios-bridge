import subprocess
import json
import tempfile
import uuid
import time
import threading
import os
import asyncio
import numpy as np
import base64
import io
import signal
import atexit
from PIL import Image, ImageGrab
import Quartz
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
import pyautogui
from typing import Dict, List, Optional, Tuple, Callable
import logging
from datetime import datetime
import base64
import websocket
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect, Request, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import socketio
import uvicorn

from IOSSimulatorManager import iOSSimulatorManager

# Persistent session storage class
class SessionStorage:
    def __init__(self, storage_file: str = "simulator_sessions.json"):
        self.storage_file = storage_file
        self.sessions_data = {}
        self.load_sessions()
    
    def load_sessions(self):
        """Load sessions from JSON file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    self.sessions_data = json.load(f)
                print(f"📂 Loaded {len(self.sessions_data)} sessions from {self.storage_file}")
            else:
                print(f"📂 No existing session file found, will create {self.storage_file}")
                self.sessions_data = {}
        except Exception as e:
            print(f"❌ Error loading sessions: {e}")
            self.sessions_data = {}
    
    def save_sessions(self):
        """Save sessions to JSON file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.sessions_data, f, indent=2)
            print(f"💾 Saved {len(self.sessions_data)} sessions to {self.storage_file}")
        except Exception as e:
            print(f"❌ Error saving sessions: {e}")
    
    def add_session(self, session_id: str, session_data: dict):
        """Add a session to storage"""
        # Preserve the original created_at if it's already a timestamp
        created_at = session_data.get('created_at')
        if created_at is None or isinstance(created_at, str):
            created_at = datetime.now().isoformat()
        
        self.sessions_data[session_id] = {
            **session_data,
            'created_at_iso': datetime.now().isoformat(),  # Always store ISO for human readability
            'last_verified': datetime.now().isoformat()
        }
        
        # Keep the original created_at format for compatibility
        if 'created_at' in session_data:
            self.sessions_data[session_id]['created_at'] = session_data['created_at']
        
        self.save_sessions()
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data by ID"""
        return self.sessions_data.get(session_id)
    
    def get_all_sessions(self) -> dict:
        """Get all sessions"""
        return self.sessions_data
    
    def remove_session(self, session_id: str):
        """Remove a session from storage"""
        if session_id in self.sessions_data:
            del self.sessions_data[session_id]
            self.save_sessions()
    
    def update_session_verification(self, session_id: str):
        """Update last verification time"""
        if session_id in self.sessions_data:
            self.sessions_data[session_id]['last_verified'] = datetime.now().isoformat()
            self.save_sessions()


class WebSimulatorStreamer:
    def __init__(self, session_id: str, udid: str):
        self.session_id = session_id
        self.udid = udid
        self.ws = None
        self.streaming = False
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.simulator_port = None
        
    def connect_to_simulator_web_interface(self) -> bool:
        """Connect to the simulator's web interface"""
        try:
            # First, enable the web interface in the simulator
            command = [
                'xcrun', 'simctl', 'ui', self.udid, 'appearance', 'dark'  # This ensures simulator is active
            ]
            subprocess.run(command, capture_output=True)
            
            # The simulator web interface typically runs on a dynamic port
            # We need to find it or configure it
            simulator_port = self._get_simulator_web_port()
            
            if not simulator_port:
                print("❌ Could not find simulator web interface port")
                return False
            
            # Connect to the WebSocket
            ws_url = f"ws://localhost:{simulator_port}/websocket"
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Start WebSocket in a thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Error connecting to simulator web interface: {e}")
            return False
    
    def _get_simulator_web_port(self) -> Optional[int]:
        """Get the port number for simulator's web interface"""
        # This would need to be implemented based on how you configure
        # the simulator's web interface. Some approaches:
        # 1. Parse simulator logs
        # 2. Use a fixed port configuration
        # 3. Scan common ports
        return 8080  # Default/example port
    
    def _on_open(self, ws):
        """Called when WebSocket connection opens"""
        print("✅ Connected to simulator web interface")
        self.streaming = True
        
        # Request video stream
        ws.send(json.dumps({
            'type': 'start_video_stream',
            'quality': 'high',
            'fps': 30
        }))
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            if data.get('type') == 'video_frame':
                # Decode base64 frame data
                frame_b64 = data.get('frame_data')
                if frame_b64:
                    frame_data = base64.b64decode(frame_b64)
                    with self.frame_lock:
                        self.latest_frame = frame_data
                        
        except Exception as e:
            print(f"❌ Error processing WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"❌ WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        print("🔌 WebSocket connection closed")
        self.streaming = False
    
    def send_touch_event(self, x: int, y: int, event_type: str = "tap"):
        """Send touch event through WebSocket"""
        if self.ws and self.streaming:
            self.ws.send(json.dumps({
                'type': 'touch_event',
                'x': x,
                'y': y,
                'event_type': event_type
            }))
            return True
        return False

class SimulatorVideoStreamer:
    def __init__(self, session_id: str, udid: str):
        self.session_id = session_id
        self.udid = udid
        self.streaming = False
        self.recording_process = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
    def start_streaming(self):
        """Start video streaming using simctl video recording"""
        try:
            self.streaming = True
            
            # Create a temporary directory for video chunks
            self.temp_dir = tempfile.mkdtemp(prefix="simulator_stream_")
            
            # Start the streaming thread
            self.stream_thread = threading.Thread(target=self._stream_loop)
            self.stream_thread.daemon = True
            self.stream_thread.start()
            
            print("✅ Simulator video streaming started")
            return True
            
        except Exception as e:
            print(f"❌ Error starting video stream: {e}")
            return False
    
    def _stream_loop(self):
        """Main streaming loop using simctl video recording"""
        chunk_duration = 2  # 2-second video chunks
        chunk_counter = 0
        
        while self.streaming:
            try:
                # Record a short video chunk
                chunk_file = os.path.join(self.temp_dir, f"chunk_{chunk_counter:04d}.mp4")
                
                # Start recording
                command = [
                    'xcrun', 'simctl', 'io', self.udid, 'recordVideo',
                    '--type=mp4', '--codec=h264',
                    chunk_file
                ]
                
                process = subprocess.Popen(command)
                
                # Let it record for the specified duration
                time.sleep(chunk_duration)
                
                # Stop recording
                process.terminate()
                process.wait()
                
                # Extract frame from the video chunk
                if os.path.exists(chunk_file):
                    frame_data = self._extract_frame_from_video(chunk_file)
                    if frame_data:
                        with self.frame_lock:
                            self.latest_frame = frame_data
                    
                    # Clean up the chunk file
                    os.unlink(chunk_file)
                
                chunk_counter += 1
                
            except Exception as e:
                print(f"❌ Error in video stream loop: {e}")
                time.sleep(1)
    
    def _extract_frame_from_video(self, video_file: str) -> bytes:
        """Extract a frame from video file using ffmpeg"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_frame:
                # Use ffmpeg to extract the last frame
                command = [
                    'ffmpeg', '-i', video_file,
                    '-vf', 'select=eof-1',
                    '-vsync', 'vfr',
                    '-q:v', '2',
                    '-y', temp_frame.name
                ]
                
                result = subprocess.run(command, capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(temp_frame.name):
                    with open(temp_frame.name, 'rb') as f:
                        frame_data = f.read()
                    os.unlink(temp_frame.name)
                    return frame_data
                
        except Exception as e:
            print(f"❌ Error extracting frame: {e}")
        
        return None


class SimulatorStreamer:
    def __init__(self, session_id: str, udid: str, quality: int = 80, fps: int = 30):
        self.session_id = session_id
        self.udid = udid
        self.quality = quality
        self.fps = fps
        self.streaming = False
        self.stream_thread = None
        self.websocket_clients = set()
        self.socketio_clients = set()
        self.simulator_window_bounds = None
        self.latest_frame = None  # Store latest frame for REST API access
        self.frame_lock = threading.Lock()
        
    def find_simulator_window(self) -> Optional[Dict]:
        """Find the simulator window bounds with enhanced debugging"""
        try:
            print(f"🔍 Looking for simulator window for UDID: {self.udid}")
            window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
            
            # Debug: Print all windows
            simulator_windows = []
            for window in window_list:
                window_name = window.get('kCGWindowName', '')
                window_owner = window.get('kCGWindowOwnerName', '')
                
                if window_owner == 'Simulator':
                    simulator_windows.append({
                        'name': window_name,
                        'owner': window_owner,
                        'bounds': window.get('kCGWindowBounds', {})
                    })
                    print(f"   Found Simulator window: '{window_name}' bounds: {window.get('kCGWindowBounds', {})}")
            
            if not simulator_windows:
                print("❌ No Simulator windows found at all")
                return None
            
            # Strategy 1: Look for window with our specific UDID
            for window in window_list:
                window_name = window.get('kCGWindowName', '')
                window_owner = window.get('kCGWindowOwnerName', '')
                
                if (window_owner == 'Simulator' and 
                    (self.udid in window_name or self.udid[:8] in window_name)):
                    
                    bounds = window.get('kCGWindowBounds', {})
                    print(f"✅ Found UDID-specific window: '{window_name}'")
                    return {
                        'x': int(bounds.get('X', 0)),
                        'y': int(bounds.get('Y', 0)),
                        'width': int(bounds.get('Width', 414)),
                        'height': int(bounds.get('Height', 896))
                    }
            
            # Strategy 2: Look for iOS Simulator window
            for window in window_list:
                window_name = window.get('kCGWindowName', '')
                window_owner = window.get('kCGWindowOwnerName', '')
                
                if (window_owner == 'Simulator' and 
                    ('iOS' in window_name or 'iPhone' in window_name or 'iPad' in window_name)):
                    
                    bounds = window.get('kCGWindowBounds', {})
                    print(f"✅ Found iOS Simulator window: '{window_name}'")
                    return {
                        'x': int(bounds.get('X', 0)),
                        'y': int(bounds.get('Y', 0)),
                        'width': int(bounds.get('Width', 414)),
                        'height': int(bounds.get('Height', 896))
                    }
            
            # Strategy 3: Take the largest Simulator window
            largest_window = None
            largest_area = 0
            
            for window in window_list:
                window_owner = window.get('kCGWindowOwnerName', '')
                if window_owner == 'Simulator':
                    bounds = window.get('kCGWindowBounds', {})
                    width = bounds.get('Width', 0)
                    height = bounds.get('Height', 0)
                    area = width * height
                    
                    if area > largest_area and width > 200 and height > 200:  # Reasonable size check
                        largest_area = area
                        largest_window = {
                            'x': int(bounds.get('X', 0)),
                            'y': int(bounds.get('Y', 0)),
                            'width': int(width),
                            'height': int(height)
                        }
            
            if largest_window:
                print(f"✅ Using largest Simulator window: {largest_window}")
                return largest_window
            
            print("❌ No suitable Simulator window found")
            return None
            
        except Exception as e:
            print(f"❌ Error finding simulator window: {e}")
            return None
    
    def ensure_simulator_visible(self) -> bool:
        """Ensure the simulator is visible and focused"""
        try:
            print(f"📱 Ensuring simulator {self.udid} is visible...")
            
            # Try to open/focus the simulator
            command = ['open', '-a', 'Simulator', '--args', '-CurrentDeviceUDID', self.udid]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"⚠️  Failed to open simulator: {result.stderr}")
                return False
            
            # Wait a bit for the simulator to become visible
            time.sleep(2)
            
            # Check if window is now available
            window_bounds = self.find_simulator_window()
            return window_bounds is not None
            
        except Exception as e:
            print(f"❌ Error ensuring simulator visibility: {e}")
            return False
    
    def capture_simulator_screen(self) -> Optional[bytes]:
        """Capture simulator screen as JPEG bytes with enhanced error handling"""
        try:
            # First attempt: use cached window bounds
            if not self.simulator_window_bounds:
                self.simulator_window_bounds = self.find_simulator_window()
            
            # If still no bounds, try to make simulator visible
            if not self.simulator_window_bounds:
                print("🔄 No window bounds found, trying to make simulator visible...")
                if self.ensure_simulator_visible():
                    self.simulator_window_bounds = self.find_simulator_window()
                
                if not self.simulator_window_bounds:
                    print("❌ Still no window bounds after making simulator visible")
                    return None
            
            # Validate bounds
            bounds = self.simulator_window_bounds
            if bounds['width'] <= 0 or bounds['height'] <= 0:
                print(f"❌ Invalid window bounds: {bounds}")
                self.simulator_window_bounds = None
                return None
            
            print(f"📸 Capturing screen with bounds: {bounds}")
            
            # Method 1: Try PIL screenshot
            try:
                x, y = bounds['x'], bounds['y']
                width, height = bounds['width'], bounds['height']
                
                # Capture the specific window area
                screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
                
                # Check if we got a valid image
                if screenshot.size[0] == 0 or screenshot.size[1] == 0:
                    raise Exception("Empty screenshot captured")
                
                # Convert to JPEG bytes
                img_buffer = io.BytesIO()
                screenshot.save(img_buffer, format='JPEG', quality=self.quality)
                img_buffer.seek(0)
                
                frame_data = img_buffer.read()
                if len(frame_data) > 1000:  # Reasonable size check
                    print(f"✅ Successfully captured frame ({len(frame_data)} bytes)")
                    return frame_data
                else:
                    raise Exception("Frame too small")
                
            except Exception as pil_error:
                print(f"⚠️  PIL capture failed: {pil_error}")
                
                # Method 2: Try simctl screenshot as fallback
                return self._capture_via_simctl()
            
        except Exception as e:
            print(f"❌ Error capturing screen: {e}")
            # Reset window bounds on error
            self.simulator_window_bounds = None
            return None
    
    def _capture_via_simctl(self) -> Optional[bytes]:
        """Fallback method using simctl screenshot"""
        try:
            print("🔄 Trying simctl screenshot fallback...")
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                command = ['xcrun', 'simctl', 'io', self.udid, 'screenshot', tmp_file.name]
                result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    print(f"❌ simctl screenshot failed: {result.stderr}")
                    os.unlink(tmp_file.name)
                    return None
                
                # Read and convert to JPEG
                with open(tmp_file.name, 'rb') as f:
                    png_data = f.read()
                
                # Convert PNG to JPEG
                png_image = Image.open(io.BytesIO(png_data))
                img_buffer = io.BytesIO()
                png_image.convert('RGB').save(img_buffer, format='JPEG', quality=self.quality)
                img_buffer.seek(0)
                
                # Clean up temp file
                os.unlink(tmp_file.name)
                
                frame_data = img_buffer.read()
                print(f"✅ simctl screenshot successful ({len(frame_data)} bytes)")
                return frame_data
                
        except Exception as e:
            print(f"❌ simctl screenshot fallback failed: {e}")
            return None
    
    def start_streaming(self):
        """Start streaming simulator screen"""
        if self.streaming:
            return
        
        self.streaming = True
        self.stream_thread = threading.Thread(target=self._stream_loop)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        print(f"📺 Started streaming simulator {self.session_id}")
    
    def stop_streaming(self):
        """Stop streaming"""
        self.streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=5)
        print(f"🛑 Stopped streaming simulator {self.session_id}")
    
    def _stream_loop(self):
        """Main streaming loop"""
        frame_delay = 1.0 / self.fps
        consecutive_failures = 0
        max_failures = 10
        
        while self.streaming:
            try:
                frame_start = time.time()
                
                # Capture frame
                frame_data = self.capture_simulator_screen()
                if frame_data:
                    consecutive_failures = 0  # Reset failure counter
                    
                    # Store latest frame for REST API
                    with self.frame_lock:
                        self.latest_frame = frame_data
                    
                    # Broadcast to clients if any are connected
                    if self.websocket_clients or self.socketio_clients:
                        frame_b64 = base64.b64encode(frame_data).decode('utf-8')
                        self._broadcast_frame(frame_b64)
                else:
                    consecutive_failures += 1
                    print(f"⚠️  Frame capture failed ({consecutive_failures}/{max_failures})")
                    
                    # If too many consecutive failures, reset everything
                    if consecutive_failures >= max_failures:
                        print("🔄 Too many failures, resetting window detection...")
                        self.simulator_window_bounds = None
                        consecutive_failures = 0
                        time.sleep(2)  # Longer delay before retrying
                
                # Maintain FPS
                elapsed = time.time() - frame_start
                sleep_time = max(0, frame_delay - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"❌ Error in streaming loop: {e}")
                time.sleep(0.5)  # Wait before retrying
    
    def _broadcast_frame(self, frame_b64: str):
        """Broadcast frame to all clients"""
        # Broadcast to WebSocket clients
        disconnected_ws_clients = set()
        for client in self.websocket_clients.copy():
            try:
                asyncio.create_task(client.send_text(json.dumps({
                    'type': 'frame',
                    'data': frame_b64,
                    'session_id': self.session_id
                })))
            except:
                disconnected_ws_clients.add(client)
        
        self.websocket_clients -= disconnected_ws_clients
    
    def get_latest_frame(self) -> Optional[bytes]:
        """Get the latest captured frame for REST API"""
        with self.frame_lock:
            return self.latest_frame
    
    def add_websocket_client(self, websocket):
        """Add a websocket client"""
        self.websocket_clients.add(websocket)
    
    def remove_websocket_client(self, websocket):
        """Remove a websocket client"""
        self.websocket_clients.discard(websocket)
    
    def add_socketio_client(self, sid):
        """Add a SocketIO client"""
        self.socketio_clients.add(sid)
    
    def remove_socketio_client(self, sid):
        """Remove a SocketIO client"""
        self.socketio_clients.discard(sid)
    
    def handle_touch_event(self, x: int, y: int, event_type: str = "tap"):
        """Handle remote touch events"""
        try:
            if not self.simulator_window_bounds:
                self.simulator_window_bounds = self.find_simulator_window()
                if not self.simulator_window_bounds:
                    return False
            
            print(f"🖱️ Touch event: {event_type} at ({x}, {y}) on session {self.session_id[:8]}")
            
            if event_type == "tap":
                # Use simctl for more reliable touch simulation
                command = ['xcrun', 'simctl', 'ui', self.udid, 'tap', str(x), str(y)]
                result = subprocess.run(command, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ Touch successful via simctl")
                    return True
                else:
                    print(f"⚠️ simctl failed, trying pyautogui fallback: {result.stderr}")
                    # Fallback to pyautogui
                    abs_x = self.simulator_window_bounds['x'] + x
                    abs_y = self.simulator_window_bounds['y'] + y
                    pyautogui.click(abs_x, abs_y)
                    return True
                
            elif event_type == "swipe":
                # This would need additional parameters (end_x, end_y)
                pass
            
            return True
            
        except Exception as e:
            print(f"❌ Error handling touch event: {e}")
            return False

class RemoteSimulatorServer:
    def __init__(self, simulator_manager, host: str = "0.0.0.0", port: int = 5000):
        self.simulator_manager = simulator_manager
        self.host = host
        self.port = port
        self.streamers: Dict[str, SimulatorStreamer] = {}
        self.templates = Jinja2Templates(directory="templates") 

        # Setup FastAPI
        self.app = FastAPI(title="iOS Simulator Remote Control")
        self.router = APIRouter()
        
        # Setup SocketIO
        self.sio = socketio.AsyncServer(
            async_mode="asgi", 
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False
        )
        
        self.setup_routes()
        self.setup_socket_handlers()
        self.setup_websocket_handlers()

        # Create ASGI app combining FastAPI and Socket.IO
        self.asgi_app = socketio.ASGIApp(self.sio, self.app)

    def setup_routes(self):
        """Setup HTTP routes"""
        
        @self.router.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            return self.templates.TemplateResponse("simulator_control.html", {"request": request})

        @self.router.get("/sessions")
        async def list_sessions():
            sessions = self.simulator_manager.list_active_sessions()
            return JSONResponse(content=sessions)

        @self.router.get("/start_stream/{session_id}")
        async def start_stream(session_id: str):
            if session_id not in self.simulator_manager.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")

            session = self.simulator_manager.active_sessions[session_id]
            if session_id not in self.streamers:
                streamer = SimulatorStreamer(session_id, session.udid)
                self.streamers[session_id] = streamer

            # IMPORTANT: Start streaming immediately
            streamer = self.streamers[session_id]
            if not streamer.streaming:
                streamer.start_streaming()
                
            # Give it a moment to capture first frame
            await asyncio.sleep(0.5)
            
            return {"success": True, "session_id": session_id, "streaming": streamer.streaming}

        @self.router.get("/stop_stream/{session_id}")
        async def stop_stream(session_id: str):
            if session_id in self.streamers:
                self.streamers[session_id].stop_streaming()
                del self.streamers[session_id]
            return {"success": True}

        @self.router.post("/touch/{session_id}")
        async def handle_touch(session_id: str, request: Request):
            if session_id not in self.streamers:
                raise HTTPException(status_code=404, detail="Stream not active")

            data = await request.json()
            x = data.get("x", 0)
            y = data.get("y", 0)
            event_type = data.get("type", "tap")

            success = self.streamers[session_id].handle_touch_event(x, y, event_type)
            return {"success": success}

        @self.router.get("/frame/{session_id}")
        async def get_frame(session_id: str):
            if session_id not in self.simulator_manager.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.simulator_manager.active_sessions[session_id]
            print(f"🎯 Frame request for session {session_id[:8]} (UDID: {session.udid[:8]})")
            
            # If no streamer exists, create one
            if session_id not in self.streamers:
                print("📺 Creating new streamer...")
                streamer = SimulatorStreamer(session_id, session.udid)
                self.streamers[session_id] = streamer
            else:
                streamer = self.streamers[session_id]
            
            # Always try to capture a frame, regardless of streaming status
            print("📸 Attempting to capture frame...")
            frame_data = streamer.capture_simulator_screen()
            
            if frame_data is None:
                # Try alternative capture methods
                print("🔄 Primary capture failed, trying alternatives...")
                
                # Method 1: Ensure simulator is visible and retry
                if streamer.ensure_simulator_visible():
                    await asyncio.sleep(1)  # Wait for simulator to be ready
                    frame_data = streamer.capture_simulator_screen()
                
                # Method 2: Try direct simctl screenshot
                if frame_data is None:
                    frame_data = streamer._capture_via_simctl()
                
                # Method 3: Try full screen capture as last resort
                if frame_data is None:
                    print("🔄 Trying full screen capture...")
                    try:
                        screenshot = ImageGrab.grab()
                        img_buffer = io.BytesIO()
                        screenshot.save(img_buffer, format='JPEG', quality=80)
                        img_buffer.seek(0)
                        frame_data = img_buffer.read()
                        print("✅ Full screen capture successful")
                    except Exception as e:
                        print(f"❌ Full screen capture failed: {e}")
            
            if frame_data is None:
                # Provide detailed error information
                debug_info = {
                    "session_exists": session_id in self.simulator_manager.active_sessions,
                    "udid": session.udid,
                    "simulator_running": await self._check_simulator_running(session.udid),
                    "available_windows": await self._get_available_windows()
                }
                raise HTTPException(
                    status_code=503, 
                    detail=f"Unable to capture frame. Debug info: {debug_info}"
                )
            
            # Store the frame for future use
            with streamer.frame_lock:
                streamer.latest_frame = frame_data
            
            print(f"✅ Returning frame ({len(frame_data)} bytes)")
            return Response(content=frame_data, media_type="image/jpeg")

        # NEW: Add device action endpoints
        @self.router.post("/device_action/{session_id}")
        async def device_action(session_id: str, request: Request):
            if session_id not in self.simulator_manager.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.simulator_manager.active_sessions[session_id]
            data = await request.json()
            action = data.get("action", "")
            
            try:
                if action == "home":
                    command = ['xcrun', 'simctl', 'ui', session.udid, 'home']
                    subprocess.run(command, check=True)
                elif action == "lock":
                    command = ['xcrun', 'simctl', 'ui', session.udid, 'lock']
                    subprocess.run(command, check=True)
                elif action == "rotate":
                    # Toggle between portrait and landscape
                    command = ['xcrun', 'simctl', 'ui', session.udid, 'rotate', 'left']
                    subprocess.run(command, check=True)
                else:
                    raise HTTPException(status_code=400, detail="Unknown action")
                
                return {"success": True}
            except subprocess.CalledProcessError as e:
                raise HTTPException(status_code=500, detail=f"Device action failed: {e}")

        # NEW: Add screenshot endpoint
        @self.router.get("/screenshot/{session_id}")
        async def take_screenshot(session_id: str):
            if session_id not in self.simulator_manager.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.simulator_manager.active_sessions[session_id]
            
            try:
                # Use simctl to take screenshot
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    command = ['xcrun', 'simctl', 'io', session.udid, 'screenshot', tmp_file.name]
                    subprocess.run(command, check=True)
                    
                    # Read the screenshot
                    with open(tmp_file.name, 'rb') as f:
                        screenshot_data = f.read()
                    
                    # Clean up temp file
                    os.unlink(tmp_file.name)
                    
                    return Response(content=screenshot_data, media_type="image/png")
                    
            except subprocess.CalledProcessError as e:
                raise HTTPException(status_code=500, detail=f"Screenshot failed: {e}")

        # Add helper endpoints for debugging
        @self.router.get("/debug/{session_id}")
        async def debug_session(session_id: str):
            """Enhanced debug endpoint"""
            if session_id not in self.simulator_manager.active_sessions:
                return {"error": "Session not found"}
            
            session = self.simulator_manager.active_sessions[session_id]
            streamer = self.streamers.get(session_id)
            
            debug_info = {
                "session_exists": True,
                "udid": session.udid,
                "device_type": session.device_type,
                "ios_version": session.ios_version,
                "streamer_exists": streamer is not None,
                "streaming_active": streamer.streaming if streamer else False,
                "has_frame": streamer.latest_frame is not None if streamer else False,
                "window_bounds": streamer.simulator_window_bounds if streamer else None,
                "simulator_running": await self._check_simulator_running(session.udid),
                "available_windows": await self._get_available_windows()
            }
            
            return debug_info

        self.app.include_router(self.router)

    async def _check_simulator_running(self, udid: str) -> bool:
        """Check if simulator is running"""
        try:
            result = subprocess.run(
                ['xcrun', 'simctl', 'list', 'devices', '-j'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for runtime, devices in data.get('devices', {}).items():
                    for device in devices:
                        if device.get('udid') == udid:
                            return device.get('state') == 'Booted'
            return False
        except Exception:
            return False

    async def _get_available_windows(self) -> List[Dict]:
        """Get list of available simulator windows"""
        try:
            window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
            simulator_windows = []
            
            for window in window_list:
                window_name = window.get('kCGWindowName', '')
                window_owner = window.get('kCGWindowOwnerName', '')
                
                if window_owner == 'Simulator':
                    simulator_windows.append({
                        'name': window_name,
                        'owner': window_owner,
                        'bounds': window.get('kCGWindowBounds', {})
                    })
            
            return simulator_windows
        except Exception as e:
            return [{"error": str(e)}]

    def setup_websocket_handlers(self):
        """Setup native WebSocket handlers"""
        @self.app.websocket("/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            await websocket.accept()
            
            if session_id not in self.streamers:
                await websocket.close(code=4004, reason="Stream not active")
                return
            
            streamer = self.streamers[session_id]
            streamer.add_websocket_client(websocket)
            
            try:
                while True:
                    # Keep connection alive and handle incoming messages
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    if message.get('type') == 'touch':
                        x = message.get('x', 0)
                        y = message.get('y', 0)
                        event_type = message.get('event_type', 'tap')
                        
                        success = streamer.handle_touch_event(x, y, event_type)
                        await websocket.send_text(json.dumps({
                            'type': 'touch_result',
                            'success': success
                        }))
                        
            except WebSocketDisconnect:
                pass
            finally:
                streamer.remove_websocket_client(websocket)

    def setup_socket_handlers(self):
        """Setup Socket.IO handlers"""
        @self.sio.event
        async def connect(sid, environ):
            print(f"🔌 SocketIO Client connected: {sid}")

        @self.sio.event
        async def disconnect(sid):
            print(f"❌ SocketIO Client disconnected: {sid}")
            # Remove from all streamers
            for streamer in self.streamers.values():
                streamer.remove_socketio_client(sid)

        @self.sio.event
        async def start_stream(sid, data):
            session_id = data.get("session_id")
            if session_id and session_id in self.simulator_manager.active_sessions:
                if session_id not in self.streamers:
                    session = self.simulator_manager.active_sessions[session_id]
                    streamer = SimulatorStreamer(session_id, session.udid)
                    self.streamers[session_id] = streamer

                streamer = self.streamers[session_id]
                streamer.add_socketio_client(sid)
                streamer.start_streaming()
                
                await self.sio.emit("stream_started", {"session_id": session_id}, to=sid)
                
                # Start broadcasting frames to this client
                asyncio.create_task(self._socketio_frame_broadcaster(session_id, sid))

        @self.sio.event
        async def touch_event(sid, data):
            session_id = data.get("session_id")
            if session_id in self.streamers:
                x = data.get("x", 0)
                y = data.get("y", 0)
                event_type = data.get("type", "tap")
                success = self.streamers[session_id].handle_touch_event(x, y, event_type)
                await self.sio.emit("touch_result", {"success": success}, to=sid)

    async def _socketio_frame_broadcaster(self, session_id: str, sid: str):
        """Broadcast frames to a specific SocketIO client"""
        streamer = self.streamers.get(session_id)
        if not streamer:
            return
        
        frame_delay = 1.0 / streamer.fps
        
        while streamer.streaming and sid in streamer.socketio_clients:
            try:
                frame_data = streamer.get_latest_frame()
                if frame_data:
                    frame_b64 = base64.b64encode(frame_data).decode('utf-8')
                    await self.sio.emit('frame_update', {
                        'session_id': session_id,
                        'frame': frame_b64
                    }, to=sid)
                
                await asyncio.sleep(frame_delay)
                
            except Exception as e:
                print(f"Error broadcasting to {sid}: {e}")
                break
        
        # Clean up
        if streamer:
            streamer.remove_socketio_client(sid)

    def start_server(self, reload: bool = False):
        """Start server using Uvicorn with reload support"""
        print(f"🌐 Starting remote simulator server on http://{self.host}:{self.port}")
        
        # Configure logging for reload mode
        if reload:
            log_level = "debug"
            print("🔄 Hot reload enabled - server will restart on file changes")
        else:
            log_level = "info"
        
        uvicorn.run(
            "SimulaotrStreamServer:create_app",  # Use factory function for reload
            host=self.host, 
            port=self.port, 
            log_level=log_level,
            reload=reload,
            reload_dirs=["./"] if reload else None
        )

    def cleanup(self):
        """Cleanup server resources - DON'T kill simulators!"""
        print("🧹 Cleaning up server resources...")
        
        # Stop all streamers but keep simulators running
        for streamer in self.streamers.values():
            streamer.stop_streaming()
        self.streamers.clear()
        
        print("✅ Server cleanup complete - simulators remain running")

# Enhanced simulator manager with persistent storage
class EnhancediOSSimulatorManager:
    def __init__(self, storage_file: str = "simulator_sessions.json"):
        self.simulator_manager = iOSSimulatorManager()
        self.session_storage = SessionStorage(storage_file)
        self.remote_server = None
        self.server_thread = None
        
        # Setup cleanup handlers for graceful shutdown
        self._setup_cleanup_handlers()
        
        # Initialize and verify sessions on startup
        self._initialize_sessions()
    
    def _initialize_sessions(self):
        """Initialize sessions from storage and create new ones if needed"""
        print("🔄 Initializing simulator sessions...")
        
        stored_sessions = self.session_storage.get_all_sessions()
        verified_sessions = []
        
        # First, verify existing sessions
        for session_id, session_data in stored_sessions.items():
            if self._verify_simulator_session(session_id, session_data):
                verified_sessions.append(session_id)
                print(f"✅ Verified existing session: {session_id[:8]} - {session_data.get('device_type')} (iOS {session_data.get('ios_version')})")
        
        # If no valid sessions exist, create a default one
        if not verified_sessions:
            print("📱 No valid sessions found, creating new simulator...")
            try:
                session_id = self._create_new_simulator_session("iPhone 14", "18.2")
                if session_id:
                    print(f"✅ Created new simulator session: {session_id[:8]}")
                    verified_sessions.append(session_id)
                else:
                    print("❌ Failed to create new simulator session")
            except Exception as e:
                print(f"❌ Error creating new simulator: {e}")
        
        print(f"📱 Initialized with {len(verified_sessions)} active simulator sessions")
    
    def _verify_simulator_session(self, session_id: str, session_data: dict) -> bool:
        """Verify if a stored session is still valid and running"""
        try:
            udid = session_data.get('udid')
            if not udid:
                print(f"⚠️  Session {session_id[:8]} missing UDID")
                return False
            
            # Check if simulator is still available in simctl
            result = subprocess.run(
                ['xcrun', 'simctl', 'list', 'devices', '-j'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                print(f"⚠️  Failed to list devices: {result.stderr}")
                return False
            
            devices_data = json.loads(result.stdout)
            
            # Find the device
            device_found = False
            device_state = None
            device_info = None
            runtime_name = None
            
            for runtime, devices in devices_data.get('devices', {}).items():
                for device in devices:
                    if device.get('udid') == udid:
                        device_found = True
                        device_state = device.get('state')
                        device_info = device
                        runtime_name = runtime
                        break
                if device_found:
                    break
            
            if not device_found:
                print(f"⚠️  Simulator {udid[:8]} not found in device list")
                self.session_storage.remove_session(session_id)
                return False
            
            # Try to boot the simulator if it's not running
            if device_state != 'Booted':
                print(f"🔄 Starting simulator {udid[:8]}...")
                boot_result = subprocess.run(
                    ['xcrun', 'simctl', 'boot', udid],
                    capture_output=True, text=True, timeout=30
                )
                
                if boot_result.returncode != 0 and "already booted" not in boot_result.stderr.lower():
                    print(f"⚠️  Failed to boot simulator: {boot_result.stderr}")
                    return False
                
                # Wait a bit for simulator to boot
                time.sleep(3)
                
                # Open simulator app
                try:
                    subprocess.Popen(['open', '-a', 'Simulator', '--args', '-CurrentDeviceUDID', udid])
                except Exception as e:
                    print(f"⚠️  Could not open Simulator app: {e}")
            
            # Create SimulatorDevice object
            from IOSSimulatorManager import SimulatorDevice, SimulatorSession
            
            simulator_device = SimulatorDevice(
                name=device_info.get('name', f"Simulator-{udid[:8]}"),
                identifier=udid,
                runtime=runtime_name or session_data.get('ios_version', '18.2'),
                state=device_info.get('state', 'Booted'),
                udid=udid
            )
            
            # Get the created_at timestamp from stored data or use current time
            created_at = session_data.get('created_at')
            if created_at:
                # Convert ISO string back to timestamp if needed
                if isinstance(created_at, str):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        created_at = dt.timestamp()
                    except:
                        created_at = time.time()
            else:
                created_at = time.time()
            
            # Create session object with correct parameters
            session = SimulatorSession(
                session_id=session_id,
                device=simulator_device,
                udid=udid,
                device_type=session_data.get('device_type', 'iPhone 14'),
                ios_version=session_data.get('ios_version', '18.2'),
                created_at=created_at,
                pid=self._get_simulator_pid(udid)
            )
            
            # Add to active sessions
            self.simulator_manager.active_sessions[session_id] = session
            
            # Update verification time
            self.session_storage.update_session_verification(session_id)
            
            return True
            
        except Exception as e:
            print(f"❌ Error verifying session {session_id[:8]}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_simulator_pid(self, udid: str) -> Optional[int]:
        """Get the process ID of a running simulator"""
        try:
            command = ['pgrep', '-f', f'CurrentDeviceUDID {udid}']
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split('\n')[0])
        except Exception as e:
            print(f"⚠️  Could not get simulator PID: {e}")
        return None
    
    def _create_new_simulator_session(self, device_type: str, ios_version: str) -> Optional[str]:
        """Create a new simulator session and store it"""
        try:
            # Use the underlying simulator manager to create the simulator
            session_id = self.simulator_manager.start_simulator(device_type, ios_version)
            
            if session_id and session_id in self.simulator_manager.active_sessions:
                # Get the session object
                session = self.simulator_manager.active_sessions[session_id]
                
                # Store session data persistently
                session_data = {
                    'session_id': session_id,
                    'udid': session.udid,
                    'device_type': session.device_type,
                    'ios_version': session.ios_version,
                    'status': 'active',
                    'created_at': session.created_at  # Store as timestamp, not ISO string
                }
                
                self.session_storage.add_session(session_id, session_data)
                print(f"💾 Stored new session: {session_id[:8]} - {device_type} (iOS {ios_version})")
                
                return session_id
            else:
                print("❌ Failed to create simulator session")
                return None
                
        except Exception as e:
            print(f"❌ Error creating new simulator session: {e}")
            return None
    
    @property
    def active_sessions(self):
        """Delegate to underlying simulator manager"""
        return self.simulator_manager.active_sessions
    
    def start_simulator(self, device_type: str, ios_version: str):
        """Create a new simulator and store it persistently"""
        return self._create_new_simulator_session(device_type, ios_version)
    
    def list_active_sessions(self):
        """Delegate to underlying simulator manager"""
        return self.simulator_manager.list_active_sessions()
    
    def _setup_cleanup_handlers(self):
        """Setup cleanup handlers to preserve simulators on exit"""
        def cleanup_handler(signum=None, frame=None):
            print("🔄 Server shutting down - preserving simulators...")
            if self.remote_server:
                self.remote_server.cleanup()
            print("✅ Cleanup complete - simulators preserved")
        
        # Register cleanup for different exit scenarios
        signal.signal(signal.SIGINT, cleanup_handler)
        signal.signal(signal.SIGTERM, cleanup_handler)
        atexit.register(cleanup_handler)
    
    def start_remote_server(self, host: str = "0.0.0.0", port: int = 5000, reload: bool = False):
        """Start remote control server with persistence and reload support"""
        if self.remote_server and not reload:
            print("⚠️  Remote server already running, stopping it first...")
            self.stop_remote_server()
        
        print(f"📱 Found {len(self.active_sessions)} active simulator sessions")
        for session_id, session in self.active_sessions.items():
            print(f"   📲 {session.device_type} (iOS {session.ios_version}) - {session_id[:8]}")
        
        self.remote_server = RemoteSimulatorServer(self, host, port)
        
        if reload:
            # For hot reload, run server directly (blocking)
            print("🔄 Starting server with hot reload...")
            self.remote_server.start_server(reload=True)
        else:
            # Start server in a separate thread
            self.server_thread = threading.Thread(
                target=self.remote_server.start_server,
                daemon=False  # Don't make it daemon so we can clean it up properly
            )
            self.server_thread.start()
            
            print(f"🌐 Remote server started at http://{host}:{port}")
            return self.server_thread
    
    def stop_remote_server(self):
        """Stop remote control server while preserving simulators"""
        if self.remote_server:
            print("🛑 Stopping remote server (preserving simulators)...")
            self.remote_server.cleanup()
            self.remote_server = None
        
        if self.server_thread and self.server_thread.is_alive():
            print("⏳ Waiting for server thread to finish...")
            self.server_thread.join(timeout=5)  # Wait up to 5 seconds
            if self.server_thread.is_alive():
                print("⚠️  Server thread didn't stop gracefully")
            else:
                print("✅ Server thread stopped")
        
        self.server_thread = None
        
        # Note: We deliberately DON'T call simulator_manager cleanup
        print(f"💾 {len(self.active_sessions)} simulator sessions preserved")

# Factory function for uvicorn reload
def create_app():
    """Factory function to create the app for hot reload"""
    manager = EnhancediOSSimulatorManager()
    server = RemoteSimulatorServer(manager, "0.0.0.0", 5002)
    return server.asgi_app

# For direct execution
if __name__ == "__main__":
    manager = EnhancediOSSimulatorManager()
    
    # Start with reload for development
    manager.start_remote_server(host="0.0.0.0", port=5002, reload=True)