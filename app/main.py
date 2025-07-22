import signal
import atexit
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config.settings import settings
from app.core.logging import logger
from app.services.video_service import VideoService
from app.services.webrtc_service import WebRTCService
from app.services.device_service import DeviceService
from app.services.screenshot_service import ScreenshotService
from app.api.routes import debug
from app.api.websockets.control_ws import ControlWebSocket
from app.api.websockets.video_ws import VideoWebSocket
from app.api.websockets.webrtc_ws import WebRTCWebSocket
from app.api.websockets.screenshot_ws import ScreenshotWebSocket

# Initialize services
video_service = VideoService()
webrtc_service = WebRTCService()
device_service = DeviceService()
screenshot_service = ScreenshotService()

# Initialize WebSocket handlers
control_ws = ControlWebSocket()
video_ws = VideoWebSocket(video_service)
webrtc_ws = WebRTCWebSocket(webrtc_service)
screenshot_ws = ScreenshotWebSocket(device_service, screenshot_service)

app = FastAPI(title="iOS Remote Control", version="1.0.0")

# Static files
import os
os.makedirs(settings.STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Include routers
app.include_router(debug.router)

# WebSocket endpoints
@app.websocket("/ws/control")
async def control_websocket(websocket: WebSocket):
    try:
        await control_ws.handle_connection(websocket)
    except WebSocketDisconnect:
        logger.info("Control WebSocket disconnected")
    except Exception as e:
        logger.error(f"Control WebSocket error: {e}")

@app.websocket("/ws/video")
async def video_websocket(websocket: WebSocket):
    try:
        await video_ws.handle_connection(websocket)
    except WebSocketDisconnect:
        logger.info("Video WebSocket disconnected")
    except Exception as e:
        logger.error(f"Video WebSocket error: {e}")

@app.websocket("/ws/webrtc")
async def webrtc_websocket(websocket: WebSocket):
    try:
        await webrtc_ws.handle_connection(websocket)
    except WebSocketDisconnect:
        logger.info("WebRTC WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebRTC WebSocket error: {e}")

@app.websocket("/ws/screenshot")
async def screenshot_websocket(websocket: WebSocket):
    try:
        await screenshot_ws.handle_connection(websocket)
    except WebSocketDisconnect:
        logger.info("Screenshot WebSocket disconnected")
    except Exception as e:
        logger.error(f"Screenshot WebSocket error: {e}")

# HTTP endpoints
@app.get("/")
def index():
    return FileResponse(f"{settings.STATIC_DIR}/index.html")

@app.get("/status")
async def get_status():
    """Get application status"""
    simulator_accessible = await device_service.is_accessible()
    video_status = video_service.get_status()
    webrtc_status = webrtc_service.get_status()
    
    return {
        "udid": settings.UDID,
        "simulator_accessible": simulator_accessible,
        **video_status,
        **webrtc_status,
        "status": "healthy" if (video_status["video_streaming"] or webrtc_status["webrtc_active"]) else "starting"
    }

@app.get("/webrtc/quality/{quality}")
async def set_webrtc_quality(quality: str):
    """Set WebRTC quality preset"""
    return webrtc_service.set_quality_preset(quality)

# Cleanup
def cleanup():
    """Cleanup on shutdown"""
    logger.info("Cleaning up services...")
    video_service.stop_video_capture()
    webrtc_service.stop_webrtc_capture()

atexit.register(cleanup)
signal.signal(signal.SIGTERM, lambda s, f: cleanup())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level=settings.LOG_LEVEL.lower())