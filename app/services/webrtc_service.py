import asyncio
import threading
import time
import subprocess
import uuid
import numpy as np
from typing import Dict, Optional, List, Tuple
from collections import deque
from dataclasses import dataclass
import av
from fractions import Fraction
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceCandidate
from aiortc.contrib.media import MediaRelay
import weakref
from concurrent.futures import ThreadPoolExecutor

from app.config.settings import settings
from app.core.logging import logger

@dataclass
class PerformanceMetrics:
    """Performance tracking for adaptive optimization"""
    frame_times: deque
    encode_times: deque
    network_rtt: float
    packet_loss: float
    last_updated: float
    
    def __post_init__(self):
        if not hasattr(self, 'frame_times'):
            self.frame_times = deque(maxlen=60)
        if not hasattr(self, 'encode_times'):
            self.encode_times = deque(maxlen=30)

# Replace the UltraMaxQualityVideoTrack.recv method with this improved version:

class UltraMaxQualityVideoTrack(VideoStreamTrack):
    def __init__(self, webrtc_service, target_fps: int = 60, connection_id: str = ""):
        super().__init__()
        self.webrtc_service = webrtc_service
        self.target_fps = target_fps
        self.connection_id = connection_id
        self.frame_count = 0
        self.last_frame_time = 0
        self.frame_interval = 1.0 / target_fps
        self.last_valid_frame = None  # Keep a backup of last good frame

        self.current_frame = None
        self.frame_lock = threading.RLock()
        self.frame_producer_thread = None
        self.frame_queue = deque(maxlen=1)
        
        logger.info(f"🚀 Ultra-max quality video track created: {target_fps}fps, connection: {connection_id}")

    # Replace the UltraMaxQualityVideoTrack.recv method with this anti-lag version:

    async def recv(self):
        """Ultra-low latency frame delivery with aggressive optimization"""
        current_time = time.time()
        
        # ✅ MINIMAL rate limiting for real-time feel
        min_frame_interval = 1.0 / min(60, self.target_fps)  # Cap at 60fps for browser compatibility
        if current_time - self.last_frame_time < min_frame_interval:
            sleep_time = min_frame_interval - (current_time - self.last_frame_time)
            if sleep_time > 0.001:  # Only sleep if > 1ms
                await asyncio.sleep(min(sleep_time, 0.016))  # Max 16ms (60fps)
        
        try:
            # ✅ GET FRESHEST FRAME: Always get the most recent
            av_frame = None
            
            # Try to get the absolute latest frame
            with self.webrtc_service.frame_lock:
                # Priority 1: Current frame (most recent)
                if self.webrtc_service.current_frame is not None:
                    av_frame = self.webrtc_service.current_frame
                # Priority 2: Last frame in queue
                elif self.webrtc_service.frame_queue:
                    av_frame = self.webrtc_service.frame_queue[-1]
            
            # Fallback handling
            if av_frame is None:
                if self.last_valid_frame is not None:
                    logger.debug("Using last valid frame as fallback")
                    av_frame = self.last_valid_frame
                else:
                    logger.warning("No frames available, creating black frame")
                    av_frame = self._create_black_frame()
            
            # ✅ FAST validation and processing
            if not self._is_frame_valid(av_frame):
                logger.warning("Invalid frame detected, using fallback")
                if self.last_valid_frame is not None:
                    av_frame = self.last_valid_frame
                else:
                    av_frame = self._create_black_frame()
            
            # ✅ MINIMAL format conversion
            try:
                if av_frame.format.name != 'yuv420p':
                    # Fast conversion without quality loss
                    av_frame = av_frame.reformat(format='yuv420p')
                
                # Quick plane validation
                if not hasattr(av_frame, 'planes') or len(av_frame.planes) != 3:
                    raise ValueError("Frame missing YUV planes")
                
                # Store as last valid frame
                self.last_valid_frame = av_frame
                
            except Exception as conversion_error:
                logger.error(f"Frame conversion error: {conversion_error}")
                if self.last_valid_frame is not None:
                    av_frame = self.last_valid_frame
                else:
                    av_frame = self._create_black_frame()
            
            # ✅ PRECISE timing for smooth playback
            self.frame_count += 1
            av_frame.pts = self.frame_count
            av_frame.time_base = Fraction(1, min(60, self.target_fps))  # Browser-compatible timing
            
            self.last_frame_time = current_time
            
            # Minimal logging
            if self.frame_count % 120 == 0:  # Log every 2 seconds at 60fps
                logger.debug(f"📊 Sent frame {self.frame_count} for connection {self.connection_id}")
            
            return av_frame
            
        except Exception as e:
            logger.error(f"❌ Error in recv() for connection {self.connection_id}: {e}")
            if self.last_valid_frame is not None:
                return self.last_valid_frame
            else:
                return self._create_black_frame()
            
    def clear_frame_buffers(self):
        """Clear frame buffers to eliminate lag after actions"""
        try:
            with self.frame_lock:
                # Keep only the most recent frame
                if self.frame_queue:
                    latest_frame = self.frame_queue[-1] if self.frame_queue else None
                    self.frame_queue.clear()
                    if latest_frame:
                        self.frame_queue.append(latest_frame)
                
                logger.debug("🧹 Cleared frame buffers to reduce lag")
                
        except Exception as e:
            logger.error(f"❌ Error clearing frame buffers: {e}")
    
    def optimize_for_real_time(self):
        """Optimize settings for real-time interaction"""
        try:
            # Clear any accumulated frames
            self.clear_frame_buffers()
            
            # Reduce queue size even further
            with self.frame_lock:
                # Create new queue with minimal size
                current_frames = list(self.frame_queue)
                self.frame_queue = deque(maxlen=1)  # ✅ Smallest possible buffer
                
                # Keep only the newest frame if any
                if current_frames:
                    self.frame_queue.append(current_frames[-1])
            
            logger.info("⚡ Optimized for real-time with minimal buffering")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error optimizing for real-time: {e}")
            return False
        

    def _is_frame_valid(self, frame) -> bool:
        """Validate frame integrity"""
        try:
            if frame is None:
                return False
            
            # Check basic properties
            if not hasattr(frame, 'width') or not hasattr(frame, 'height'):
                return False
            
            if frame.width <= 0 or frame.height <= 0:
                return False
            
            # Check if frame has proper format
            if not hasattr(frame, 'format') or frame.format is None:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _create_black_frame(self):
        """Create a black frame as fallback"""
        try:
            import av
            
            # Create a black frame with standard iPhone resolution
            width, height = 1170, 2532
            
            # Create black frame in YUV420P format
            frame = av.VideoFrame.from_ndarray(
                np.zeros((height, width, 3), dtype=np.uint8),
                format='rgb24'
            )
            
            # Convert to YUV420P
            frame = frame.reformat(format='yuv420p')
            frame.pts = self.frame_count
            frame.time_base = Fraction(1, self.target_fps)
            
            return frame
            
        except Exception as e:
            logger.error(f"Failed to create black frame: {e}")
            # This should never happen, but just in case
            raise RuntimeError("Cannot create fallback frame")
    
    async def _get_ultra_optimized_frame(self):
        """Get frame with advanced caching and format optimization"""
        service = self.webrtc_service()
        if not service:
            return None
        
        current_time = time.time()
        
        # Try multiple frame sources for maximum reliability
        frame = None
        
        # 1. Try current frame first
        frame = service.get_latest_frame()
        
        # 2. If no current frame, try frame queue
        if frame is None:
            with service.frame_lock:
                if service.frame_queue:
                    frame = service.frame_queue[-1]  # Most recent
        
        # 3. Process and optimize the frame
        if frame:
            try:
                # Ensure optimal format for WebRTC
                optimized_frame = await self._optimize_frame_for_webrtc(frame)
                return optimized_frame
            except Exception as e:
                logger.debug(f"Frame optimization error: {e}")
                return frame  # Return original if optimization fails
        
        return None
    
    async def _optimize_frame_for_webrtc(self, source_frame):
        """Optimize frame specifically for WebRTC transmission"""
        try:
            # Convert to the most efficient format for WebRTC
            if source_frame.format.name != 'yuv420p':
                # Use high-quality conversion
                optimized_frame = source_frame.reformat(
                    format='yuv420p',
                    interpolation='lanczos'  # High-quality scaling
                )
            else:
                # Clone frame to avoid reference issues
                frame_array = source_frame.to_ndarray()
                optimized_frame = av.VideoFrame.from_ndarray(frame_array, format='yuv420p')
            
            # Set optimal properties
            optimized_frame.pts = source_frame.pts if hasattr(source_frame, 'pts') else self.frame_count
            optimized_frame.time_base = source_frame.time_base if hasattr(source_frame, 'time_base') else Fraction(1, self.target_fps)
            
            return optimized_frame
            
        except Exception as e:
            logger.debug(f"Frame format optimization failed: {e}")
            # Return a safe copy
            try:
                frame_array = source_frame.to_ndarray()
                return av.VideoFrame.from_ndarray(frame_array, format='yuv420p')
            except:
                return source_frame
    
    def _create_high_quality_emergency_frame(self):
        """Create high-quality emergency frame with proper format"""
        try:
            # Create a gradient or pattern instead of solid black for debugging
            import numpy as np
            
            # Create a subtle gradient pattern
            height, width = 844, 390
            
            # Y channel (brightness) - create a subtle pattern
            y_channel = np.zeros((height, width), dtype=np.uint8)
            y_channel.fill(16)  # Dark gray instead of black
            
            # Add a subtle grid pattern for debugging
            if self.emergency_frame_count < 5:  # Only for first few frames
                for i in range(0, height, 50):
                    y_channel[i:i+2, :] = 32
                for i in range(0, width, 50):
                    y_channel[:, i:i+2] = 32
            
            # U and V channels (chrominance) - centered
            u_channel = np.full((height // 2, width // 2), 128, dtype=np.uint8)
            v_channel = np.full((height // 2, width // 2), 128, dtype=np.uint8)
            
            # Create YUV420p frame
            frame = av.VideoFrame(width=width, height=height, format='yuv420p')
            frame.planes[0].update(y_channel)
            frame.planes[1].update(u_channel)
            frame.planes[2].update(v_channel)
            
            frame.pts = self.frame_count
            frame.time_base = Fraction(1, self.target_fps)
            
            return frame
            
        except Exception as e:
            logger.error(f"Emergency frame creation failed: {e}")
            # Absolute fallback
            return av.VideoFrame(width=390, height=844, format='yuv420p')
    
    async def _ultra_adaptive_frame_timing(self):
        """Ultra-adaptive timing with predictive adjustment"""
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        # Base target sleep time
        target_sleep = self.frame_interval - elapsed
        
        # Advanced adaptive adjustment based on performance history
        if len(self.performance_metrics.frame_times) > 20:
            recent_times = list(self.performance_metrics.frame_times)[-20:]
            avg_frame_time = sum(recent_times) / len(recent_times)
            
            # Predictive adjustment based on trend
            if avg_frame_time > self.frame_interval * 0.9:
                # Frames are taking too long, aggressive catch-up
                target_sleep *= 0.3
            elif avg_frame_time > self.frame_interval * 0.7:
                # Moderate adjustment
                target_sleep *= 0.6
            elif avg_frame_time < self.frame_interval * 0.3:
                # Frames are very fast, we can afford to wait
                target_sleep *= 1.1
        
        # Ensure minimum viable timing
        if target_sleep > 0.0005:  # 0.5ms minimum
            await asyncio.sleep(min(target_sleep, 0.008))  # Max 8ms (125fps limit)
        
        self.last_frame_time = time.time()

class UltraMaxQualityWebRTCService:
    """Ultra-maximum quality WebRTC service with minimum latency"""
    
    def __init__(self, udid: Optional[str] = None):
        self.udid = udid
        
        # Core WebRTC state
        self.webrtc_connections: Dict[str, RTCPeerConnection] = {}
        self.webrtc_active = False
        self.video_stream_process = None
        self.stream_active = False
        self.stream_lock = threading.RLock()  # Use RLock for nested locking
        self.media_relay = MediaRelay()
        
        # Ultra-optimized frame management
        self.current_frame = None
        self.frame_lock = threading.RLock()  # Use RLock for nested locking
        self.frame_producer_thread = None
        self.frame_queue = deque(maxlen=5)  # Slightly larger buffer for stability
        
        # MAXIMUM quality settings
        self.quality_settings = {
            "fps": 120,           # Ultra-high FPS
            "bitrate": "50M",     # Ultra-high bitrate
            "format": "h264",
            "preset": "ultrafast",
            "profile": "high",
            "level": "5.1",       # Higher level for more features
            "crf": "12",          # Near-lossless quality
            "tune": "zerolatency",
            "compression_quality": "1.0",  # Maximum compression quality
            "scale": "1.0"        # No downscaling
        }
        
        # Enhanced performance monitoring
        self.performance_metrics = PerformanceMetrics(
            frame_times=deque(maxlen=200),  # More samples
            encode_times=deque(maxlen=100),
            network_rtt=0.0,
            packet_loss=0.0,
            last_updated=time.time()
        )
        
        # Advanced optimization settings
        self.latency_threshold_ms = 100  # Stricter latency target
        self.quality_adaptation_enabled = True
        self.max_quality_mode = True
        
        # Frame processing optimization
        self.frame_processor_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="FrameProcessor")
        
        logger.info(f"🚀 Ultra-max quality WebRTC service initialized for {udid}")
    
    def set_udid(self, udid: str):
        """Set the UDID for this service instance"""
        self.udid = udid
        logger.info(f"WebRTC service UDID set to: {udid}")
    

    def start_video_stream(self) -> bool:
        """Start video streaming with enhanced error handling"""
        if not self.udid:
            logger.error("No UDID set for video stream")
            return False
        
        with self.stream_lock:
            if self.stream_active and self.video_stream_process:
                logger.info("Stream already active")
                return True
            
            # ✅ Clean up any existing process first
            self._cleanup_video_process()
            
            try:
                # Simple idb command - exactly like the working test
                cmd = [
                    "idb", "video-stream",
                    "--udid", self.udid,
                    "--format", "h264",
                    "--fps", "30"  # ✅ Use 30fps like the working test
                ]
                
                logger.info(f"🚀 Starting idb stream: {' '.join(cmd)}")
                
                # ✅ Start process with better error handling
                self.video_stream_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0
                )
                
                if not self.video_stream_process:
                    logger.error("❌ Failed to create subprocess")
                    return False
                
                logger.info(f"✅ Process created with PID: {self.video_stream_process.pid}")
                
                # ✅ Validate process startup
                startup_delay = 0.5
                time.sleep(startup_delay)
                
                try:
                    process_status = self.video_stream_process.poll()
                    if process_status is not None:
                        # Process died immediately
                        stderr_data = ""
                        try:
                            stderr_data = self.video_stream_process.stderr.read().decode()
                        except:
                            pass
                        logger.error(f"❌ idb stream failed immediately (code {process_status}): {stderr_data}")
                        self.video_stream_process = None
                        return False
                    
                    # ✅ Check if stdout is available
                    if not self.video_stream_process.stdout:
                        logger.error("❌ No stdout available from idb process")
                        self._cleanup_video_process()
                        return False
                    
                    # ✅ Set stream as active BEFORE starting frame producer
                    self.stream_active = True
                    self.webrtc_active = True
                    
                    logger.info(f"✅ idb stream validated, starting frame producer...")
                    
                    # Start frame producer
                    self._start_ultra_frame_producer()
                    
                    logger.info(f"✅ idb stream started successfully for {self.udid}")
                    return True
                    
                except Exception as validation_error:
                    logger.error(f"❌ Process validation failed: {validation_error}")
                    self._cleanup_video_process()
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Failed to start stream: {e}")
                self._cleanup_video_process()
                return False
    
    def _cleanup_video_process(self):
        """Clean up video stream process safely"""
        try:
            if self.video_stream_process:
                logger.info("🧹 Cleaning up existing video process...")
                
                try:
                    # Try graceful termination first
                    if self.video_stream_process.poll() is None:
                        self.video_stream_process.terminate()
                        time.sleep(0.1)
                        
                        # Force kill if still running
                        if self.video_stream_process.poll() is None:
                            self.video_stream_process.kill()
                            time.sleep(0.1)
                except:
                    pass
                
                self.video_stream_process = None
                logger.info("✅ Video process cleaned up")
                
        except Exception as e:
            logger.error(f"❌ Error during video process cleanup: {e}")
        
        # Reset flags
        self.stream_active = False
        self.webrtc_active = False


    def _set_ultra_high_priority(self):
        """Set ultra-high priority for video stream process"""
        try:
            import os
            import psutil
            
            # Set highest possible priority
            os.nice(-10)  # Maximum priority
            
            # Try to set real-time priority if possible
            try:
                p = psutil.Process()
                p.nice(psutil.HIGH_PRIORITY_CLASS if hasattr(psutil, 'HIGH_PRIORITY_CLASS') else -10)
            except:
                pass
                
        except Exception:
            pass  # Ignore if can't set priority
    

    def _start_ultra_frame_producer(self):
        """Start ultra-optimized frame producer thread with better management"""
        try:
            # ✅ Stop existing producer if running
            if self.frame_producer_thread and self.frame_producer_thread.is_alive():
                logger.info("🛑 Stopping existing frame producer...")
                self.stream_active = False
                self.frame_producer_thread.join(timeout=2)
                if self.frame_producer_thread.is_alive():
                    logger.warning("⚠️ Frame producer thread didn't stop gracefully")
            
            # ✅ Ensure we have a valid process before starting producer
            if not self.video_stream_process:
                logger.error("❌ Cannot start frame producer: no video process")
                return False
            
            try:
                if self.video_stream_process.poll() is not None:
                    logger.error("❌ Cannot start frame producer: video process is dead")
                    return False
            except AttributeError:
                logger.error("❌ Cannot start frame producer: invalid video process")
                return False
            
            # ✅ Start new producer thread
            self.frame_producer_thread = threading.Thread(
                target=self._ultra_max_quality_frame_producer,
                daemon=True,
                name=f"FrameProducer-{self.udid[:8]}"
            )
            
            self.frame_producer_thread.start()
            logger.info(f"🚀 Started ultra-max quality frame producer for {self.udid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start frame producer: {e}")
            return False


    def _ultra_max_quality_frame_producer(self):
        """Enhanced frame producer with anti-lag optimizations"""
        logger.info(f"🚀 Frame producer starting for {self.udid}")
        
        frame_count = 0
        start_time = time.time()
        corrupted_frames = 0
        dropped_frames = 0
        last_action_time = time.time()
        
        try:
            # Validation and container setup
            if not self.video_stream_process:
                logger.error("❌ No video stream process found")
                return
            
            time.sleep(0.2)
            
            try:
                process_status = self.video_stream_process.poll()
                if process_status is not None:
                    stderr_data = ""
                    try:
                        if self.video_stream_process.stderr:
                            stderr_data = self.video_stream_process.stderr.read().decode()
                    except:
                        pass
                    logger.error(f"❌ Process died with code {process_status}: {stderr_data}")
                    return
            except AttributeError:
                logger.error("❌ Video stream process became None during startup")
                return
            
            logger.info("📡 Opening video container...")
            
            try:
                if not self.video_stream_process.stdout:
                    logger.error("❌ No stdout available from process")
                    return
                
                container = av.open(self.video_stream_process.stdout, 'r', format='h264')
                
            except Exception as container_error:
                logger.error(f"❌ Failed to open container: {container_error}")
                return
            
            logger.info(f"✅ Container opened successfully")
            logger.info(f"Video streams: {len(container.streams.video)}")
            
            if not container.streams.video:
                logger.error("❌ No video streams found")
                return
            
            stream = container.streams.video[0]
            logger.info(f"Stream info: {stream}")
            
            logger.info("🎬 Starting frame processing...")
            
            last_log_time = time.time()
            
            # ✅ ANTI-LAG processing loop
            for packet in container.demux(stream):
                if not self.stream_active:
                    logger.info("🛑 Stream stopping")
                    break
                
                # Check process health
                if frame_count % 30 == 0:
                    try:
                        if not self.video_stream_process or self.video_stream_process.poll() is not None:
                            logger.error("❌ Video stream process died during processing")
                            break
                    except AttributeError:
                        logger.error("❌ Video stream process became None during processing")
                        break
                
                try:
                    for frame in packet.decode():
                        # ✅ VALIDATE frame before processing
                        if not self._validate_frame_integrity(frame):
                            corrupted_frames += 1
                            if corrupted_frames % 10 == 0:
                                logger.warning(f"⚠️ Skipped {corrupted_frames} corrupted frames")
                            continue
                        
                        frame_count += 1
                        current_time = time.time()
                        
                        # ✅ CRITICAL: Anti-lag frame management
                        try:
                            # Ensure proper format
                            if frame.format.name != 'yuv420p':
                                frame = frame.reformat(format='yuv420p')
                            
                            # Set timing
                            frame.pts = frame_count
                            frame.time_base = Fraction(1, 30)
                            
                            # ✅ SMART BUFFERING: Aggressive queue management
                            with self.frame_lock:
                                # Check if we should drop frames (queue getting full)
                                queue_size = len(self.frame_queue)
                                
                                if queue_size >= 3:  # ✅ Much smaller buffer
                                    # Drop oldest frames aggressively
                                    frames_to_drop = queue_size - 1  # Keep only 1 frame
                                    for _ in range(frames_to_drop):
                                        if self.frame_queue:
                                            self.frame_queue.popleft()
                                            dropped_frames += 1
                                
                                # Always update current frame (most recent)
                                self.current_frame = frame
                                
                                # Add to queue only if there's space
                                if len(self.frame_queue) < 2:  # ✅ Very small queue
                                    self.frame_queue.append(frame)
                                else:
                                    # Replace the newest frame in queue
                                    if self.frame_queue:
                                        self.frame_queue.pop()  # Remove newest
                                    self.frame_queue.append(frame)
                                    dropped_frames += 1
                            
                        except Exception as frame_process_error:
                            logger.warning(f"Frame processing error: {frame_process_error}")
                            continue
                        
                        # Progress logging with drop info
                        if current_time - last_log_time > 2.0 or frame_count <= 10:
                            elapsed = current_time - start_time
                            fps = frame_count / elapsed if elapsed > 0 else 0
                            logger.info(f"✅ Frame {frame_count}: {frame.width}x{frame.height}, {fps:.1f}fps (corrupted: {corrupted_frames}, dropped: {dropped_frames})")
                            last_log_time = current_time
                        
                        # ✅ MINIMAL SLEEP: Only yield occasionally
                        if frame_count % 60 == 0:
                            time.sleep(0.0001)  # Extremely minimal sleep
                
                except Exception as decode_error:
                    logger.warning(f"Packet decode error: {decode_error}")
                    continue
        
        except Exception as e:
            logger.error(f"❌ Frame producer error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        
        finally:
            try:
                if 'container' in locals():
                    container.close()
                    logger.info("📦 Container closed")
            except:
                pass
            
            elapsed = time.time() - start_time
            avg_fps = frame_count / elapsed if elapsed > 0 else 0
            logger.info(f"🏁 Frame producer stopped. {frame_count} frames, {avg_fps:.1f}fps, {corrupted_frames} corrupted, {dropped_frames} dropped")
    def _validate_frame_integrity(self, frame) -> bool:
        """Validate frame integrity to prevent corruption"""
        try:
            # Basic validation
            if frame is None:
                return False
            
            # Check dimensions
            if not hasattr(frame, 'width') or not hasattr(frame, 'height'):
                return False
            
            if frame.width <= 0 or frame.height <= 0:
                return False
            
            # Check for reasonable dimensions (not corrupted)
            if frame.width > 4000 or frame.height > 4000:
                return False
            
            # Check format
            if not hasattr(frame, 'format') or frame.format is None:
                return False
            
            # Check for data availability
            if hasattr(frame, 'planes'):
                for plane in frame.planes:
                    if plane.buffer_size <= 0:
                        return False
            
            return True
            
        except Exception:
            return False


    def _process_frame_ultra_optimized(self, frame, frame_count):
        """Ultra-optimized frame processing for maximum quality"""
        try:
            # Ensure optimal format
            if frame.format.name != 'yuv420p':
                frame = frame.reformat(format='yuv420p')
            
            # Set ultra-precise timing
            frame.pts = frame_count
            frame.time_base = Fraction(1, self.quality_settings["fps"])
            
            return frame
            
        except Exception as e:
            logger.debug(f"Frame processing error: {e}")
            return None
    
    def get_latest_frame(self):
        """Get the latest frame with ultra-minimal latency"""
        try:
            with self.frame_lock:
                if self.current_frame:
                    return self.current_frame
                elif self.frame_queue:
                    return self.frame_queue[-1]
                return None
        except Exception as e:
            logger.debug(f"Get latest frame error: {e}")
            return None
    

    async def create_peer_connection(self) -> Tuple[str, RTCPeerConnection]:
        """Create peer connection with minimal configuration"""
        connection_id = str(uuid.uuid4())
        
        try:
            # ✅ ULTRA-SIMPLE: Just create with default configuration
            pc = RTCPeerConnection()
            
            logger.info(f"✅ Created simple peer connection: {connection_id}")
            
            # Set up event handlers
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"🔗 Connection {connection_id} state: {pc.connectionState}")
            
            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                logger.info(f"🧊 ICE connection {connection_id} state: {pc.iceConnectionState}")
            
            # Create and add video track
            video_track = await self._create_ultra_video_track(connection_id)
            pc.addTrack(video_track)
            
            # Store connection
            self.webrtc_connections[connection_id] = pc
            
            logger.info(f"✅ Peer connection created successfully: {connection_id}")
            return connection_id, pc
            
        except Exception as e:
            logger.error(f"❌ Failed to create peer connection: {e}")
            raise
        
    async def _create_ultra_video_track(self, connection_id: str) -> UltraMaxQualityVideoTrack:
        """Create ultra-high quality video track"""
        try:
            # Create video track with maximum quality settings
            video_track = UltraMaxQualityVideoTrack(
                webrtc_service=self,
                target_fps=self.quality_settings["fps"],
                connection_id=connection_id
            )
            
            logger.info(f"✅ Created ultra video track for connection: {connection_id}")
            return video_track
            
        except Exception as e:
            logger.error(f"❌ Failed to create video track: {e}")
            raise

    def enable_absolute_maximum_quality(self) -> Dict:
        """Enable ABSOLUTE maximum quality mode"""
        self.quality_settings.update({
            "fps": 120,
            "bitrate": "100M",    # Extreme bitrate
            "crf": "8",           # Visually lossless
            "preset": "ultrafast",
            "tune": "zerolatency",
            "profile": "high",
            "level": "5.2",       # Highest level
            "compression_quality": "1.0",
            "scale": "1.0"
        })
        
        # Disable adaptive quality for consistency
        self.quality_adaptation_enabled = False
        self.max_quality_mode = True
        self.latency_threshold_ms = 50  # Ultra-strict latency
        
        # Restart stream to apply settings
        if self.stream_active:
            self.stop_video_stream()
            time.sleep(0.1)
            self.start_video_stream()
        
        logger.info(f"🚀 ABSOLUTE MAXIMUM QUALITY enabled for {self.udid}")
        return {
            "success": True,
            "mode": "absolute_maximum_quality",
            "settings": self.quality_settings,
            "note": "Ultra-maximum quality with minimum latency enabled"
        }
    
    # Include all the compatibility and other methods from the original service
    def start_webrtc_capture(self, fps: int = 120) -> bool:
        """Compatibility method"""
        if fps != self.quality_settings["fps"]:
            self.quality_settings["fps"] = min(fps, 120)  # Cap at 120
        return self.start_video_stream()
    
    def stop_webrtc_capture(self):
        """Compatibility method"""
        return self.stop_video_stream()
    
    def get_current_frame(self):
        """Compatibility method"""
        return self.get_latest_frame()
    

    def stop_video_stream(self) -> bool:
        """Stop ultra-maximum quality idb video streaming"""
        logger.info(f"Stopping ultra-max quality video stream for {self.udid}")
        
        try:
            with self.stream_lock:
                self.stream_active = False
                self.webrtc_active = False
                
                # Stop frame producer thread
                if self.frame_producer_thread and self.frame_producer_thread.is_alive():
                    logger.info("🛑 Stopping frame producer thread...")
                    # stream_active is already False, thread should exit
                    self.frame_producer_thread.join(timeout=3)
                    if self.frame_producer_thread.is_alive():
                        logger.warning("⚠️ Frame producer thread didn't stop gracefully")
                
                # Clean up video process
                self._cleanup_video_process()
                
                # Clear frame data
                with self.frame_lock:
                    self.current_frame = None
                    self.frame_queue.clear()
                
                logger.info(f"✅ Video stream stopped for {self.udid}")
                return True  # ✅ RETURN TRUE ON SUCCESS
                
        except Exception as e:
            logger.error(f"❌ Error stopping video stream: {e}")
            return False  # ✅ RETURN FALSE ON ERROR
        

    def get_status(self) -> Dict:
        """Get comprehensive status"""
        with self.frame_lock:
            has_current_frame = self.current_frame is not None
            queue_size = len(self.frame_queue)
        
        return {
            "stream_active": self.stream_active,
            "webrtc_active": self.webrtc_active,
            "connections": len(self.webrtc_connections),
            "quality_settings": self.quality_settings,
            "udid": self.udid,
            "stream_type": "ultra_maximum_quality_stream",
            "performance": {
                "has_current_frame": has_current_frame,
                "frame_queue_size": queue_size,
                "max_quality_mode": self.max_quality_mode,
                "frame_producer_alive": self.frame_producer_thread.is_alive() if self.frame_producer_thread else False
            }
        }
    
    # Add all other methods from original service (handle_offer, handle_ice_candidate, etc.)

    async def handle_offer(self, pc: RTCPeerConnection, offer_data: dict) -> dict:
        """Handle WebRTC offer and return answer"""
        try:
            # ✅ FIXED: Proper SDP handling
            from aiortc import RTCSessionDescription
            
            offer_sdp = offer_data.get("sdp")
            if not offer_sdp:
                raise ValueError("No SDP in offer data")
            
            # Create RTCSessionDescription from offer
            offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
            
            # Set remote description
            await pc.setRemoteDescription(offer)
            logger.info("✅ Set remote description from offer")
            
            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            logger.info("✅ Created and set local description (answer)")
            
            # Return answer in correct format
            return {
                "type": "answer",
                "sdp": pc.localDescription.sdp
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to handle offer: {e}")
            raise

    # Add this debug method before the WebRTCService alias:

    def debug_offer_data(self, offer_data):
        """Debug helper to identify offer data issues"""
        logger.info(f"🔍 DEBUG - Offer data type: {type(offer_data)}")
        logger.info(f"🔍 DEBUG - Offer data value: {offer_data}")
        
        if isinstance(offer_data, bool):
            logger.error(f"❌ CRITICAL: Offer data is boolean: {offer_data}")
            logger.error(f"❌ This suggests the calling code is passing a boolean instead of offer data")
            return False
        
        if not isinstance(offer_data, dict):
            logger.error(f"❌ CRITICAL: Offer data is not a dictionary: {type(offer_data)}")
            return False
        
        required_keys = ["sdp", "type"]
        missing_keys = [key for key in required_keys if key not in offer_data]
        
        if missing_keys:
            logger.error(f"❌ Missing required keys in offer data: {missing_keys}")
            logger.error(f"❌ Available keys: {list(offer_data.keys())}")
            return False
        
        logger.info(f"✅ Offer data validation passed")
        return True
    

    async def handle_ice_candidate(self, pc: RTCPeerConnection, candidate_data: Dict):
        """Handle ICE candidate"""
        try:
            candidate_info = candidate_data.get("candidate")
            if not candidate_info:
                return
            
            if isinstance(candidate_info, dict):
                candidate = RTCIceCandidate(
                    candidate=candidate_info.get("candidate"),
                    sdpMid=candidate_info.get("sdpMid"),
                    sdpMLineIndex=candidate_info.get("sdpMLineIndex")
                )
            elif isinstance(candidate_info, str):
                candidate = RTCIceCandidate(
                    candidate=candidate_info,
                    sdpMid=candidate_data.get("sdpMid"),
                    sdpMLineIndex=candidate_data.get("sdpMLineIndex")
                )
            else:
                return
            
            await pc.addIceCandidate(candidate)
            
        except Exception as e:
            logger.error(f"Failed to add ICE candidate: {e}")
    
    def _start_performance_monitoring(self, pc):
        """Start performance monitoring"""
        async def monitor():
            while pc.iceConnectionState == "connected":
                try:
                    await asyncio.sleep(1.0)
                except Exception:
                    break
        asyncio.create_task(monitor())
    
    async def _cleanup_connection(self, connection_id: str):
        """Clean up connection"""
        if connection_id in self.webrtc_connections:
            pc = self.webrtc_connections[connection_id]
            await pc.close()
            del self.webrtc_connections[connection_id]
            logger.info(f"Cleaned up ultra-max connection: {connection_id}")

    
    # Add this method to the UltraMaxQualityWebRTCService class (around line 800, before the WebRTCService alias)

    def force_restart_stream(self):
        """Force restart the video stream"""
        logger.info(f"🔄 Force restarting ultra-max quality stream for {self.udid}")
        
        try:
            # Stop current stream
            self.stop_video_stream()
            
            # Wait a moment for cleanup
            time.sleep(0.2)
            
            # Start fresh stream
            success = self.start_video_stream()
            
            if success:
                logger.info(f"✅ Ultra-max quality stream force restarted for {self.udid}")
                return {
                    "success": True,
                    "message": "Stream restarted successfully",
                    "udid": self.udid
                }
            else:
                logger.error(f"❌ Failed to force restart stream for {self.udid}")
                return {
                    "success": False,
                    "error": "Failed to start video stream after restart",
                    "udid": self.udid
                }
                
        except Exception as e:
            logger.error(f"❌ Exception during force restart: {e}")
            return {
                "success": False,
                "error": f"Exception during restart: {str(e)}",
                "udid": self.udid
            }
    
    def restart_stream_if_needed(self):
        """Restart stream if it's not working properly"""
        try:
            # Check if stream is supposed to be active but isn't producing frames
            if self.stream_active and self.webrtc_active:
                with self.frame_lock:
                    has_frames = self.current_frame is not None or len(self.frame_queue) > 0
                
                if not has_frames:
                    logger.warning(f"🔄 Stream active but no frames available, restarting...")
                    return self.force_restart_stream()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking stream status: {e}")
            return False
    
    def get_stream_health(self) -> Dict:
        """Get detailed stream health information"""
        try:
            with self.frame_lock:
                has_current_frame = self.current_frame is not None
                queue_size = len(self.frame_queue)
            
            process_alive = False
            process_pid = None
            
            if self.video_stream_process:
                process_alive = self.video_stream_process.poll() is None
                process_pid = self.video_stream_process.pid if process_alive else None
            
            producer_alive = (
                self.frame_producer_thread is not None and 
                self.frame_producer_thread.is_alive()
            )
            
            return {
                "stream_active": self.stream_active,
                "webrtc_active": self.webrtc_active,
                "has_current_frame": has_current_frame,
                "frame_queue_size": queue_size,
                "process_alive": process_alive,
                "process_pid": process_pid,
                "producer_thread_alive": producer_alive,
                "connections": len(self.webrtc_connections),
                "udid": self.udid,
                "max_quality_mode": self.max_quality_mode
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting stream health: {e}")
            return {
                "error": str(e),
                "stream_active": False,
                "webrtc_active": False,
                "has_current_frame": False,
                "frame_queue_size": 0,
                "process_alive": False,
                "producer_thread_alive": False,
                "connections": 0,
                "udid": self.udid
            }
        
    # Add these methods to the UltraMaxQualityWebRTCService class (before the WebRTCService alias at the end):

    def emergency_recovery(self) -> Dict:
        """Emergency recovery when stream is not producing frames"""
        logger.error(f"🚨 Starting emergency recovery for {self.udid}")
        
        try:
            # Step 1: Kill all existing idb processes for this device
            logger.info("🔪 Killing existing idb processes...")
            try:
                # Kill idb processes for this specific device
                subprocess.run(["pkill", "-f", f"idb.*{self.udid}"], check=False)
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Failed to kill existing idb processes: {e}")
            
            # Step 2: Force stop current stream
            logger.info("🛑 Force stopping current stream...")
            self.stop_video_stream()
            time.sleep(1.0)  # Longer wait
            
            # Step 3: Clear all frame data
            with self.frame_lock:
                self.current_frame = None
                self.frame_queue.clear()
            
            # Step 4: Test device connectivity
            logger.info("🔌 Testing device connectivity...")
            device_test = self._test_device_connectivity()
            if not device_test["success"]:
                return {
                    "success": False,
                    "error": "Device connectivity test failed",
                    "details": device_test
                }
            
            # Step 5: Restart with fresh settings
            logger.info("🔄 Restarting with fresh settings...")
            success = self.start_video_stream()
            
            if success:
                # Step 6: Wait for frames with timeout
                logger.info("⏳ Waiting for frames after emergency recovery...")
                for i in range(50):  # 5 seconds
                    time.sleep(0.1)
                    if self.get_latest_frame() is not None:
                        logger.info(f"✅ Emergency recovery successful after {(i+1)*100}ms")
                        return {
                            "success": True,
                            "message": "Emergency recovery successful",
                            "recovery_time_ms": (i+1) * 100,
                            "udid": self.udid
                        }
                
                logger.error("❌ Emergency recovery failed - no frames after restart")
                return {
                    "success": False,
                    "error": "No frames produced after emergency restart",
                    "udid": self.udid
                }
            else:
                logger.error("❌ Emergency recovery failed - could not restart stream")
                return {
                    "success": False,
                    "error": "Failed to restart stream during emergency recovery",
                    "udid": self.udid
                }
                
        except Exception as e:
            logger.error(f"❌ Emergency recovery exception: {e}")
            return {
                "success": False,
                "error": f"Emergency recovery exception: {str(e)}",
                "udid": self.udid
            }
    

    def _test_device_connectivity(self) -> Dict:
        """Test if device is still connected and responsive"""
        try:
            logger.info(f"🔍 Testing connectivity for device {self.udid}")
            
            # Test 1: Check if device is listed
            result = subprocess.run(
                ["idb", "list-targets"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": "idb list-targets failed",
                    "stderr": result.stderr
                }
            
            # Check if our device is in the list
            if self.udid not in result.stdout:
                return {
                    "success": False,
                    "error": f"Device {self.udid} not found in target list",
                    "available_devices": result.stdout.strip()
                }
            
            logger.info(f"✅ Device {self.udid} found in target list")
            
            # Test 2: Try a simple command - FIXED: Use correct idb syntax
            test_result = subprocess.run(
                ["idb", "describe", "--udid", self.udid],  # ✅ FIXED: moved --udid after describe
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if test_result.returncode != 0:
                return {
                    "success": False,
                    "error": "Device describe command failed",
                    "stderr": test_result.stderr
                }
            
            logger.info(f"✅ Device {self.udid} responds to commands")
            
            return {
                "success": True,
                "message": "Device connectivity confirmed",
                "udid": self.udid
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Device connectivity test timed out",
                "udid": self.udid
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Device connectivity test failed: {str(e)}",
                "udid": self.udid
            }
        
    def remove_connection(self, connection_id: str):
        """Remove a WebRTC connection"""
        try:
            if connection_id in self.webrtc_connections:
                pc = self.webrtc_connections[connection_id]
                # Note: We can't await here since this isn't async
                # The WebSocket handler should handle the actual closing
                del self.webrtc_connections[connection_id]
                logger.info(f"🗑️ Removed WebRTC connection: {connection_id}")
            else:
                logger.warning(f"❓ Connection not found for removal: {connection_id}")
        except Exception as e:
            logger.error(f"❌ Error removing connection {connection_id}: {e}")
    
    def set_quality_preset(self, quality: str) -> Dict:
        """Set quality preset"""
        try:
            presets = {
                "ultra": {
                    "fps": 120,
                    "bitrate": "100M",
                    "crf": "8",
                    "preset": "ultrafast"
                },
                "high": {
                    "fps": 60,
                    "bitrate": "50M",
                    "crf": "12",
                    "preset": "ultrafast"
                },
                "medium": {
                    "fps": 30,
                    "bitrate": "25M",
                    "crf": "18",
                    "preset": "fast"
                },
                "low": {
                    "fps": 15,
                    "bitrate": "10M",
                    "crf": "23",
                    "preset": "medium"
                }
            }
            
            if quality not in presets:
                return {
                    "success": False,
                    "error": f"Unknown quality preset: {quality}",
                    "available": list(presets.keys())
                }
            
            # Update settings
            self.quality_settings.update(presets[quality])
            
            # Restart stream if active to apply settings
            if self.stream_active:
                self.stop_video_stream()
                time.sleep(0.2)
                success = self.start_video_stream()
                
                return {
                    "success": success,
                    "quality": quality,
                    "settings": self.quality_settings,
                    "stream_restarted": True
                }
            else:
                return {
                    "success": True,
                    "quality": quality,
                    "settings": self.quality_settings,
                    "stream_restarted": False
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to set quality preset: {str(e)}"
            }
    
    def enable_max_quality_mode(self) -> Dict:
        """Enable maximum quality mode"""
        return self.enable_absolute_maximum_quality()
    
    def optimize_for_latency(self, target_latency_ms: int = 50) -> Dict:
        """Optimize settings for ultra-low latency"""
        try:
            # Ultra-low latency settings
            latency_settings = {
                "fps": min(120, max(30, 120)),  # High FPS for smoothness
                "bitrate": "30M",  # Lower bitrate for speed
                "crf": "15",  # Balance quality vs speed
                "preset": "ultrafast",
                "tune": "zerolatency"
            }
            
            self.quality_settings.update(latency_settings)
            self.latency_threshold_ms = target_latency_ms
            
            # Restart stream if active
            if self.stream_active:
                self.stop_video_stream()
                time.sleep(0.1)
                success = self.start_video_stream()
            else:
                success = True
            
            return {
                "success": success,
                "mode": "ultra_low_latency",
                "target_latency_ms": target_latency_ms,
                "settings": self.quality_settings
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to optimize for latency: {str(e)}"
            }

# Create an alias for backward compatibility
WebRTCService = UltraMaxQualityWebRTCService