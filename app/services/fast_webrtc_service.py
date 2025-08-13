import threading
import time
import asyncio
import uuid
import base64
import io
from typing import Dict, Optional
from queue import Queue, Empty
import av
import numpy as np
from PIL import Image
from fractions import Fraction
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceCandidate, RTCConfiguration

from app.core.logging import logger
from app.services.screenshot_service import ScreenshotService

class FastVideoTrack(VideoStreamTrack):
    """Fast video track optimized for low latency streaming"""
    
    def __init__(self, service, target_fps=60):
        super().__init__()
        self.service = service
        self.frame_count = 0
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.start_time = time.time()
        self.last_frame_data = None
        logger.info(f"🚀 FastVideoTrack initialized: {target_fps}fps")
    
    async def recv(self):
        """Generate fast video frames with consistent timing"""
        # Calculate precise frame timing
        target_time = self.start_time + (self.frame_count * self.frame_interval)
        current_time = time.time()
        
        # Wait for precise timing
        wait_time = target_time - current_time
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        # Get frame from service
        frame_data = await self.service.get_fast_frame()
        
        if frame_data is not None:
            self.last_frame_data = frame_data
            frame = frame_data
        elif self.last_frame_data is not None:
            # Reuse last frame if no new data
            frame = self.last_frame_data
        else:
            # Create minimal placeholder
            frame = av.VideoFrame.from_ndarray(
                np.zeros((200, 200, 3), dtype=np.uint8),
                format='rgb24'
            )
        
        # Set WebRTC timing
        frame.pts = self.frame_count
        frame.time_base = Fraction(1, self.target_fps)
        
        self.frame_count += 1
        return frame

class FastWebRTCService:
    """Fast WebRTC service optimized for continuous streaming with low latency"""
    
    def __init__(self, udid: Optional[str] = None):
        self.udid = udid
        
        # WebRTC state
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.stream_active = False
        self.frame_queue = Queue(maxsize=1)  # Single frame buffer for lowest latency
        
        # Stream processing
        self.frame_thread = None
        self.stream_lock = threading.Lock()
        
        # Fast streaming settings
        self.target_fps = 60
        self.quality_preset = "medium"
        
        logger.info(f"🚀 FastWebRTCService initialized for {udid}")
    
    def set_udid(self, udid: str):
        """Set the UDID for this service instance"""
        self.udid = udid
        logger.info(f"🎯 Fast WebRTC UDID set to: {udid}")
    
    def start_video_stream(self, quality: str = "medium", fps: int = 60) -> bool:
        """Start fast continuous streaming"""
        if not self.udid:
            logger.error("❌ No UDID set for fast WebRTC streaming")
            return False
        
        with self.stream_lock:
            if self.stream_active:
                logger.info(f"✅ Fast WebRTC stream already active for {self.udid}")
                return True
            
            self.target_fps = fps
            self.quality_preset = quality
            
            try:
                logger.info(f"🚀 Starting fast WebRTC stream for {self.udid} at {fps}fps")
                
                self.stream_active = True
                
                # Start continuous frame generation
                self.frame_thread = threading.Thread(
                    target=self._generate_fast_frames,
                    daemon=True
                )
                self.frame_thread.start()
                
                logger.info(f"✅ Fast WebRTC stream started for {self.udid}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to start fast WebRTC stream for {self.udid}: {e}")
                return False
    
    def _generate_fast_frames(self):
        """Generate frames continuously for smooth streaming"""
        logger.info(f"🎬 Starting fast frame generation for {self.udid} @ {self.target_fps}fps")
        
        try:
            screenshot_service = ScreenshotService(self.udid)
            
            frame_count = 0
            frame_interval = 1.0 / self.target_fps
            next_frame_time = time.time()
            last_log_time = time.time()
            
            while self.stream_active:
                current_time = time.time()
                
                # Precise timing control
                if current_time < next_frame_time:
                    sleep_time = next_frame_time - current_time
                    if sleep_time > 0.001:
                        time.sleep(sleep_time)
                    continue
                
                try:
                    # Fast screenshot capture
                    if self.quality_preset in ["high", "ultra"]:
                        screenshot_data = screenshot_service.capture_high_quality_screenshot()
                    else:
                        screenshot_data = screenshot_service.capture_ultra_fast_screenshot()
                    
                    if screenshot_data and "data" in screenshot_data:
                        # Quick image processing
                        image_bytes = base64.b64decode(screenshot_data["data"])
                        
                        with Image.open(io.BytesIO(image_bytes)) as img:
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            # Optimize resolution for speed vs quality
                            if self.quality_preset == "ultra":
                                target_size = (468, 1014)  # 2x logical
                            elif self.quality_preset == "high":
                                target_size = (390, 844)   # 1.67x logical
                            elif self.quality_preset == "medium":
                                target_size = (312, 675)   # 1.33x logical
                            else:  # low
                                target_size = (234, 507)   # 1x logical
                            
                            # Fast resize
                            img = img.resize(target_size, Image.Resampling.BILINEAR)  # Faster than LANCZOS
                            
                            # Convert to frame
                            img_array = np.array(img, dtype=np.uint8)
                            av_frame = av.VideoFrame.from_ndarray(img_array, format='rgb24')
                            
                            # Replace frame in queue (always fresh frame)
                            while not self.frame_queue.empty():
                                try:
                                    self.frame_queue.get_nowait()
                                except Empty:
                                    break
                            
                            try:
                                self.frame_queue.put_nowait(av_frame)
                                frame_count += 1
                            except:
                                pass  # Queue management
                    
                    # Update timing
                    next_frame_time += frame_interval
                    
                    # Prevent timing drift
                    if next_frame_time < current_time:
                        next_frame_time = current_time + frame_interval
                    
                    # Periodic status
                    if current_time - last_log_time >= 15.0:
                        actual_fps = frame_count / (current_time - last_log_time) if (current_time - last_log_time) > 0 else 0
                        logger.info(f"📊 Fast WebRTC {self.udid}: {frame_count} frames, {actual_fps:.1f}fps, queue: {self.frame_queue.qsize()}")
                        last_log_time = current_time
                        frame_count = 0
                
                except Exception as e:
                    logger.debug(f"Frame generation error: {e}")
                    next_frame_time += frame_interval
                    
        except Exception as e:
            logger.error(f"Fast frame generation error for {self.udid}: {e}")
        finally:
            logger.info(f"🛑 Fast frame generation stopped for {self.udid}")
    
    async def get_fast_frame(self):
        """Get next frame with minimal delay"""
        try:
            frame = self.frame_queue.get(timeout=0.02)  # Very short timeout
            return frame
        except Empty:
            return None
    
    def stop_video_stream(self):
        """Stop video streaming and cleanup"""
        logger.info(f"🛑 Stopping fast WebRTC stream for {self.udid}")
        
        with self.stream_lock:
            self.stream_active = False
            
            # Clear frame queue
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    break
        
        # Close all peer connections
        connections_to_close = list(self.peer_connections.items())
        self.peer_connections.clear()
        
        for connection_id, pc in connections_to_close:
            try:
                asyncio.create_task(pc.close())
            except Exception as e:
                logger.debug(f"Error closing connection {connection_id}: {e}")
    
    async def create_peer_connection(self) -> tuple[str, RTCPeerConnection]:
        """Create new WebRTC peer connection optimized for speed"""
        if not self.stream_active:
            if not self.start_video_stream(self.quality_preset, self.target_fps):
                raise Exception("Failed to start fast WebRTC stream")
        
        connection_id = str(uuid.uuid4())
        
        # Simple WebRTC configuration for speed
        config = RTCConfiguration(iceServers=[])
        pc = RTCPeerConnection(configuration=config)
        
        # Add fast video track
        video_track = FastVideoTrack(self, target_fps=self.target_fps)
        pc.addTrack(video_track)
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():  # noqa: F841
            logger.info(f"🔗 Fast WebRTC connection state for {self.udid}: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed"]:
                self.remove_connection(connection_id)
        
        self.peer_connections[connection_id] = pc
        logger.info(f"🤝 Created fast WebRTC peer connection: {connection_id} for {self.udid}")
        return connection_id, pc
    
    async def handle_offer(self, pc: RTCPeerConnection, offer_data: Dict) -> Dict:
        """Handle WebRTC offer"""
        logger.info(f"📤 Handling fast WebRTC offer for {self.udid}")
        
        await pc.setRemoteDescription(RTCSessionDescription(
            sdp=offer_data["sdp"],
            type=offer_data["type"]
        ))
        
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        logger.info(f"📥 Fast WebRTC answer created for {self.udid}")
        
        return {
            "type": "answer",
            "sdp": pc.localDescription.sdp
        }
    
    async def handle_ice_candidate(self, pc: RTCPeerConnection, candidate_data: Dict):
        """Handle ICE candidate"""
        logger.debug(f"🧊 Handling ICE candidate for fast WebRTC {self.udid}")
        candidate_info = candidate_data.get("candidate")
        if candidate_info:
            candidate = RTCIceCandidate(
                candidate=candidate_info.get("candidate"),
                sdpMid=candidate_info.get("sdpMid"),
                sdpMLineIndex=candidate_info.get("sdpMLineIndex")
            )
            await pc.addIceCandidate(candidate)
    
    def remove_connection(self, connection_id: str):
        """Remove connection and cleanup if no more connections"""
        if connection_id in self.peer_connections:
            try:
                del self.peer_connections[connection_id]
                logger.info(f"🗑️  Removed fast WebRTC connection: {connection_id}")
            except KeyError:
                pass
        
        # Stop stream if no more connections
        if not self.peer_connections:
            self.stop_video_stream()
    
    def set_quality(self, quality: str) -> Dict:
        """Set streaming quality preset"""
        valid_qualities = ["low", "medium", "high", "ultra"]
        if quality not in valid_qualities:
            return {"success": False, "error": f"Invalid quality. Must be one of: {valid_qualities}"}
        
        old_quality = self.quality_preset
        self.quality_preset = quality
        
        logger.info(f"🎚️  Quality changed from {old_quality} to {quality} for {self.udid}")
        return {"success": True, "quality": quality}
    
    def set_fps(self, fps: int) -> Dict:
        """Set target FPS"""
        if fps < 20 or fps > 120:
            return {"success": False, "error": "FPS must be between 20 and 120"}
        
        old_fps = self.target_fps
        self.target_fps = fps
        
        # Restart if active
        was_active = self.stream_active
        if was_active:
            self.stop_video_stream()
            self.start_video_stream(self.quality_preset, fps)
        
        logger.info(f"📊 FPS changed from {old_fps} to {fps} for {self.udid}")
        return {"success": True, "fps": fps}
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            "stream_active": self.stream_active,
            "connections": len(self.peer_connections),
            "quality": self.quality_preset,
            "fps": self.target_fps,
            "queue_size": self.frame_queue.qsize(),
            "udid": self.udid,
            "type": "fast_screenshot_webrtc"
        }