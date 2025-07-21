import os, subprocess, asyncio, json, base64, tempfile, signal, atexit
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import logging
import time
import struct
from concurrent.futures import ThreadPoolExecutor
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UDID = "B8BA84BA-664B-4D0D-9627-AC67F9BF0685"   

app = FastAPI()

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global variables
video_clients: List[WebSocket] = []
screenshot_cache = None
screenshot_cache_time = 0
screenshot_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=4)

def cleanup_processes():
    """Clean up background processes"""
    logger.info("Server shutdown - cleaning up...")
    executor.shutdown(wait=False)

# Register cleanup
atexit.register(cleanup_processes)
signal.signal(signal.SIGTERM, lambda s, f: cleanup_processes())

def capture_screenshot_sync():
    """Synchronous screenshot capture for thread pool"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            # Use the virtual environment idb path
            idb_path = "/Users/himanshukukreja/autoflow/ios-bridge/venv/bin/idb"
            cmd = [idb_path, "screenshot", "--udid", UDID, temp_file.name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0 and os.path.exists(temp_file.name):
                with open(temp_file.name, 'rb') as f:
                    image_data = f.read()
                os.unlink(temp_file.name)
                
                # Get image dimensions from PNG header
                try:
                    pixel_width = struct.unpack('>I', image_data[16:20])[0]
                    pixel_height = struct.unpack('>I', image_data[20:24])[0]
                except:
                    pixel_width, pixel_height = 0, 0
                
                return {
                    "data": base64.b64encode(image_data).decode('utf-8'),
                    "pixel_width": pixel_width,
                    "pixel_height": pixel_height,
                    "timestamp": time.time()
                }
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
    return None

async def capture_screenshot_optimized():
    """Optimized screenshot capture with caching"""
    global screenshot_cache, screenshot_cache_time
    
    current_time = time.time()
    
    # Use cache if less than 33ms old (30 FPS target) - reduced from 16ms for better performance
    with screenshot_lock:
        if (screenshot_cache and 
            current_time - screenshot_cache_time < 0.033):
            return screenshot_cache
    
    # Capture new screenshot in thread pool
    loop = asyncio.get_event_loop()
    screenshot_data = await loop.run_in_executor(executor, capture_screenshot_sync)
    
    if screenshot_data:
        # Get point dimensions (cache this too since it rarely changes)
        point_width, point_height = await get_point_dimensions()
        
        result = {
            **screenshot_data,
            "point_width": point_width,
            "point_height": point_height,
            "width": screenshot_data["pixel_width"],
            "height": screenshot_data["pixel_height"]
        }
        
        # Update cache
        with screenshot_lock:
            screenshot_cache = result
            screenshot_cache_time = current_time
        
        return result
    
    return screenshot_cache  # Return cached version if new capture failed

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
        idb_path = "/Users/himanshukukreja/autoflow/ios-bridge/venv/bin/idb"
        cmd = [idb_path, "describe", "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        
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


# Replace the control_ws function with this enhanced version:

# Update the control_ws function to map button names correctly:

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
                idb_path = "/Users/himanshukukreja/autoflow/ios-bridge/venv/bin/idb"
                cmd = [idb_path, "ui", "tap", str(x), str(y), "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                
                if result.returncode == 0:
                    logger.info(f"✅ Tap: ({x}, {y})")
                    global screenshot_cache_time
                    screenshot_cache_time = 0
                else:
                    logger.error(f"❌ Tap failed: {result.stderr}")
                    
            elif ev["t"] == "swipe":
                start_x, start_y = ev["start_x"], ev["start_y"]
                end_x, end_y = ev["end_x"], ev["end_y"]
                duration = ev.get("duration", 0.5)
                
                idb_path = "/Users/himanshukukreja/autoflow/ios-bridge/venv/bin/idb"
                cmd = [idb_path, "ui", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), "--duration", str(duration), "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    logger.info(f"✅ Swipe: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
                    screenshot_cache_time = 0
                else:
                    logger.error(f"❌ Swipe failed: {result.stderr}")
                    
            elif ev["t"] == "text":
                text = ev["text"]
                idb_path = "/Users/himanshukukreja/autoflow/ios-bridge/venv/bin/idb"
                cmd = [idb_path, "ui", "text", text, "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    logger.info(f"✅ Text entered: {text}")
                    screenshot_cache_time = 0
                else:
                    logger.error(f"❌ Text failed: {result.stderr}")
                    
            elif ev["t"] == "button":
                button = ev["button"]
                
                # Map button names to IDB expected values
                button_mapping = {
                    'home': 'HOME',
                    'lock': 'LOCK',
                    'siri': 'SIRI',
                    'side-button': 'SIDE_BUTTON',
                    'apple-pay': 'APPLE_PAY'
                }
                
                idb_button = button_mapping.get(button, button.upper())
                
                idb_path = "/Users/himanshukukreja/autoflow/ios-bridge/venv/bin/idb"
                cmd = [idb_path, "ui", "button", idb_button, "--udid", UDID]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                
                if result.returncode == 0:
                    logger.info(f"✅ Button pressed: {button} ({idb_button})")
                    screenshot_cache_time = 0
                else:
                    logger.error(f"❌ Button failed: {result.stderr}")
                    
    except WebSocketDisconnect:
        logger.info("Control WebSocket disconnected")

@app.websocket("/ws/video")
async def video_ws(ws: WebSocket):
    """High-performance video streaming"""
    await ws.accept()
    logger.info("Video WebSocket connected")
    
    video_clients.append(ws)
    
    try:
        frame_count = 0
        target_fps = 30
        frame_interval = 1.0 / target_fps
        last_frame_time = 0
        
        while True:
            frame_start = time.time()
            
            # Throttle to target FPS
            if frame_start - last_frame_time < frame_interval:
                sleep_time = frame_interval - (frame_start - last_frame_time)
                await asyncio.sleep(sleep_time)
                continue
            
            try:
                screenshot_result = await capture_screenshot_optimized()
                
                if screenshot_result:
                    frame_count += 1
                    
                    # Send frame data
                    frame_data = {
                        "type": "video_frame",
                        "data": screenshot_result["data"],
                        "pixel_width": screenshot_result.get("pixel_width", 0),
                        "pixel_height": screenshot_result.get("pixel_height", 0),
                        "point_width": screenshot_result.get("point_width", 390),
                        "point_height": screenshot_result.get("point_height", 844),
                        "frame": frame_count,
                        "timestamp": screenshot_result.get("timestamp", frame_start),
                        "fps": round(1.0 / (frame_start - last_frame_time)) if last_frame_time > 0 else 0
                    }
                    
                    await ws.send_text(json.dumps(frame_data))
                    
                    last_frame_time = frame_start
                    
                    if frame_count % 100 == 0:
                        actual_fps = 1.0 / (frame_start - last_frame_time) if last_frame_time > 0 else 0
                        logger.info(f"Video frame {frame_count}, FPS: {actual_fps:.1f}")
                        
            except Exception as e:
                logger.error(f"Video frame error: {e}")
                await asyncio.sleep(0.1)
            
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
        screenshot_result = await capture_screenshot_optimized()
        if screenshot_result:
            await ws.send_text(json.dumps({
                "type": "screenshot",
                "data": screenshot_result["data"],
                "pixel_width": screenshot_result.get("pixel_width", 0),
                "pixel_height": screenshot_result.get("pixel_height", 0),
                "point_width": screenshot_result.get("point_width", 390),
                "point_height": screenshot_result.get("point_height", 844)
            }))
        
        async for message in ws.iter_text():
            try:
                ev = json.loads(message)
                
                if ev.get("t") == "tap":
                    x, y = ev["x"], ev["y"]
                    cmd = ["idb", "ui", "tap", str(x), str(y), "--udid", UDID]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0:
                        logger.info(f"Screenshot tap: ({x}, {y})")
                        
                        # Invalidate cache and get fresh screenshot
                        global screenshot_cache_time
                        screenshot_cache_time = 0
                        
                        await asyncio.sleep(0.3)  # Shorter delay
                        screenshot_result = await capture_screenshot_optimized()
                        if screenshot_result:
                            await ws.send_text(json.dumps({
                                "type": "screenshot",
                                "data": screenshot_result["data"],
                                "pixel_width": screenshot_result.get("pixel_width", 0),
                                "pixel_height": screenshot_result.get("pixel_height", 0),
                                "point_width": screenshot_result.get("point_width", 390),
                                "point_height": screenshot_result.get("point_height", 844)
                            }))
                    else:
                        logger.error(f"Screenshot tap failed: {result.stderr}")
                        
                elif ev.get("t") == "refresh":
                    screenshot_cache_time = 0  # Force fresh screenshot
                    screenshot_result = await capture_screenshot_optimized()
                    if screenshot_result:
                        await ws.send_text(json.dumps({
                            "type": "screenshot",
                            "data": screenshot_result["data"],
                            "pixel_width": screenshot_result.get("pixel_width", 0),
                            "pixel_height": screenshot_result.get("pixel_height", 0),
                            "point_width": screenshot_result.get("point_width", 390),
                            "point_height": screenshot_result.get("point_height", 844)
                        }))
                        
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Message handling error: {e}")
                
    except WebSocketDisconnect:
        logger.info("Screenshot WebSocket disconnected")

@app.get("/")
def index():
    """Serve the main interface"""
    return FileResponse("static/index.html")

@app.get("/status")
async def status():
    """Get server status"""
    try:
        test_cmd = ["idb", "list-targets"]
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
        simulator_accessible = UDID in result.stdout
    except:
        simulator_accessible = False
    
    screenshot_test = await capture_screenshot_optimized()
    
    return {
        "udid": UDID,
        "simulator_accessible": simulator_accessible,
        "screenshot_working": screenshot_test is not None,
        "video_clients": len(video_clients),
        "cache_age": time.time() - screenshot_cache_time if screenshot_cache_time > 0 else 0,
        "status": "healthy" if simulator_accessible and screenshot_test else "unhealthy"
    }

@app.get("/debug/screenshot")
async def debug_screenshot():
    """Test screenshot capture"""
    screenshot = await capture_screenshot_optimized()
    return {
        "success": screenshot is not None,
        "data_length": len(screenshot["data"]) if screenshot else 0,
        "dimensions": f"{screenshot['pixel_width']}x{screenshot['pixel_height']}" if screenshot else "unknown",
        "cache_age": time.time() - screenshot_cache_time if screenshot_cache_time > 0 else 0
    }

# Keep existing debug endpoints but update them to use the optimized function
@app.get("/debug/tap/{x}/{y}")
async def debug_tap(x: int, y: int):
    """Debug endpoint to test tapping at specific coordinates"""
    try:
        cmd = ["idb", "ui", "tap", str(x), str(y), "--udid", UDID]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # Invalidate cache after tap
        global screenshot_cache_time
        screenshot_cache_time = 0
        
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except Exception as e:
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