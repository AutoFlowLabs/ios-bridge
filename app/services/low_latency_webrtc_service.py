import threading
import time
import asyncio
import uuid
import subprocess
import tempfile
import os
from typing import Dict, Optional, AsyncGenerator
from queue import Queue, Empty
import av
import numpy as np
from fractions import Fraction
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceCandidate, RTCConfiguration

from app.core.logging import logger

class IDBVideoStreamTrack(VideoStreamTrack):
    """Ultra low-latency video track using direct idb video-stream H.264 data"""
    
    def __init__(self, service, target_fps=60):
        super().__init__()
        self.service = service
        self.frame_count = 0
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.start_time = time.time()
        self.last_pts = 0
        logger.info(f"🚀 IDBVideoStreamTrack initialized: {target_fps}fps for ultra-low latency")
    
    async def recv(self):
        """Receive H.264 frames directly from idb video stream"""
        try:
            # Get H.264 frame from service
            frame = await self.service.get_h264_frame()
            
            if frame is not None:
                # Set precise timing for minimal latency
                current_time = time.time()
                elapsed = current_time - self.start_time
                expected_pts = int(elapsed * self.target_fps * 90000)  # 90kHz timebase
                
                frame.pts = expected_pts
                frame.time_base = Fraction(1, 90000)  # Standard RTP timebase
                
                self.frame_count += 1
                return frame
            
            # Return a minimal placeholder if no frame available
            placeholder = av.VideoFrame.from_ndarray(
                np.zeros((100, 100, 3), dtype=np.uint8),  # Minimal size
                format='rgb24'
            )
            placeholder.pts = self.last_pts + int(self.frame_interval * 90000)
            placeholder.time_base = Fraction(1, 90000)
            self.last_pts = placeholder.pts
            return placeholder
            
        except Exception as e:
            logger.debug(f"Frame recv error: {e}")
            # Return minimal placeholder on error
            placeholder = av.VideoFrame.from_ndarray(
                np.zeros((100, 100, 3), dtype=np.uint8),
                format='rgb24'
            )
            placeholder.pts = self.last_pts + int(self.frame_interval * 90000)
            placeholder.time_base = Fraction(1, 90000)
            self.last_pts = placeholder.pts
            return placeholder

class LowLatencyWebRTCService:
    """Ultra low-latency WebRTC service using direct idb video-stream H.264"""
    
    def __init__(self, udid: Optional[str] = None):
        self.udid = udid
        
        # WebRTC state
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.stream_active = False
        
        # H.264 streaming
        self.h264_process = None
        self.h264_file = None
        self.frame_queue = Queue(maxsize=2)  # Minimal buffer for ultra-low latency
        
        # Stream processing
        self.frame_thread = None
        self.stream_lock = threading.Lock()
        
        # Ultra low-latency settings
        self.target_fps = 60
        self.video_bitrate = 2000000  # 2Mbps for good quality
        self.keyframe_interval = 30  # I-frame every 30 frames (0.5s at 60fps)
        
        logger.info(f"🚀 LowLatencyWebRTCService initialized for {udid}")
    
    def set_udid(self, udid: str):
        """Set the UDID for this service instance"""
        self.udid = udid
        logger.info(f"🎯 Low-latency WebRTC UDID set to: {udid}")
    
    def start_video_stream(self, quality: str = "high", fps: int = 90) -> bool:
        """Start ultra low-latency H.264 streaming"""
        if not self.udid:
            logger.error("❌ No UDID set for low-latency WebRTC streaming")
            return False
        
        with self.stream_lock:
            if self.stream_active:
                logger.info(f"✅ Low-latency WebRTC stream already active for {self.udid}")
                return True
            
            self.target_fps = fps
            
            # Adjust settings based on quality preference for latency
            if quality == "ultra":
                self.video_bitrate = 4000000  # 4Mbps
                self.keyframe_interval = 20   # More frequent keyframes
            elif quality == "high":
                self.video_bitrate = 2500000  # 2.5Mbps
                self.keyframe_interval = 25
            elif quality == "medium":
                self.video_bitrate = 1500000  # 1.5Mbps
                self.keyframe_interval = 30
            else:  # low
                self.video_bitrate = 1000000  # 1Mbps
                self.keyframe_interval = 40
            
            try:
                logger.info(f"🚀 Starting low-latency WebRTC stream for {self.udid} at {fps}fps")
                
                # Start H.264 video stream process
                if not self._start_h264_stream():
                    return False
                
                self.stream_active = True
                
                # Start frame processing thread
                self.frame_thread = threading.Thread(
                    target=self._process_h264_frames,
                    daemon=True
                )
                self.frame_thread.start()
                
                logger.info(f"✅ Low-latency WebRTC stream started for {self.udid}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to start low-latency WebRTC stream for {self.udid}: {e}")
                import traceback
                logger.error(f"   Traceback: {traceback.format_exc()}")
                return False
    
    def _start_h264_stream(self) -> bool:
        """Start idb video-stream process with optimized settings"""
        try:
            # Create temporary file for H.264 stream
            self.h264_file = tempfile.NamedTemporaryFile(suffix='.h264', delete=False)
            self.h264_file.close()
            
            # Ultra low-latency idb command
            cmd = [
                "idb", "video-stream",
                "--udid", self.udid,
                "--format", "h264",
                "--fps", str(self.target_fps),
                "--compression-quality", "0.8",  # Higher quality for better frames
                self.h264_file.name
            ]
            
            logger.info(f"🎬 Starting idb video-stream: {' '.join(cmd)}")
            
            # Start H.264 capture process
            self.h264_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give it a moment to start and create initial data
            time.sleep(0.5)
            
            if self.h264_process.poll() is not None:
                stderr = self.h264_process.stderr.read().decode()
                logger.error(f"❌ idb video-stream failed to start: {stderr}")
                return False
            
            # Check if file is being written
            if os.path.exists(self.h264_file.name) and os.path.getsize(self.h264_file.name) > 0:
                logger.info(f"✅ idb video-stream started successfully, file: {self.h264_file.name}")
                return True
            else:
                logger.warning(f"⚠️  H.264 file not created yet, waiting...")
                time.sleep(0.5)
                return os.path.exists(self.h264_file.name)
            
        except Exception as e:
            logger.error(f"❌ Error starting H.264 stream: {e}")
            return False
    
    def _process_h264_frames(self):
        """Process H.264 frames from file with minimal latency"""
        logger.info(f"🎬 Starting low-latency H.264 frame processing for {self.udid}")
        
        try:
            last_size = 0
            frame_count = 0
            last_log_time = time.time()
            
            # Wait for initial data
            while self.stream_active and not os.path.exists(self.h264_file.name):
                time.sleep(0.1)
            
            while self.stream_active and self.h264_process and self.h264_process.poll() is None:
                try:
                    if not os.path.exists(self.h264_file.name):
                        time.sleep(0.01)
                        continue
                    
                    current_size = os.path.getsize(self.h264_file.name)
                    
                    # Check if new data is available
                    if current_size > last_size:
                        try:
                            # Try to decode the entire file periodically for frames
                            container = av.open(self.h264_file.name, 'r')
                            
                            if container.streams.video:
                                video_stream = container.streams.video[0]
                                
                                # Seek to near the end for latest frames (low latency)
                                frames_decoded = 0
                                for frame in container.decode(video_stream):
                                    frames_decoded += 1
                                    
                                    # Only keep the most recent frames (skip frames for ultra-low latency)
                                    if frames_decoded % 2 == 0:  # Every 2nd frame for minimum latency
                                        # Clear old frames from queue
                                        while not self.frame_queue.empty():
                                            try:
                                                self.frame_queue.get_nowait()
                                            except Empty:
                                                break
                                        
                                        # Add fresh frame
                                        try:
                                            self.frame_queue.put_nowait(frame)
                                            frame_count += 1
                                        except:
                                            pass  # Queue full
                                        
                                        # Break after adding one frame for low latency
                                        break
                            
                            container.close()
                            last_size = current_size
                            
                        except Exception as decode_error:
                            logger.debug(f"H.264 decode error: {decode_error}")
                            time.sleep(0.01)
                    else:
                        time.sleep(0.01)  # Wait for new data
                    
                    # Periodic logging
                    current_time = time.time()
                    if current_time - last_log_time >= 10.0:
                        logger.info(f"📊 Low-latency H.264 for {self.udid}: {frame_count} frames processed, queue: {self.frame_queue.qsize()}")
                        last_log_time = current_time
                        frame_count = 0
                
                except Exception as e:
                    logger.debug(f"Frame processing error: {e}")
                    time.sleep(0.01)
                    
        except Exception as e:
            logger.error(f"H.264 frame processing error for {self.udid}: {e}")
        finally:
            # Cleanup
            try:
                if hasattr(self, 'h264_file') and os.path.exists(self.h264_file.name):
                    os.unlink(self.h264_file.name)
            except:
                pass
            logger.info(f"🛑 H.264 frame processing stopped for {self.udid}")
    
    async def get_h264_frame(self):
        """Get next H.264 frame with ultra-low latency"""
        try:
            # Very short timeout for minimal latency
            frame = self.frame_queue.get(timeout=0.01)
            return frame
        except Empty:
            return None
    
    def stop_video_stream(self):
        """Stop video streaming and cleanup"""
        logger.info(f"🛑 Stopping low-latency WebRTC stream for {self.udid}")
        
        with self.stream_lock:
            self.stream_active = False
            
            # Stop H.264 process
            if self.h264_process:
                try:
                    self.h264_process.terminate()
                    self.h264_process.wait(timeout=2)
                except:
                    try:
                        self.h264_process.kill()
                    except:
                        pass
                self.h264_process = None
            
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
        """Create new WebRTC peer connection with low-latency settings"""
        if not self.stream_active:
            if not self.start_video_stream("high", self.target_fps):
                raise Exception("Failed to start low-latency WebRTC stream")
        
        connection_id = str(uuid.uuid4())
        
        # WebRTC configuration optimized for low latency
        config = RTCConfiguration(
            iceServers=[],  # Local network only for minimal latency
        )
        pc = RTCPeerConnection(configuration=config)
        
        # Add video track with low-latency settings
        video_track = IDBVideoStreamTrack(self, target_fps=self.target_fps)
        transceiver = pc.addTransceiver(video_track, direction="sendonly")
        
        # Optimize transceiver for low latency
        if transceiver.sender:
            # Set encoding parameters for minimal latency
            encoding_params = {
                "maxBitrate": self.video_bitrate,
                "maxFramerate": self.target_fps,
                "scaleResolutionDownBy": 1,
            }
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():  # noqa: F841
            logger.info(f"🔗 Low-latency WebRTC connection state for {self.udid}: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed"]:
                self.remove_connection(connection_id)
        
        self.peer_connections[connection_id] = pc
        logger.info(f"🤝 Created low-latency WebRTC peer connection: {connection_id} for {self.udid}")
        return connection_id, pc
    
    async def handle_offer(self, pc: RTCPeerConnection, offer_data: Dict) -> Dict:
        """Handle WebRTC offer with low-latency optimizations"""
        logger.info(f"📤 Handling low-latency WebRTC offer for {self.udid}")
        
        await pc.setRemoteDescription(RTCSessionDescription(
            sdp=offer_data["sdp"],
            type=offer_data["type"]
        ))
        
        # Create answer with low-latency settings
        answer = await pc.createAnswer()
        
        # Modify SDP for minimal latency
        sdp_lines = answer.sdp.split('\r\n')
        modified_sdp = []
        
        for line in sdp_lines:
            # Add low-latency optimizations to SDP
            if line.startswith('a=fmtp:'):
                # Add H.264 low-latency parameters
                if 'H264' in line or 'h264' in line:
                    line += ';profile-level-id=42e01f;level-asymmetry-allowed=1;packetization-mode=1'
            elif line.startswith('a=rtcp-fb:'):
                # Add feedback for low latency
                modified_sdp.append(line)
                if 'nack' in line:
                    continue  # Skip duplicate
            modified_sdp.append(line)
        
        # Set modified answer
        modified_answer = RTCSessionDescription(
            sdp='\r\n'.join(modified_sdp),
            type="answer"
        )
        await pc.setLocalDescription(modified_answer)
        
        logger.info(f"📥 Low-latency WebRTC answer created for {self.udid}")
        
        return {
            "type": "answer",
            "sdp": pc.localDescription.sdp
        }
    
    async def handle_ice_candidate(self, pc: RTCPeerConnection, candidate_data: Dict):
        """Handle ICE candidate"""
        logger.debug(f"🧊 Handling ICE candidate for low-latency WebRTC {self.udid}")
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
                logger.info(f"🗑️  Removed low-latency WebRTC connection: {connection_id}")
            except KeyError:
                pass
        
        # Stop stream if no more connections
        if not self.peer_connections:
            self.stop_video_stream()
    
    def set_quality(self, quality: str) -> Dict:
        """Set streaming quality preset (optimized for latency)"""
        valid_qualities = ["low", "medium", "high", "ultra"]
        if quality not in valid_qualities:
            return {"success": False, "error": f"Invalid quality. Must be one of: {valid_qualities}"}
        
        # Restart with new quality settings
        was_active = self.stream_active
        if was_active:
            self.stop_video_stream()
            self.start_video_stream(quality, self.target_fps)
        
        logger.info(f"🎚️  Low-latency quality set to {quality} for {self.udid}")
        return {"success": True, "quality": quality}
    
    def set_fps(self, fps: int) -> Dict:
        """Set target FPS (higher FPS = lower latency)"""
        if fps < 30 or fps > 120:
            return {"success": False, "error": "FPS must be between 30 and 120 for low latency"}
        
        old_fps = self.target_fps
        self.target_fps = fps
        
        # Restart with new FPS
        was_active = self.stream_active
        if was_active:
            self.stop_video_stream()
            self.start_video_stream("high", fps)
        
        logger.info(f"📊 Low-latency FPS changed from {old_fps} to {fps} for {self.udid}")
        return {"success": True, "fps": fps}
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            "stream_active": self.stream_active,
            "connections": len(self.peer_connections),
            "fps": self.target_fps,
            "bitrate": self.video_bitrate,
            "keyframe_interval": self.keyframe_interval,
            "queue_size": self.frame_queue.qsize(),
            "udid": self.udid,
            "type": "low_latency_h264"
        }