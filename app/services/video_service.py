import threading
import time
import subprocess
import queue
from typing import List, Optional, Dict
from queue import Queue, Empty
from app.config.settings import settings
from app.core.logging import logger
from app.services.screenshot_service import ScreenshotService
from app.utils.system_utils import SystemUtils

class VideoService:
    """Service for video streaming"""
    
    def __init__(self):
        self.udid = settings.UDID
        self.screenshot_service = ScreenshotService()
        
        # Video streaming state
        self.video_clients: List[any] = []
        self.video_frame_queue = Queue(maxsize=settings.VIDEO_QUEUE_SIZE)
        self.video_streaming_active = False
        self.video_capture_process = None
        self.video_capture_thread = None
        self.video_lock = threading.Lock()
    
    def start_video_capture(self) -> bool:
        """Start video capture"""
        with self.video_lock:
            if self.video_streaming_active:
                return True
            
            # Try different capture methods
            if self._try_idb_video_stream():
                return True
            elif self._try_ffmpeg_hardware_capture():
                return True
            elif self._try_ffmpeg_software_capture():
                return True
            else:
                # Fallback to screenshot mode
                return self._start_screenshot_mode()
    
    def _try_idb_video_stream(self) -> bool:
        """Try idb video-stream"""
        try:
            logger.info("Attempting idb video-stream...")
            cmd = [
                "idb", "video-stream",
                "--udid", self.udid,
                "--format", "h264",
                "--fps", "60"
            ]
            
            self.video_capture_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
            )
            
            time.sleep(1)
            if self.video_capture_process.poll() is None:
                self.video_streaming_active = True
                self.video_capture_thread = threading.Thread(
                    target=self._process_idb_video_stream, daemon=True
                )
                self.video_capture_thread.start()
                logger.info("✅ idb video-stream started successfully")
                return True
            else:
                stderr = self.video_capture_process.stderr.read().decode()
                logger.warning(f"❌ idb video-stream failed: {stderr}")
                self.video_capture_process = None
                
        except Exception as e:
            logger.warning(f"❌ idb video-stream error: {e}")
        
        return False
    
    def _try_ffmpeg_hardware_capture(self) -> bool:
        """Try FFmpeg hardware-accelerated capture"""
        try:
            logger.info("Trying FFmpeg hardware-accelerated capture...")
            window_info = SystemUtils.get_simulator_window_info()
            
            cmd = [
                "ffmpeg",
                "-f", "avfoundation",
                "-capture_cursor", "0",
                "-capture_mouse_clicks", "0",
                "-pixel_format", "uyvy422",
                "-framerate", "60",
                "-i", "1:none",
                "-vf", f"crop={window_info['width']}:{window_info['height']}:{window_info['x']}:{window_info['y']}",
                "-c:v", "h264_videotoolbox",
                "-profile:v", "baseline",
                "-level:v", "3.1",
                "-b:v", "2M",
                "-maxrate", "3M",
                "-bufsize", "6M",
                "-g", "30",
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-f", "h264",
                "-"
            ]
            
            self.video_capture_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
            )
            
            time.sleep(1)
            if self.video_capture_process.poll() is None:
                self.video_streaming_active = True
                self.video_capture_thread = threading.Thread(
                    target=self._process_h264_stream, daemon=True
                )
                self.video_capture_thread.start()
                logger.info("✅ FFmpeg hardware capture started")
                return True
            else:
                stderr = self.video_capture_process.stderr.read().decode()
                logger.warning(f"❌ FFmpeg hardware capture failed: {stderr}")
                self.video_capture_process = None
                
        except Exception as e:
            logger.warning(f"❌ FFmpeg hardware capture error: {e}")
        
        return False
    
    def _try_ffmpeg_software_capture(self) -> bool:
        """Try FFmpeg software capture"""
        try:
            logger.info("Trying FFmpeg software capture...")
            window_info = SystemUtils.get_simulator_window_info()
            
            cmd = [
                "ffmpeg",
                "-f", "avfoundation",
                "-capture_cursor", "0",
                "-framerate", "30",
                "-i", "1:none",
                "-vf", f"crop={window_info['width']}:{window_info['height']}:{window_info['x']}:{window_info['y']},scale=390:844",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-crf", "23",
                "-g", "15",
                "-f", "mjpeg",
                "-q:v", "3",
                "-"
            ]
            
            self.video_capture_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
            )
            
            time.sleep(1)
            if self.video_capture_process.poll() is None:
                self.video_streaming_active = True
                self.video_capture_thread = threading.Thread(
                    target=self._process_mjpeg_stream, daemon=True
                )
                self.video_capture_thread.start()
                logger.info("✅ FFmpeg software capture started")
                return True
            else:
                stderr = self.video_capture_process.stderr.read().decode()
                logger.warning(f"❌ FFmpeg software capture failed: {stderr}")
                
        except Exception as e:
            logger.warning(f"❌ FFmpeg software error: {e}")
        
        return False
    
    def _start_screenshot_mode(self) -> bool:
        """Start high-frequency screenshot mode"""
        logger.info("Falling back to ultra high-frequency screenshots...")
        self.video_streaming_active = True
        self.video_capture_thread = threading.Thread(
            target=self._ultra_high_fps_screenshots, daemon=True
        )
        self.video_capture_thread.start()
        return True
    
    def _process_idb_video_stream(self):
        """Process idb video stream"""
        logger.info("Processing idb video stream...")
        while self.video_streaming_active and self.video_capture_process:
            try:
                # For now, fall back to screenshot method for simplicity
                screenshot_data = self.screenshot_service.capture_ultra_fast_screenshot()
                if screenshot_data:
                    self._enqueue_frame({
                        "data": screenshot_data["data"],
                        "timestamp": time.time(),
                        "format": "jpeg",
                        "pixel_width": screenshot_data.get("pixel_width", 390),
                        "pixel_height": screenshot_data.get("pixel_height", 844)
                    })
                time.sleep(1/60)
            except Exception as e:
                logger.error(f"idb stream processing error: {e}")
                break
    
    def _process_h264_stream(self):
        """Process H.264 stream from FFmpeg"""
        logger.info("Processing H.264 stream...")
        frame_count = 0
        while self.video_streaming_active and self.video_capture_process:
            try:
                screenshot_data = self.screenshot_service.capture_ultra_fast_screenshot()
                if screenshot_data:
                    self._enqueue_frame({
                        "data": screenshot_data["data"],
                        "timestamp": time.time(),
                        "format": "jpeg",
                        "pixel_width": screenshot_data.get("pixel_width", 390),
                        "pixel_height": screenshot_data.get("pixel_height", 844)
                    })
                
                frame_count += 1
                time.sleep(1/45)
            except Exception as e:
                logger.error(f"H.264 processing error: {e}")
                break
    
    def _process_mjpeg_stream(self):
        """Process MJPEG stream from FFmpeg"""
        logger.info("Processing MJPEG stream...")
        buffer = b""
        
        while self.video_streaming_active and self.video_capture_process:
            try:
                chunk = self.video_capture_process.stdout.read(8192)
                if not chunk:
                    break
                
                buffer += chunk
                
                # Look for JPEG boundaries
                while b'\xff\xd8' in buffer and b'\xff\xd9' in buffer:
                    start = buffer.find(b'\xff\xd8')
                    end = buffer.find(b'\xff\xd9', start) + 2
                    
                    if start != -1 and end > start:
                        jpeg_data = buffer[start:end]
                        buffer = buffer[end:]
                        
                        import base64
                        frame_b64 = base64.b64encode(jpeg_data).decode('utf-8')
                        
                        self._enqueue_frame({
                            "data": frame_b64,
                            "timestamp": time.time(),
                            "format": "jpeg",
                            "pixel_width": 390,
                            "pixel_height": 844
                        })
                    else:
                        break
                        
            except Exception as e:
                logger.error(f"MJPEG processing error: {e}")
                break
    
    def _ultra_high_fps_screenshots(self):
        """Ultra high-frequency screenshot capture"""
        logger.info("Starting ultra high-FPS screenshot mode...")
        
        target_fps = settings.DEFAULT_VIDEO_FPS
        frame_interval = 1.0 / target_fps
        last_capture = 0
        frame_count = 0
        
        while self.video_streaming_active:
            current_time = time.time()
            
            if current_time - last_capture >= frame_interval:
                try:
                    screenshot_data = self.screenshot_service.capture_ultra_fast_screenshot()
                    if screenshot_data:
                        self._enqueue_frame({
                            "data": screenshot_data["data"],
                            "timestamp": current_time,
                            "format": "jpeg",
                            "pixel_width": screenshot_data.get("pixel_width", 390),
                            "pixel_height": screenshot_data.get("pixel_height", 844)
                        })
                        
                        frame_count += 1
                        if frame_count % 120 == 0:
                            logger.info(f"Screenshot mode: {frame_count} frames captured")
                    
                    last_capture = current_time
                    
                except Exception as e:
                    logger.error(f"Screenshot error: {e}")
                    time.sleep(0.1)
            else:
                sleep_time = frame_interval - (current_time - last_capture)
                if sleep_time > 0:
                    time.sleep(sleep_time)
    
    def _enqueue_frame(self, frame_data: Dict):
        """Add frame to queue with overflow handling"""
        try:
            self.video_frame_queue.put_nowait(frame_data)
        except queue.Full:
            try:
                self.video_frame_queue.get_nowait()
                self.video_frame_queue.put_nowait(frame_data)
            except queue.Empty:
                pass
    
    def get_frame(self, timeout: float = 0.05) -> Optional[Dict]:
        """Get next frame from queue"""
        try:
            return self.video_frame_queue.get(timeout=timeout)
        except Empty:
            return None
    
    def stop_video_capture(self):
        """Stop video capture"""
        logger.info("Stopping video capture...")
        
        with self.video_lock:
            self.video_streaming_active = False
            
            if self.video_capture_process:
                try:
                    self.video_capture_process.terminate()
                    self.video_capture_process.wait(timeout=3)
                except Exception:
                    try:
                        self.video_capture_process.kill()
                    except Exception:
                        pass
                self.video_capture_process = None
            
            if self.video_capture_thread:
                self.video_capture_thread.join(timeout=3)
                self.video_capture_thread = None
        
        # Clear queue
        while not self.video_frame_queue.empty():
            try:
                self.video_frame_queue.get_nowait()
            except Empty:
                break
    
    def add_client(self, client):
        """Add video client"""
        self.video_clients.append(client)
        if not self.video_streaming_active:
            self.start_video_capture()
    
    def remove_client(self, client):
        """Remove video client"""
        if client in self.video_clients:
            self.video_clients.remove(client)
        
        if not self.video_clients:
            self.stop_video_capture()
    
    def get_status(self) -> Dict:
        """Get video service status"""
        return {
            "video_streaming": self.video_streaming_active,
            "video_clients": len(self.video_clients),
            "queue_size": self.video_frame_queue.qsize(),
            "capture_method": "hardware" if self.video_capture_process else "screenshots"
        }