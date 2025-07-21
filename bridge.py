import os, subprocess, asyncio, json, base64, tempfile, signal, atexit
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import logging
import time
import struct
from concurrent.futures import ThreadPoolExecutor
import threading
import cv2
import numpy as np
from PIL import Image
import io

logging.basicConfig(level=logging.INFO)
logging.getLogger("PIL").setLevel(logging.WARNING)  # Reduce PIL noise
logger = logging.getLogger(__name__)

UDID = "B8BA84BA-664B-4D0D-9627-AC67F9BF0685"   

app = FastAPI()

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global variables
video_clients: List[WebSocket] = []
video_stream_process = None
video_stream_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=6)  # Increased workers

# Frame buffer for high-performance streaming
frame_buffer = None
frame_buffer_time = 0
frame_buffer_lock = threading.Lock()

def cleanup_processes():
    """Clean up background processes"""
    logger.info("Server shutdown - cleaning up...")
    stop_video_stream()
    executor.shutdown(wait=False)

# Register cleanup
atexit.register(cleanup_processes)
signal.signal(signal.SIGTERM, lambda s, f: cleanup_processes())

def start_video_stream():
    """Start h264 video stream using idb"""
    global video_stream_process
    
    with video_stream_lock:
        if video_stream_process is None or video_stream_process.poll() is not None:
            try:
                # Use idb video stream for much better performance
                cmd = [
                    "idb", "video-stream", 
                    "--udid", UDID,
                    "--format", "h264",  # Use hardware-accelerated H264
                    "--fps", "60",       # Target 60 FPS
                    "--compression-quality", "0.8",  # Good balance
                    "--output", "-"      # Output to stdout
                ]
                
                logger.info(f"Starting video stream: {' '.join(cmd)}")
                video_stream_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0  # Unbuffered for real-time
                )
                
                logger.info("Video stream process started")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start video stream: {e}")
                return False
    
    return video_stream_process is not None

def stop_video_stream():
    """Stop video stream"""
    global video_stream_process
    
    with video_stream_lock:
        if video_stream_process:
            try:
                video_stream_process.terminate()
                video_stream_process.wait(timeout=3)
            except:
                video_stream_process.kill()
            video_stream_process = None

def capture_frame_from_stream():
    """Capture frame from video stream - much faster than screenshot"""
    global video_stream_process, frame_buffer, frame_buffer_time
    
    if not video_stream_process or video_stream_process.poll() is not None:
        if not start_video_stream():
            return None
    
    try:
        # Read H264 frame data
        # This is simplified - you might need to implement proper H264 decoding
        # For now, fall back to optimized screenshot but with better caching
        return capture_optimized_screenshot()
        
    except Exception as e:
        logger.error(f"Frame capture error: {e}")
        return None

def capture_optimized_screenshot():
    """Ultra-optimized screenshot with aggressive caching and compression"""
    try:
        # Use PNG format but with specific optimizations
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            # Optimized idb command with quality settings
            cmd = [
                "idb", "screenshot", 
                "--udid", UDID, 
                temp_file.name
            ]
            
            # Use shorter timeout for better responsiveness
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5)
            
            if result.returncode == 0 and os.path.exists(temp_file.name):
                # Use PIL for faster processing and compression
                with Image.open(temp_file.name) as img:
                    # Convert to RGB if needed and resize for better performance
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    original_width, original_height = img.size
                    
                    # Optional: Scale down for better streaming performance
                    # Uncomment if you want to trade quality for speed
                    # scale_factor = 0.8  # 80% of original size
                    # new_width = int(original_width * scale_factor)
                    # new_height = int(original_height * scale_factor)
                    # img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Compress to JPEG for better streaming (much smaller than PNG)
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=85, optimize=True)
                    image_data = output.getvalue()
                
                os.unlink(temp_file.name)
                
                return {
                    "data": base64.b64encode(image_data).decode('utf-8'),
                    "pixel_width": original_width,
                    "pixel_height": original_height,
                    "timestamp": time.time(),
                    "format": "jpeg"  # Changed from PNG
                }
                
    except subprocess.TimeoutExpired:
        logger.warning("Screenshot timeout")
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
    
    return None

async def capture_frame_optimized():
    """Optimized frame capture with smart caching"""
    global frame_buffer, frame_buffer_time
    
    current_time = time.time()
    
    # Use cache if less than 8ms old (120+ FPS target)
    with frame_buffer_lock:
        if (frame_buffer and 
            current_time - frame_buffer_time < 0.008):  # More aggressive caching
            return frame_buffer
    
    # Capture new frame in thread pool
    loop = asyncio.get_event_loop()
    frame_data = await loop.run_in_executor(executor, capture_optimized_screenshot)
    
    if frame_data:
        # Cache point dimensions
        point_width, point_height = await get_point_dimensions()
        
        result = {
            **frame_data,
            "point_width": point_width,
            "point_height": point_height,
            "width": frame_data["pixel_width"],
            "height": frame_data["pixel_height"]
        }
        
        # Update cache
        with frame_buffer_lock:
            frame_buffer = result
            frame_buffer_time = current_time
        
        return result
    
    return frame_buffer  # Return cached version if new capture failed

# Cache point dimensions since they don't change
point_dimensions_cache = None
point_dimensions_cache_time = 0

async def get_point_dimensions():
    """Get the point dimensions with caching"""
    global point_dimensions_cache, point_dimensions_cache_time
    
    current_time = time.time()
    
    # Cache for 60 seconds
    if (point_dimensions_cache and 
        current_time - point_dimensions_cache_time < 60):
        return point_dimensions_cache
    
    try:
        cmd = ["idb", "describe", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        
        if result.returncode == 0:
            output = result.stdout
            import re
            width_match = re.search(r'width_points=(\d+)', output)
            height_match = re.search(r'height_points=(\d+)', output)
            
            if width_match and height_match:
                dimensions = (int(width_match.group(1)), int(height_match.group(1)))
                point_dimensions_cache = dimensions
                point_dimensions_cache_time = current_time
                return dimensions
        
        # Fallback values
        logger.warning("Could not parse point dimensions, using iPhone 14 defaults")
        dimensions = (390, 844)
        point_dimensions_cache = dimensions
        point_dimensions_cache_time = current_time
        return dimensions
        
    except Exception as e:
        logger.error(f"Error getting point dimensions: {e}")
        return (390, 844)

@app.websocket("/ws/control")
async def control_ws(ws: WebSocket):
    """WebSocket for device control commands"""
    await ws.accept()
    logger.info("Control WebSocket connected")
    
    try:
        while True:
            msg = await ws.receive_text()
            ev = json.loads(msg)
            
            if ev["t"] == "tap":
                x, y = ev["x"], ev["y"]
                cmd = ["idb", "ui", "tap", str(x), str(y), "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)  # Faster timeout
                
                if result.returncode == 0:
                    logger.info(f"✅ Tap: ({x}, {y})")
                    # Invalidate cache immediately for responsive UI
                    global frame_buffer_time
                    frame_buffer_time = 0
                else:
                    logger.error(f"❌ Tap failed: {result.stderr}")
                    
            elif ev["t"] == "swipe":
                start_x, start_y = ev["start_x"], ev["start_y"]
                end_x, end_y = ev["end_x"], ev["end_y"]
                duration = ev.get("duration", 0.3)  # Faster default duration
                
                cmd = ["idb", "ui", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), "--duration", str(duration), "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    logger.info(f"✅ Swipe: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
                    frame_buffer_time = 0
                else:
                    logger.error(f"❌ Swipe failed: {result.stderr}")
                    
            elif ev["t"] == "text":
                text = ev["text"]
                cmd = ["idb", "ui", "text", text, "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    logger.info(f"✅ Text entered: {text}")
                    frame_buffer_time = 0
                else:
                    logger.error(f"❌ Text failed: {result.stderr}")
                    
            elif ev["t"] == "button":
                button = ev["button"]
                
                button_mapping = {
                    'home': 'HOME',
                    'lock': 'LOCK', 
                    'siri': 'SIRI',
                    'side-button': 'SIDE_BUTTON',
                    'apple-pay': 'APPLE_PAY'
                }
                
                idb_button = button_mapping.get(button, button.upper())
                
                cmd = ["idb", "ui", "button", idb_button, "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                
                if result.returncode == 0:
                    logger.info(f"✅ Button pressed: {button} ({idb_button})")
                    frame_buffer_time = 0
                else:
                    logger.error(f"❌ Button failed: {result.stderr}")
                    
    except WebSocketDisconnect:
        logger.info("Control WebSocket disconnected")

@app.websocket("/ws/video")
async def video_ws(ws: WebSocket):
    """Ultra high-performance video streaming"""
    await ws.accept()
    logger.info("Video WebSocket connected")
    
    video_clients.append(ws)
    
    try:
        frame_count = 0
        target_fps = 45  # More realistic target for screenshot-based streaming
        frame_interval = 1.0 / target_fps
        last_frame_time = 0
        
        # Performance tracking
        frame_times = []
        last_stats_time = time.time()
        
        while True:
            frame_start = time.time()
            
            # More precise FPS throttling
            time_since_last = frame_start - last_frame_time
            if time_since_last < frame_interval:
                sleep_time = frame_interval - time_since_last
                await asyncio.sleep(sleep_time)
                continue
            
            try:
                frame_result = await capture_frame_optimized()
                
                if frame_result:
                    frame_count += 1
                    
                    # Calculate actual FPS
                    frame_times.append(frame_start)
                    if len(frame_times) > 30:  # Keep last 30 frames for FPS calc
                        frame_times.pop(0)
                    
                    actual_fps = 0
                    if len(frame_times) > 1:
                        time_span = frame_times[-1] - frame_times[0]
                        if time_span > 0:
                            actual_fps = (len(frame_times) - 1) / time_span
                    
                    # Send frame data
                    frame_data = {
                        "type": "video_frame",
                        "data": frame_result["data"],
                        "pixel_width": frame_result.get("pixel_width", 0),
                        "pixel_height": frame_result.get("pixel_height", 0),
                        "point_width": frame_result.get("point_width", 390),
                        "point_height": frame_result.get("point_height", 844),
                        "frame": frame_count,
                        "timestamp": frame_result.get("timestamp", frame_start),
                        "fps": round(actual_fps, 1),
                        "format": frame_result.get("format", "png")
                    }
                    
                    await ws.send_text(json.dumps(frame_data))
                    
                    last_frame_time = frame_start
                    
                    # Less frequent logging for better performance
                    if time.time() - last_stats_time > 2:  # Every 2 seconds
                        logger.info(f"Video performance: Frame {frame_count}, FPS: {actual_fps:.1f}")
                        last_stats_time = time.time()
                        
            except Exception as e:
                logger.error(f"Video frame error: {e}")
                await asyncio.sleep(0.05)  # Brief pause before retry
            
    except WebSocketDisconnect:
        logger.info("Video WebSocket disconnected")
    except Exception as e:
        logger.error(f"Video WebSocket error: {e}")
    finally:
        if ws in video_clients:
            video_clients.remove(ws)

@app.websocket("/ws/screenshot")
async def screenshot_ws(ws: WebSocket):
    """WebSocket for screenshot mode with interaction"""
    await ws.accept()
    logger.info("Screenshot WebSocket connected")
    
    try:
        # Send initial screenshot
        screenshot_result = await capture_frame_optimized()
        if screenshot_result:
            await ws.send_text(json.dumps({
                "type": "screenshot",
                "data": screenshot_result["data"],
                "pixel_width": screenshot_result.get("pixel_width", 0),
                "pixel_height": screenshot_result.get("pixel_height", 0),
                "point_width": screenshot_result.get("point_width", 390),
                "point_height": screenshot_result.get("point_height", 844),
                "format": screenshot_result.get("format", "png")
            }))
        
        async for message in ws.iter_text():
            try:
                ev = json.loads(message)
                
                if ev.get("t") == "tap":
                    x, y = ev["x"], ev["y"]
                    cmd = ["idb", "ui", "tap", str(x), str(y), "--udid", UDID]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                    
                    if result.returncode == 0:
                        logger.info(f"Screenshot tap: ({x}, {y})")
                        
                        # Invalidate cache and get fresh screenshot faster
                        global frame_buffer_time
                        frame_buffer_time = 0
                        
                        await asyncio.sleep(0.1)  # Reduced delay
                        screenshot_result = await capture_frame_optimized()
                        if screenshot_result:
                            await ws.send_text(json.dumps({
                                "type": "screenshot",
                                "data": screenshot_result["data"],
                                "pixel_width": screenshot_result.get("pixel_width", 0),
                                "pixel_height": screenshot_result.get("pixel_height", 0),
                                "point_width": screenshot_result.get("point_width", 390),
                                "point_height": screenshot_result.get("point_height", 844),
                                "format": screenshot_result.get("format", "png")
                            }))
                    else:
                        logger.error(f"Screenshot tap failed: {result.stderr}")
                        
                elif ev.get("t") == "refresh":
                    frame_buffer_time = 0  # Force fresh screenshot
                    screenshot_result = await capture_frame_optimized()
                    if screenshot_result:
                        await ws.send_text(json.dumps({
                            "type": "screenshot",
                            "data": screenshot_result["data"],
                            "pixel_width": screenshot_result.get("pixel_width", 0),
                            "pixel_height": screenshot_result.get("pixel_height", 0),
                            "point_width": screenshot_result.get("point_width", 390),
                            "point_height": screenshot_result.get("point_height", 844),
                            "format": screenshot_result.get("format", "png")
                        }))
                        
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Message handling error: {e}")
                
    except WebSocketDisconnect:
        logger.info("Screenshot WebSocket disconnected")

# Keep all your existing endpoints unchanged...
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
    
    frame_test = await capture_frame_optimized()
    
    return {
        "udid": UDID,
        "simulator_accessible": simulator_accessible,
        "frame_working": frame_test is not None,
        "video_clients": len(video_clients),
        "cache_age": time.time() - frame_buffer_time if frame_buffer_time > 0 else 0,
        "status": "healthy" if simulator_accessible and frame_test else "unhealthy"
    }

@app.get("/debug/screenshot")
async def debug_screenshot():
    frame = await capture_frame_optimized()
    return {
        "success": frame is not None,
        "data_length": len(frame["data"]) if frame else 0,
        "dimensions": f"{frame['pixel_width']}x{frame['pixel_height']}" if frame else "unknown",
        "cache_age": time.time() - frame_buffer_time if frame_buffer_time > 0 else 0,
        "format": frame.get("format", "unknown") if frame else "unknown"
    }

@app.get("/debug/tap/{x}/{y}")
async def debug_tap(x: int, y: int) -> Dict[str, Any]:
    """Debug endpoint to test tapping at specific coordinates"""
    # Validate coordinates
    if x < 0 or y < 0:
        return {
            "success": False,
            "error": "Coordinates must be non-negative"
        }
    
    try:
        cmd = ["idb", "ui", "tap", str(x), str(y), "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # Invalidate cache after tap
        global screenshot_cache_time
        screenshot_cache_time = 0
        
        # Log the operation for debugging
        logging.info(f"Tap executed at ({x}, {y}) with exit code: {result.returncode}")
        
        return {
            "success": result.returncode == 0,
            "coordinates": {"x": x, "y": y},
            "command": " ".join(cmd),
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out after 10 seconds"
        }
    except Exception as e:
        logging.error(f"Tap command failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
     
# Replace the debug button endpoints:

@app.get("/debug/home")
async def debug_home():
    """Press home button"""
    try:
        cmd = ["idb", "ui", "button", "HOME", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        global screenshot_cache_time
        screenshot_cache_time = 0  # Invalidate cache
        
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
    """Lock device"""
    try:
        cmd = ["idb", "ui", "button", "LOCK", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        global screenshot_cache_time
        screenshot_cache_time = 0
        
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
    """Activate Siri"""
    try:
        cmd = ["idb", "ui", "button", "SIRI", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        global screenshot_cache_time
        screenshot_cache_time = 0
        
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/debug/side-button")
async def debug_side_button():
    """Press side button"""
    try:
        cmd = ["idb", "ui", "button", "SIDE_BUTTON", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        global screenshot_cache_time
        screenshot_cache_time = 0
        
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/debug/apple-pay")
async def debug_apple_pay():
    """Activate Apple Pay"""
    try:
        cmd = ["idb", "ui", "button", "APPLE_PAY", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        global screenshot_cache_time
        screenshot_cache_time = 0
        
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Add these alternative volume control endpoints:

@app.get("/debug/volume-up")
async def debug_volume_up():
    """Volume up using key press"""
    try:
        # Try using key event instead of button
        cmd = ["idb", "ui", "key", "VolumeUp", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            # Fallback: try simctl if available
            cmd = ["xcrun", "simctl", "spawn", UDID, "osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "note": "Volume control may not work in simulator"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/debug/volume-down")
async def debug_volume_down():
    """Volume down using key press"""
    try:
        # Try using key event instead of button
        cmd = ["idb", "ui", "key", "VolumeDown", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            # Fallback: try simctl if available
            cmd = ["xcrun", "simctl", "spawn", UDID, "osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "note": "Volume control may not work in simulator"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/debug/shake")
async def debug_shake():
    """Shake device using accelerometer simulation"""
    try:
        # Use simctl for shake since idb doesn't support it as a button
        cmd = ["xcrun", "simctl", "spawn", UDID, "xcrun", "simctl", "shake", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            # Alternative: try idb if it supports shake
            cmd = ["idb", "ui", "shake", "--udid", UDID]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        global screenshot_cache_time
        screenshot_cache_time = 0
        
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
    uvicorn.run(app, host="0.0.0.0", port=8000)