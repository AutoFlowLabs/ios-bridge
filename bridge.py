import os, subprocess, asyncio, json, base64, signal, atexit
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import logging
import time
import threading
import cv2
import numpy as np
from queue import Queue, Empty
import io
import tempfile
from PIL import Image
import re
import json
import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer
import av
from fractions import Fraction
from threading import Event
import uuid
import threading
from queue import Queue
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UDID = "B8BA84BA-664B-4D0D-9627-AC67F9BF0685"

app = FastAPI()
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Video streaming globals
video_clients: List[WebSocket] = []
video_capture_process = None
video_frame_queue = Queue(maxsize=3)  # Small buffer for real-time performance
video_capture_thread = None
video_streaming_active = False
video_lock = threading.Lock()
point_dimensions_cache = None

# WebRTC globals
webrtc_connections = {}
webrtc_video_source = None
webrtc_active = False
webrtc_frame_queue = Queue(maxsize=2)  # Small buffer for low latency
webrtc_current_frame = None
webrtc_frame_lock = threading.Lock()
webrtc_frame_event = Event() 
webrtc_frame_thread = None   
webrtc_quality_settings = {"fps": 60, "resolution_scale": 2, "quality": 95}



def cleanup_processes():
    """Clean up video processes"""
    logger.info("Cleaning up video processes...")
    stop_video_capture()
    logger.info("Stopping WebRTC capture...")
    stop_webrtc_capture()

atexit.register(cleanup_processes)
signal.signal(signal.SIGTERM, lambda s, f: cleanup_processes())

def get_simulator_window_info():
    """Get iOS Simulator window position and size"""
    try:
        # Try to get simulator window bounds using AppleScript
        script = '''
        tell application "System Events"
            tell process "Simulator"
                try
                    set frontWindow to first window
                    set windowPosition to position of frontWindow
                    set windowSize to size of frontWindow
                    return (item 1 of windowPosition) & "," & (item 2 of windowPosition) & "," & (item 1 of windowSize) & "," & (item 2 of windowSize)
                on error
                    return "error"
                end try
            end tell
        end tell
        '''
        
        cmd = ["osascript", "-e", script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0 and "error" not in result.stdout:
            coords = result.stdout.strip().split(",")
            if len(coords) == 4:
                x, y, width, height = map(int, coords)
                # Adjust for simulator chrome - typically screen is inset
                screen_x = x + 20  # Account for simulator frame
                screen_y = y + 100  # Account for simulator top bar
                screen_width = width - 40  # Remove left/right borders
                screen_height = height - 120  # Remove top/bottom chrome
                
                return {
                    "x": max(0, screen_x),
                    "y": max(0, screen_y), 
                    "width": max(300, screen_width),
                    "height": max(500, screen_height)
                }
    except Exception as e:
        logger.warning(f"Could not get simulator window info: {e}")
    
    # Default fallback coordinates (you may need to adjust these)
    return {"x": 100, "y": 100, "width": 390, "height": 844}

def start_video_capture():
    """Start hardware-accelerated video capture"""
    global video_capture_process, video_capture_thread, video_streaming_active
    
    with video_lock:
        if video_streaming_active:
            return True
            
        try:
            # Method 1: Try idb video-stream first
            logger.info("Attempting idb video-stream...")
            cmd = [
                "idb", "video-stream",
                "--udid", UDID,
                "--format", "h264",
                "--fps", "60"
            ]
            
            video_capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            # Test if process started successfully
            time.sleep(1)
            if video_capture_process.poll() is None:
                video_streaming_active = True
                video_capture_thread = threading.Thread(target=process_idb_video_stream, daemon=True)
                video_capture_thread.start()
                logger.info("✅ idb video-stream started successfully")
                return True
            else:
                stderr = video_capture_process.stderr.read().decode()
                logger.warning(f"❌ idb video-stream failed: {stderr}")
                video_capture_process = None
                
        except FileNotFoundError:
            logger.warning("❌ idb not found")
        except Exception as e:
            logger.warning(f"❌ idb video-stream error: {e}")
        
        # Method 2: FFmpeg screen capture with hardware acceleration
        try:
            logger.info("Trying FFmpeg hardware-accelerated capture...")
            
            window_info = get_simulator_window_info()
            
            # FFmpeg command for macOS screen capture with hardware encoding
            cmd = [
                "ffmpeg",
                "-f", "avfoundation",
                "-capture_cursor", "0",
                "-capture_mouse_clicks", "0", 
                "-pixel_format", "uyvy422",
                "-framerate", "60",
                "-i", "1:none",  # Screen capture, no audio
                "-vf", f"crop={window_info['width']}:{window_info['height']}:{window_info['x']}:{window_info['y']}",
                "-c:v", "h264_videotoolbox",  # Hardware acceleration on macOS
                "-profile:v", "baseline",
                "-level:v", "3.1", 
                "-b:v", "2M",  # 2 Mbps bitrate
                "-maxrate", "3M",
                "-bufsize", "6M",
                "-g", "30",  # Keyframe interval
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-f", "h264",
                "-"
            ]
            
            video_capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            time.sleep(1)
            if video_capture_process.poll() is None:
                video_streaming_active = True
                video_capture_thread = threading.Thread(target=process_h264_stream, daemon=True)
                video_capture_thread.start()
                logger.info("✅ FFmpeg hardware capture started")
                return True
            else:
                stderr = video_capture_process.stderr.read().decode()
                logger.warning(f"❌ FFmpeg hardware capture failed: {stderr}")
                video_capture_process = None
                
        except Exception as e:
            logger.warning(f"❌ FFmpeg hardware capture error: {e}")
        
        # Method 3: FFmpeg software encoding fallback
        try:
            logger.info("Trying FFmpeg software capture...")
            
            window_info = get_simulator_window_info()
            
            cmd = [
                "ffmpeg",
                "-f", "avfoundation",
                "-capture_cursor", "0",
                "-framerate", "30",  # Lower framerate for software encoding
                "-i", "1:none",
                "-vf", f"crop={window_info['width']}:{window_info['height']}:{window_info['x']}:{window_info['y']},scale=390:844",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "zerolatency", 
                "-crf", "23",
                "-g", "15",
                "-f", "mjpeg",  # Use MJPEG for easier processing
                "-q:v", "3",
                "-"
            ]
            
            video_capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            time.sleep(1)
            if video_capture_process.poll() is None:
                video_streaming_active = True
                video_capture_thread = threading.Thread(target=process_mjpeg_stream, daemon=True)
                video_capture_thread.start()
                logger.info("✅ FFmpeg software capture started")
                return True
            else:
                stderr = video_capture_process.stderr.read().decode()
                logger.warning(f"❌ FFmpeg software capture failed: {stderr}")
                
        except Exception as e:
            logger.warning(f"❌ FFmpeg software error: {e}")
        
        # Method 4: Ultra high-frequency screenshot fallback
        logger.info("Falling back to ultra high-frequency screenshots...")
        video_streaming_active = True
        video_capture_thread = threading.Thread(target=ultra_high_fps_screenshots, daemon=True)
        video_capture_thread.start()
        return True

def process_idb_video_stream():
    """Process idb video stream"""
    global video_capture_process
    
    logger.info("Processing idb video stream...")
    buffer = b""
    
    while video_streaming_active and video_capture_process:
        try:
            chunk = video_capture_process.stdout.read(4096)
            if not chunk:
                break
                
            # For H.264, we need to find NAL units
            # This is a simplified approach - you might need more sophisticated H.264 parsing
            buffer += chunk
            
            # For now, let's process as raw frames and convert to JPEG
            if len(buffer) > 65536:  # Process when we have enough data
                # Convert H.264 frame to displayable format using OpenCV
                try:
                    # This is simplified - actual H.264 decoding is more complex
                    # For now, fall back to screenshot method
                    screenshot_data = capture_ultra_fast_screenshot()
                    if screenshot_data:
                        enqueue_frame({
                            "data": screenshot_data["data"],
                            "timestamp": time.time(),
                            "format": "jpeg",
                            "pixel_width": screenshot_data.get("pixel_width", 390),
                            "pixel_height": screenshot_data.get("pixel_height", 844)
                        })
                    buffer = b""  # Clear buffer
                    time.sleep(1/60)  # 60 FPS
                except:
                    buffer = b""
                    
        except Exception as e:
            logger.error(f"idb stream processing error: {e}")
            break

def process_h264_stream():
    """Process H.264 stream from FFmpeg"""
    global video_capture_process
    
    logger.info("Processing H.264 stream...")
    # For this implementation, we'll decode H.264 to frames
    # This requires more complex handling, so let's use a simpler approach
    
    frame_count = 0
    while video_streaming_active and video_capture_process:
        try:
            # Read H.264 data and process with OpenCV
            # This is complex, so for now use screenshot fallback
            screenshot_data = capture_ultra_fast_screenshot()
            if screenshot_data:
                enqueue_frame({
                    "data": screenshot_data["data"],
                    "timestamp": time.time(),
                    "format": "jpeg",
                    "pixel_width": screenshot_data.get("pixel_width", 390),
                    "pixel_height": screenshot_data.get("pixel_height", 844)
                })
            
            frame_count += 1
            time.sleep(1/45)  # 45 FPS for hardware mode
            
        except Exception as e:
            logger.error(f"H.264 processing error: {e}")
            break

def process_mjpeg_stream():
    """Process MJPEG stream from FFmpeg"""
    global video_capture_process
    
    logger.info("Processing MJPEG stream...")
    buffer = b""
    
    while video_streaming_active and video_capture_process:
        try:
            chunk = video_capture_process.stdout.read(8192)
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
                    
                    # Convert to base64
                    frame_b64 = base64.b64encode(jpeg_data).decode('utf-8')
                    
                    enqueue_frame({
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

def ultra_high_fps_screenshots():
    """Ultra high-frequency screenshot capture"""
    logger.info("Starting ultra high-FPS screenshot mode...")
    
    target_fps = 60
    frame_interval = 1.0 / target_fps
    last_capture = 0
    frame_count = 0
    
    while video_streaming_active:
        current_time = time.time()
        
        if current_time - last_capture >= frame_interval:
            try:
                screenshot_data = capture_ultra_fast_screenshot()
                if screenshot_data:
                    enqueue_frame({
                        "data": screenshot_data["data"],
                        "timestamp": current_time,
                        "format": "jpeg", 
                        "pixel_width": screenshot_data.get("pixel_width", 390),
                        "pixel_height": screenshot_data.get("pixel_height", 844)
                    })
                    
                    frame_count += 1
                    if frame_count % 120 == 0:  # Log every 2 seconds
                        logger.info(f"Screenshot mode: {frame_count} frames captured")
                        
                last_capture = current_time
                
            except Exception as e:
                logger.error(f"Screenshot error: {e}")
                time.sleep(0.1)
        else:
            # Precise timing
            sleep_time = frame_interval - (current_time - last_capture)
            if sleep_time > 0:
                time.sleep(sleep_time)

def capture_ultra_fast_screenshot():
    """Ultra-optimized screenshot capture"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            cmd = ["idb", "screenshot", "--udid", UDID, temp_file.name]
            result = subprocess.run(cmd, capture_output=True, timeout=0.5)  # Very aggressive timeout
            
            if result.returncode == 0 and os.path.exists(temp_file.name):
                with Image.open(temp_file.name) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Ultra-fast JPEG compression
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=80, optimize=False)
                    image_data = output.getvalue()
                
                os.unlink(temp_file.name)
                
                return {
                    "data": base64.b64encode(image_data).decode('utf-8'),
                    "pixel_width": img.width,
                    "pixel_height": img.height
                }
                
    except subprocess.TimeoutExpired:
        pass  # Skip this frame
    except Exception:
        pass
    
    return None

def enqueue_frame(frame_data):
    """Add frame to queue with overflow handling"""
    try:
        video_frame_queue.put_nowait(frame_data)
    except:
        # Queue full - drop oldest frame
        try:
            video_frame_queue.get_nowait()
            video_frame_queue.put_nowait(frame_data)
        except:
            pass  # Still full, drop this frame

def stop_video_capture():
    """Stop video capture"""
    global video_capture_process, video_streaming_active, video_capture_thread
    
    logger.info("Stopping video capture...")
    
    with video_lock:
        video_streaming_active = False
        
        if video_capture_process:
            try:
                video_capture_process.terminate()
                video_capture_process.wait(timeout=3)
            except:
                try:
                    video_capture_process.kill()
                except:
                    pass
            video_capture_process = None
        
        if video_capture_thread:
            video_capture_thread.join(timeout=3)
            video_capture_thread = None
    
    # Clear queue
    while not video_frame_queue.empty():
        try:
            video_frame_queue.get_nowait()
        except:
            break

async def get_point_dimensions():
    """Get device point dimensions with caching"""
    global point_dimensions_cache
    
    if point_dimensions_cache:
        return point_dimensions_cache
    
    try:
        cmd = ["idb", "describe", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        
        if result.returncode == 0:
            width_match = re.search(r'width_points=(\d+)', result.stdout)
            height_match = re.search(r'height_points=(\d+)', result.stdout) 
            
            if width_match and height_match:
                point_dimensions_cache = (int(width_match.group(1)), int(height_match.group(1)))
                return point_dimensions_cache
    except Exception as e:
        logger.error(f"Error getting point dimensions: {e}")
    
    # Default dimensions
    point_dimensions_cache = (390, 844)
    return point_dimensions_cache


class SimulatorVideoTrack(VideoStreamTrack):
    """Enhanced video track for iOS Simulator with high quality"""
    
    def __init__(self, target_fps=60):
        super().__init__()
        self.frame_count = 0
        self.target_fps = target_fps
        self.frame_time = 1.0 / target_fps
        self.last_frame_time = time.time()
        
    async def recv(self):
        """Generate high-quality video frames for WebRTC"""
        global webrtc_current_frame
        
        # Frame timing for consistent FPS
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        if elapsed < self.frame_time:
            await asyncio.sleep(self.frame_time - elapsed)
        
        with webrtc_frame_lock:
            if webrtc_current_frame is None:
                # Generate a high-quality placeholder frame
                frame = av.VideoFrame.from_ndarray(
                    np.zeros((844, 390, 3), dtype=np.uint8), 
                    format='rgb24'
                )
            else:
                # Create a new frame from the same data instead of copying
                frame_array = webrtc_current_frame.to_ndarray(format='rgb24')
                frame = av.VideoFrame.from_ndarray(frame_array, format='rgb24')
        
        # Set precise timing
        frame.pts = self.frame_count
        frame.time_base = Fraction(1, self.target_fps)
        self.frame_count += 1
        self.last_frame_time = time.time()
        
        return frame
    

def webrtc_frame_producer():
    """Continuously capture frames for WebRTC"""
    global webrtc_current_frame, webrtc_active
    
    logger.info("Starting WebRTC frame producer...")
    
    while webrtc_active:
        try:
            # Capture screenshot
            screenshot_data = capture_ultra_fast_screenshot()
            if screenshot_data:
                # Decode base64 image
                image_bytes = base64.b64decode(screenshot_data["data"])
                
                # Convert to numpy array
                with Image.open(io.BytesIO(image_bytes)) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize for optimal WebRTC performance
                    img = img.resize((390, 844), Image.Resampling.LANCZOS)
                    img_array = np.array(img)
                
                # Create AV frame with thread safety
                new_frame = av.VideoFrame.from_ndarray(img_array, format='rgb24')
                
                with webrtc_frame_lock:
                    webrtc_current_frame = new_frame
            
            time.sleep(1/30)  # 30 FPS target
            
        except Exception as e:
            logger.error(f"WebRTC frame producer error: {e}")
            time.sleep(0.1)

            
def webrtc_high_quality_frame_producer():
    """High-quality, high-FPS frame producer for WebRTC"""
    global webrtc_current_frame, webrtc_active
    
    logger.info("Starting high-quality WebRTC frame producer...")
    
    target_fps = 60
    frame_interval = 1.0 / target_fps
    last_capture = 0
    frame_count = 0
    
    # Performance tracking
    capture_times = []
    processing_times = []
    
    while webrtc_active:
        frame_start = time.time()
        
        if frame_start - last_capture >= frame_interval:
            try:
                capture_start = time.time()
                
                # Use optimized screenshot method
                screenshot_data = capture_optimized_screenshot_for_webrtc()
                
                capture_time = time.time() - capture_start
                capture_times.append(capture_time)
                if len(capture_times) > 100:
                    capture_times.pop(0)
                
                if screenshot_data:
                    processing_start = time.time()
                    
                    # Decode base64 image
                    image_bytes = base64.b64decode(screenshot_data["data"])
                    
                    # High-quality image processing
                    with Image.open(io.BytesIO(image_bytes)) as img:
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # High-quality resize with optimal dimensions
                        target_width = 390 * 2  # 2x resolution for better quality
                        target_height = 844 * 2
                        
                        # Use high-quality resampling
                        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                        img_array = np.array(img, dtype=np.uint8)
                        
                        # Ensure proper color space
                        if img_array.shape[2] == 4:  # RGBA
                            img_array = img_array[:, :, :3]  # Convert to RGB
                    
                    # Create high-quality AV frame with thread safety
                    new_frame = av.VideoFrame.from_ndarray(img_array, format='rgb24')
                    
                    with webrtc_frame_lock:
                        webrtc_current_frame = new_frame
                    
                    processing_time = time.time() - processing_start
                    processing_times.append(processing_time)
                    if len(processing_times) > 100:
                        processing_times.pop(0)
                    
                    frame_count += 1
                    
                    # Log performance every 5 seconds
                    if frame_count % 300 == 0:
                        avg_capture = sum(capture_times) / len(capture_times) * 1000
                        avg_processing = sum(processing_times) / len(processing_times) * 1000
                        logger.info(f"WebRTC: {target_fps}fps target, avg capture: {avg_capture:.1f}ms, avg processing: {avg_processing:.1f}ms")
                    
                last_capture = frame_start
                
            except Exception as e:
                logger.error(f"WebRTC frame producer error: {e}")
                time.sleep(0.01)
        else:
            # Precise timing with minimal sleep
            sleep_time = frame_interval - (time.time() - last_capture)
            if sleep_time > 0.001:  # Only sleep if meaningful time remaining
                time.sleep(min(sleep_time, 0.01))

def capture_optimized_screenshot_for_webrtc():
    """Ultra-optimized screenshot capture specifically for WebRTC"""
    try:
        # Try different capture methods for best quality/speed
        
        # Method 1: Direct idb with optimized settings
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            cmd = ["idb", "screenshot", "--udid", UDID, temp_file.name]
            result = subprocess.run(cmd, capture_output=True, timeout=0.3)
            
            if result.returncode == 0 and os.path.exists(temp_file.name):
                with Image.open(temp_file.name) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # High-quality PNG to JPEG conversion
                    output = io.BytesIO()
                    
                    # Use maximum quality for WebRTC
                    img.save(output, format='JPEG', 
                           quality=95,      # High quality
                           optimize=True,   # Optimize file size
                           progressive=True, # Progressive JPEG
                           subsampling=0)   # No chroma subsampling for best quality
                    
                    image_data = output.getvalue()
                
                os.unlink(temp_file.name)
                
                return {
                    "data": base64.b64encode(image_data).decode('utf-8'),
                    "pixel_width": img.width,
                    "pixel_height": img.height
                }
                
    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        logger.debug(f"Screenshot error: {e}")
    
    return None

def start_webrtc_capture(fps=60):
    """Start high-quality WebRTC video capture"""
    global webrtc_active, webrtc_frame_thread
    
    if webrtc_active:
        return True
    
    try:
        webrtc_active = True
        webrtc_frame_thread = threading.Thread(
            target=webrtc_high_quality_frame_producer, 
            daemon=True
        )
        webrtc_frame_thread.start()
        logger.info(f"✅ High-quality WebRTC capture started at {fps}fps")
        return True
    except Exception as e:
        logger.error(f"❌ WebRTC capture failed: {e}")
        return False
    

def stop_webrtc_capture():
    """Stop WebRTC video capture"""
    global webrtc_active, webrtc_current_frame
    
    webrtc_active = False
    webrtc_current_frame = None
    
    # Close all WebRTC connections safely
    connections_to_close = list(webrtc_connections.items())
    webrtc_connections.clear()  # Clear first to prevent race conditions
    
    for connection_id, pc in connections_to_close:
        try:
            asyncio.create_task(pc.close())
            logger.debug(f"Closed WebRTC connection: {connection_id}")
        except Exception as e:
            logger.debug(f"Error closing WebRTC connection {connection_id}: {e}")


@app.websocket("/ws/control")
async def control_ws(ws: WebSocket):
    """Control WebSocket for device interactions"""
    await ws.accept()
    logger.info("Control WebSocket connected")
    
    try:
        while True:
            msg = await ws.receive_text()
            ev = json.loads(msg)
            
            if ev["t"] == "tap":
                x, y = ev["x"], ev["y"]
                cmd = ["idb", "ui", "tap", str(x), str(y), "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                
                if result.returncode == 0:
                    logger.info(f"✅ Tap: ({x}, {y})")
                else:
                    logger.error(f"❌ Tap failed: {result.stderr}")
                    
            elif ev["t"] == "swipe":
                start_x, start_y = ev["start_x"], ev["start_y"]
                end_x, end_y = ev["end_x"], ev["end_y"]
                duration = ev.get("duration", 0.2)
                
                cmd = ["idb", "ui", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), "--duration", str(duration), "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                
                if result.returncode == 0:
                    logger.info(f"✅ Swipe: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
                else:
                    logger.error(f"❌ Swipe failed: {result.stderr}")
                    
            elif ev["t"] == "text":
                text = ev["text"]
                cmd = ["idb", "ui", "text", text, "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    logger.info(f"✅ Text entered")
                else:
                    logger.error(f"❌ Text failed")
                    
            elif ev["t"] == "button":
                button = ev["button"]
                button_mapping = {
                    'home': 'HOME', 'lock': 'LOCK', 'siri': 'SIRI',
                    'side-button': 'SIDE_BUTTON', 'apple-pay': 'APPLE_PAY'
                }
                idb_button = button_mapping.get(button, button.upper())
                
                cmd = ["idb", "ui", "button", idb_button, "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                
                if result.returncode == 0:
                    logger.info(f"✅ Button: {button}")
                else:
                    logger.error(f"❌ Button failed: {button}")
                    
    except WebSocketDisconnect:
        logger.info("Control WebSocket disconnected")

@app.websocket("/ws/video")
async def video_ws(ws: WebSocket):
    """Real-time video streaming WebSocket"""
    await ws.accept()
    logger.info("Video WebSocket connected")
    
    video_clients.append(ws)
    
    # Start video capture if not already running
    if not video_streaming_active:
        start_video_capture()
    
    try:
        frame_count = 0
        fps_counter = []
        last_fps_update = time.time()
        point_width, point_height = await get_point_dimensions()
        
        while True:
            try:
                # Get frame from queue with timeout
                frame_data = video_frame_queue.get(timeout=0.05)
                
                frame_count += 1
                current_time = time.time()
                
                # Calculate FPS
                fps_counter.append(current_time)
                fps_counter = [t for t in fps_counter if current_time - t < 1.0]
                current_fps = len(fps_counter)
                
                # Send frame
                video_frame = {
                    "type": "video_frame",
                    "data": frame_data["data"],
                    "pixel_width": frame_data.get("pixel_width", 390),
                    "pixel_height": frame_data.get("pixel_height", 844),
                    "point_width": point_width,
                    "point_height": point_height,
                    "frame": frame_count,
                    "timestamp": frame_data["timestamp"],
                    "fps": current_fps,
                    "format": frame_data.get("format", "jpeg")
                }
                
                await ws.send_text(json.dumps(video_frame))
                
                # Log performance
                if current_time - last_fps_update > 3:
                    logger.info(f"🎥 Video streaming: {current_fps} FPS, Queue: {video_frame_queue.qsize()}")
                    last_fps_update = current_time
                    
            except Empty:
                # No frame available
                await asyncio.sleep(0.01)
                continue
            except Exception as e:
                logger.error(f"Video frame send error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("Video WebSocket disconnected")
    except Exception as e:
        logger.error(f"Video WebSocket error: {e}")
    finally:
        if ws in video_clients:
            video_clients.remove(ws)
        
        # Stop capture if no more clients
        if not video_clients:
            stop_video_capture()

@app.websocket("/ws/screenshot")
async def screenshot_ws(ws: WebSocket):
    """Screenshot mode WebSocket"""
    await ws.accept()
    logger.info("Screenshot WebSocket connected")
    
    try:
        # Send initial screenshot
        screenshot_result = capture_ultra_fast_screenshot()
        if screenshot_result:
            point_width, point_height = await get_point_dimensions()
            await ws.send_text(json.dumps({
                "type": "screenshot",
                "data": screenshot_result["data"],
                "pixel_width": screenshot_result.get("pixel_width", 390),
                "pixel_height": screenshot_result.get("pixel_height", 844),
                "point_width": point_width,
                "point_height": point_height,
                "format": "jpeg"
            }))
        
        async for message in ws.iter_text():
            try:
                ev = json.loads(message)
                
                if ev.get("t") == "tap":
                    x, y = ev["x"], ev["y"]
                    cmd = ["idb", "ui", "tap", str(x), str(y), "--udid", UDID]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                    
                    if result.returncode == 0:
                        logger.info(f"Screenshot tap: ({x}, {y})")
                        
                        # Get fresh screenshot
                        await asyncio.sleep(0.1)
                        screenshot_result = capture_ultra_fast_screenshot()
                        if screenshot_result:
                            point_width, point_height = await get_point_dimensions()
                            await ws.send_text(json.dumps({
                                "type": "screenshot",
                                "data": screenshot_result["data"],
                                "pixel_width": screenshot_result.get("pixel_width", 390),
                                "pixel_height": screenshot_result.get("pixel_height", 844),
                                "point_width": point_width,
                                "point_height": point_height,
                                "format": "jpeg"
                            }))
                        
                elif ev.get("t") == "refresh":
                    screenshot_result = capture_ultra_fast_screenshot()
                    if screenshot_result:
                        point_width, point_height = await get_point_dimensions()
                        await ws.send_text(json.dumps({
                            "type": "screenshot",
                            "data": screenshot_result["data"],
                            "pixel_width": screenshot_result.get("pixel_width", 390),
                            "pixel_height": screenshot_result.get("pixel_height", 844),
                            "point_width": point_width,
                            "point_height": point_height,
                            "format": "jpeg"
                        }))
                        
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Message handling error: {e}")
                
    except WebSocketDisconnect:
        logger.info("Screenshot WebSocket disconnected")

@app.websocket("/ws/webrtc")
async def webrtc_signaling(websocket: WebSocket):
    """WebRTC signaling WebSocket"""
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    logger.info(f"WebRTC signaling connected: {connection_id}")
    
    try:
        # Start capture if not already running
        if not webrtc_active:
            start_webrtc_capture()
        
        async for message in websocket.iter_text():
            try:
                data = json.loads(message)
                await handle_webrtc_message(websocket, connection_id, data)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in WebRTC message")
            except Exception as e:
                logger.error(f"WebRTC message handling error: {e}")
                
    except Exception as e:
        logger.error(f"WebRTC signaling error: {e}")
    finally:
        # Clean up connection with safe deletion
        if connection_id in webrtc_connections:
            try:
                await webrtc_connections[connection_id].close()
            except Exception as e:
                logger.debug(f"Error closing WebRTC connection: {e}")
            finally:
                try:
                    del webrtc_connections[connection_id]
                except KeyError:
                    logger.debug(f"WebRTC connection already removed: {connection_id}")

        logger.info(f"WebRTC signaling disconnected: {connection_id}")
        
        # Stop capture if no more connections
        if not webrtc_connections:
            stop_webrtc_capture()


async def handle_webrtc_message(websocket: WebSocket, connection_id: str, data: dict):
    """Handle WebRTC signaling messages with quality optimization"""
    message_type = data.get("type")
    
    if message_type == "offer":
        # Create RTCPeerConnection with correct configuration format
        pc = RTCPeerConnection()
        webrtc_connections[connection_id] = pc
        
        # Add high-quality video track
        video_track = SimulatorVideoTrack(target_fps=60)
        pc.addTrack(video_track)
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"WebRTC connection state: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed"]:
                # Safe deletion - check if connection still exists
                if connection_id in webrtc_connections:
                    try:
                        del webrtc_connections[connection_id]
                        logger.info(f"Removed failed WebRTC connection: {connection_id}")
                    except KeyError:
                        pass  # Already removed
        
        # Set remote description
        await pc.setRemoteDescription(RTCSessionDescription(
            sdp=data["sdp"],
            type=data["type"]
        ))
        
        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        # Send answer back
        await websocket.send_text(json.dumps({
            "type": "answer",
            "sdp": pc.localDescription.sdp
        }))
        
    elif message_type == "ice-candidate":
        if connection_id in webrtc_connections:
            pc = webrtc_connections[connection_id]
            candidate_data = data.get("candidate")
            if candidate_data:
                from aiortc import RTCIceCandidate
                candidate = RTCIceCandidate(
                    candidate=candidate_data.get("candidate"),
                    sdpMid=candidate_data.get("sdpMid"),
                    sdpMLineIndex=candidate_data.get("sdpMLineIndex")
                )
                await pc.addIceCandidate(candidate)


@app.get("/webrtc/quality/{quality}")
async def set_webrtc_quality(quality: str):
    """Set WebRTC quality preset"""
    global webrtc_quality_settings
    
    presets = {
        "low": {"fps": 30, "resolution_scale": 1, "quality": 70},
        "medium": {"fps": 45, "resolution_scale": 1.5, "quality": 85},
        "high": {"fps": 60, "resolution_scale": 2, "quality": 95},
        "ultra": {"fps": 60, "resolution_scale": 2.5, "quality": 98}
    }
    
    if quality in presets:
        webrtc_quality_settings = presets[quality]
        logger.info(f"WebRTC quality set to: {quality}")
        return {"success": True, "quality": quality, "settings": presets[quality]}
    else:
        return {"success": False, "error": "Invalid quality preset"}

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.get("/status")
async def status():
    try:
        test_cmd = ["idb", "list-targets"]
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
        simulator_accessible = UDID in result.stdout
    except:
        simulator_accessible = False
    
    return {
        "udid": UDID,
        "simulator_accessible": simulator_accessible,
        "video_streaming": video_streaming_active,
        "video_clients": len(video_clients),
        "webrtc_active": webrtc_active,
        "webrtc_connections": len(webrtc_connections),
        "queue_size": video_frame_queue.qsize(),
        "capture_method": "hardware" if video_capture_process else "screenshots",
        "status": "healthy" if (video_streaming_active or webrtc_active) else "starting"
    }

@app.get("/debug/screenshot")
async def debug_screenshot():
    screenshot = capture_ultra_fast_screenshot()
    return {
        "success": screenshot is not None,
        "data_length": len(screenshot["data"]) if screenshot else 0,
        "dimensions": f"{screenshot['pixel_width']}x{screenshot['pixel_height']}" if screenshot else "unknown",
        "format": screenshot.get("format", "unknown") if screenshot else "unknown"
    }

# Add all your existing debug endpoints here...
@app.get("/debug/tap/{x}/{y}")
async def debug_tap(x: int, y: int):
    try:
        cmd = ["idb", "ui", "tap", str(x), str(y), "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/debug/home")
async def debug_home():
    try:
        cmd = ["idb", "ui", "button", "HOME", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/debug/lock")
async def debug_lock():
    try:
        cmd = ["idb", "ui", "button", "LOCK", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/debug/siri")
async def debug_siri():
    try:
        cmd = ["idb", "ui", "button", "SIRI", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")