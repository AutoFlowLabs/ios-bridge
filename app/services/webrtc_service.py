import threading
import time
import base64
import io
import uuid
import numpy as np
from typing import Dict, Optional
from queue import Queue, Empty
from PIL import Image
import av
from fractions import Fraction
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceCandidate

from app.config.settings import settings
from app.core.logging import logger
from app.services.screenshot_service import ScreenshotService

class SimulatorVideoTrack(VideoStreamTrack):
    """Enhanced video track for iOS Simulator"""
    
    def __init__(self, webrtc_service, target_fps=60):
        super().__init__()
        self.webrtc_service = webrtc_service
        self.frame_count = 0
        self.target_fps = target_fps
        self.frame_time = 1.0 / target_fps
        self.last_frame_time = time.time()
    
    async def recv(self):
        """Generate high-quality video frames for WebRTC"""
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        if elapsed < self.frame_time:
            import asyncio
            await asyncio.sleep(self.frame_time - elapsed)
        
        frame = self.webrtc_service.get_current_frame()
        if frame is None:
            # Generate placeholder frame
            frame = av.VideoFrame.from_ndarray(
                np.zeros((844, 390, 3), dtype=np.uint8),
                format='rgb24'
            )
        
        # Set precise timing
        frame.pts = self.frame_count
        frame.time_base = Fraction(1, self.target_fps)
        self.frame_count += 1
        self.last_frame_time = time.time()
        
        return frame

class WebRTCService:
    """Service for WebRTC video streaming"""
    
    def __init__(self):
        self.screenshot_service = ScreenshotService()
        
        # WebRTC state
        self.webrtc_connections: Dict[str, RTCPeerConnection] = {}
        self.webrtc_active = False
        self.webrtc_current_frame = None
        self.webrtc_frame_lock = threading.Lock()
        self.webrtc_frame_thread = None
        self.webrtc_quality_settings = {
            "fps": 60, 
            "resolution_scale": 2, 
            "quality": 95
        }
    
    def start_webrtc_capture(self, fps: int = 60) -> bool:
        """Start high-quality WebRTC video capture"""
        if self.webrtc_active:
            return True
        
        try:
            self.webrtc_active = True
            self.webrtc_frame_thread = threading.Thread(
                target=self._webrtc_frame_producer,
                daemon=True
            )
            self.webrtc_frame_thread.start()
            logger.info(f"✅ High-quality WebRTC capture started at {fps}fps")
            return True
        except Exception as e:
            logger.error(f"❌ WebRTC capture failed: {e}")
            self.webrtc_active = False
            return False
    
    def stop_webrtc_capture(self):
        """Stop WebRTC video capture"""
        self.webrtc_active = False
        
        with self.webrtc_frame_lock:
            self.webrtc_current_frame = None
        
        # Close all connections
        connections_to_close = list(self.webrtc_connections.items())
        self.webrtc_connections.clear()
        
        for connection_id, pc in connections_to_close:
            try:
                import asyncio
                asyncio.create_task(pc.close())
                logger.debug(f"Closed WebRTC connection: {connection_id}")
            except Exception as e:
                logger.debug(f"Error closing WebRTC connection {connection_id}: {e}")
    
    def _webrtc_frame_producer(self):
        """High-quality frame producer for WebRTC"""
        logger.info("Starting high-quality WebRTC frame producer...")
        
        target_fps = self.webrtc_quality_settings["fps"]
        frame_interval = 1.0 / target_fps
        last_capture = 0
        frame_count = 0
        
        while self.webrtc_active:
            frame_start = time.time()
            
            if frame_start - last_capture >= frame_interval:
                try:
                    screenshot_data = self.screenshot_service.capture_high_quality_screenshot()
                    
                    if screenshot_data:
                        # Decode and process image
                        image_bytes = base64.b64decode(screenshot_data["data"])
                        
                        with Image.open(io.BytesIO(image_bytes)) as img:
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            # High-quality resize
                            scale = self.webrtc_quality_settings["resolution_scale"]
                            target_width = int(390 * scale)
                            target_height = int(844 * scale)
                            
                            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                            img_array = np.array(img, dtype=np.uint8)
                            
                            if img_array.shape[2] == 4:  # RGBA
                                img_array = img_array[:, :, :3]  # Convert to RGB
                        
                        # Create AV frame
                        new_frame = av.VideoFrame.from_ndarray(img_array, format='rgb24')
                        
                        with self.webrtc_frame_lock:
                            self.webrtc_current_frame = new_frame
                        
                        frame_count += 1
                    
                    last_capture = frame_start
                    
                except Exception as e:
                    logger.error(f"WebRTC frame producer error: {e}")
                    time.sleep(0.01)
            else:
                sleep_time = frame_interval - (time.time() - last_capture)
                if sleep_time > 0.001:
                    time.sleep(min(sleep_time, 0.01))
    
    def get_current_frame(self):
        """Get current frame thread-safely"""
        with self.webrtc_frame_lock:
            if self.webrtc_current_frame is None:
                return None
            # Create a new frame from the same data
            frame_array = self.webrtc_current_frame.to_ndarray(format='rgb24')
            return av.VideoFrame.from_ndarray(frame_array, format='rgb24')
    
    async def create_peer_connection(self) -> tuple[str, RTCPeerConnection]:
        """Create new peer connection"""
        if not self.webrtc_active:
            self.start_webrtc_capture()
        
        connection_id = str(uuid.uuid4())
        pc = RTCPeerConnection()
        
        # Add video track
        video_track = SimulatorVideoTrack(self, target_fps=self.webrtc_quality_settings["fps"])
        pc.addTrack(video_track)
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"WebRTC connection state: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed"]:
                if connection_id in self.webrtc_connections:
                    try:
                        del self.webrtc_connections[connection_id]
                        logger.info(f"Removed failed WebRTC connection: {connection_id}")
                    except KeyError:
                        pass
        
        self.webrtc_connections[connection_id] = pc
        return connection_id, pc
    
    async def handle_offer(self, pc: RTCPeerConnection, offer_data: Dict) -> Dict:
        """Handle WebRTC offer"""
        await pc.setRemoteDescription(RTCSessionDescription(
            sdp=offer_data["sdp"],
            type=offer_data["type"]
        ))
        
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        return {
            "type": "answer",
            "sdp": pc.localDescription.sdp
        }
    
    async def handle_ice_candidate(self, pc: RTCPeerConnection, candidate_data: Dict):
        """Handle ICE candidate"""
        candidate_info = candidate_data.get("candidate")
        if candidate_info:
            candidate = RTCIceCandidate(
                candidate=candidate_info.get("candidate"),
                sdpMid=candidate_info.get("sdpMid"),
                sdpMLineIndex=candidate_info.get("sdpMLineIndex")
            )
            await pc.addIceCandidate(candidate)
    
    def remove_connection(self, connection_id: str):
        """Remove connection safely"""
        if connection_id in self.webrtc_connections:
            try:
                del self.webrtc_connections[connection_id]
            except KeyError:
                pass
        
        if not self.webrtc_connections:
            self.stop_webrtc_capture()
    
    def set_quality_preset(self, quality: str) -> Dict:
        """Set WebRTC quality preset"""
        presets = {
            "low": {"fps": 30, "resolution_scale": 1, "quality": 70},
            "medium": {"fps": 45, "resolution_scale": 1.5, "quality": 85},
            "high": {"fps": 60, "resolution_scale": 2, "quality": 95},
            "ultra": {"fps": 60, "resolution_scale": 2.5, "quality": 98}
        }
        
        if quality in presets:
            self.webrtc_quality_settings = presets[quality]
            logger.info(f"WebRTC quality set to: {quality}")
            return {"success": True, "quality": quality, "settings": presets[quality]}
        else:
            return {"success": False, "error": "Invalid quality preset"}
    
    def get_status(self) -> Dict:
        """Get WebRTC service status"""
        return {
            "webrtc_active": self.webrtc_active,
            "webrtc_connections": len(self.webrtc_connections),
            "quality_settings": self.webrtc_quality_settings
        }