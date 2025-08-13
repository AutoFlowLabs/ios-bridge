import signal
import atexit
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.websockets.log_handler_ws import handle_log_websocket
from app.config.settings import settings
from app.core.logging import logger
from app.services.video_service import VideoService
from app.services.device_service import DeviceService
from app.services.screenshot_service import ScreenshotService
from app.services.session_manager import session_manager
from app.api.routes import debug, session_routes
from app.api.websockets.control_ws import ControlWebSocket
from app.api.websockets.video_ws import VideoWebSocket
from app.api.websockets.screenshot_ws import ScreenshotWebSocket
from app.api.websockets.webrtc_ws import WebRTCWebSocket
from app.services.fast_webrtc_service import FastWebRTCService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")
    try:
        # Trigger orphaned simulator recovery on startup
        logger.info("Performing orphaned simulator recovery...")
        session_manager._recover_orphaned_simulators()
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    cleanup()

app = FastAPI(title="iOS Remote Control", version="1.0.0", lifespan=lifespan)

# Templates
templates = Jinja2Templates(directory="templates")

# Static files
import os
os.makedirs(settings.STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Include routers
app.include_router(debug.router)
app.include_router(session_routes.router)

# Initialize WebSocket handlers
control_ws = ControlWebSocket()

# WebSocket endpoints with session_id
@app.websocket("/ws/{session_id}/control")
async def control_websocket(websocket: WebSocket, session_id: str):
    """Control WebSocket endpoint"""
    try:
        await control_ws.handle_connection(websocket, session_id)
    except WebSocketDisconnect:
        logger.info(f"Control WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"Control WebSocket error for session {session_id}: {e}")

@app.websocket("/ws/{session_id}/video")
async def video_websocket(websocket: WebSocket, session_id: str):
    """Video WebSocket endpoint"""
    try:
        # Validate session exists first
        udid = session_manager.get_session_udid(session_id)
        if not udid:
            await websocket.accept()
            await websocket.close(code=4004, reason="Session not found")
            return
        
        # Create services for this session
        video_service = VideoService(udid)
        device_service = DeviceService(udid)
        
        # Start video capture for this session
        if not video_service.start_video_capture():
            logger.error(f"Failed to start video capture for session {session_id}")
            await websocket.accept()
            await websocket.close(code=4003, reason="Failed to start video capture")
            return
        
        video_ws = VideoWebSocket(video_service, device_service)
        
        # Handle the connection
        await video_ws.handle_connection(websocket)
        
    except WebSocketDisconnect:
        logger.info(f"Video WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"Video WebSocket error for session {session_id}: {e}")

@app.websocket("/ws/{session_id}/webrtc")
async def webrtc_websocket(websocket: WebSocket, session_id: str):
    """WebRTC WebSocket endpoint - Real-time streaming using idb video-stream"""
    try:
        # Validate session exists first
        udid = session_manager.get_session_udid(session_id)
        if not udid:
            await websocket.accept()
            await websocket.close(code=4004, reason="Session not found")
            return
        
        # Create fast WebRTC service for this session
        webrtc_service = FastWebRTCService(udid)
        webrtc_ws = WebRTCWebSocket(webrtc_service)
        
        # Handle the connection
        await webrtc_ws.handle_connection(websocket)
        
    except WebSocketDisconnect:
        logger.info(f"WebRTC WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebRTC WebSocket error for session {session_id}: {e}")

@app.websocket("/ws/{session_id}/screenshot")
async def screenshot_websocket(websocket: WebSocket, session_id: str):
    """Screenshot WebSocket endpoint"""
    try:
        # Validate session exists first
        udid = session_manager.get_session_udid(session_id)
        if not udid:
            await websocket.accept()
            await websocket.close(code=4004, reason="Session not found")
            return
        
        # Create services for this session
        device_service = DeviceService(udid)
        screenshot_service = ScreenshotService(udid)
        screenshot_ws = ScreenshotWebSocket(device_service, screenshot_service)
        
        # Handle the connection (only call this once!)
        await screenshot_ws.handle_connection(websocket)
        
    except WebSocketDisconnect:
        logger.info(f"Screenshot WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"Screenshot WebSocket error for session {session_id}: {e}")


@app.websocket("/ws/{session_id}/logs")
async def logs_websocket(websocket: WebSocket, session_id: str):
    """Logs WebSocket endpoint"""
    try:
        await handle_log_websocket(websocket, session_id)
    except WebSocketDisconnect:
        logger.info(f"Logs WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"Logs WebSocket error for session {session_id}: {e}")

# HTTP endpoints
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page - session list"""
    return templates.TemplateResponse("session_list.html", {"request": request})

@app.get("/control/{session_id}", response_class=HTMLResponse)
async def control_page(request: Request, session_id: str):
    """Control page for a specific session"""
    # Verify session exists
    session_info = session_manager.get_session_info(session_id)
    if not session_info:
        return HTMLResponse("Session not found", status_code=404)
    
    return templates.TemplateResponse("control.html", {
        "request": request,
        "session_id": session_id,
        "session_info": session_info
    })

@app.get("/status/{session_id}")
async def get_status(session_id: str):
    """Get session status"""
    try:
        session_info = session_manager.get_session_info(session_id)
        if not session_info:
            return {"error": "Session not found", "status_code": 404}
        
        udid = session_manager.get_session_udid(session_id)
        device_service = DeviceService(udid) if udid else None
        simulator_accessible = await device_service.is_accessible() if device_service else False
        
        return {
            "session_id": session_id,
            "udid": udid,
            "simulator_accessible": simulator_accessible,
            "session_info": session_info,
            "status": "healthy" if simulator_accessible else "offline"
        }
    except Exception as e:
        logger.error(f"Error getting status for session {session_id}: {e}")
        return {"error": str(e), "status_code": 500}

@app.get("/webrtc/quality/{session_id}/{quality}")
async def set_webrtc_quality(session_id: str, quality: str):
    """Set WebRTC quality preset for a specific session"""
    try:
        udid = session_manager.get_session_udid(session_id)
        if not udid:
            return {"success": False, "error": "Session not found"}
        
        # Fast WebRTC presets (optimized screenshots with good latency)
        presets = {
            "low": {"fps": 45, "resolution": "234x507", "quality": "good"},
            "medium": {"fps": 60, "resolution": "312x675", "quality": "better"},
            "high": {"fps": 75, "resolution": "390x844", "quality": "high"},
            "ultra": {"fps": 90, "resolution": "468x1014", "quality": "best"}
        }
        
        if quality in presets:
            return {
                "success": True, 
                "session_id": session_id,
                "quality": quality, 
                "settings": presets[quality]
            }
        else:
            return {"success": False, "error": "Invalid quality preset"}
            
    except Exception as e:
        logger.error(f"Error setting WebRTC quality for session {session_id}: {e}")
        return {"success": False, "error": str(e)}

# Legacy endpoints for backward compatibility (if needed)
@app.get("/status")
async def get_legacy_status():
    """Legacy status endpoint - shows all sessions"""
    try:
        sessions = session_manager.list_sessions()
        return {
            "total_sessions": len(sessions),
            "sessions": sessions,
            "status": "healthy" if sessions else "no_sessions"
        }
    except Exception as e:
        logger.error(f"Error getting legacy status: {e}")
        return {"error": str(e)}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "iOS Remote Control",
        "total_sessions": len(session_manager.list_sessions())
    }

# Cleanup
def cleanup():
    """Cleanup on shutdown"""
    logger.info("Cleaning up services...")
    try:
        # Cleanup any active recordings
        session_manager.cleanup_all_recordings()
        logger.info("All recordings cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during recording cleanup: {e}")
    # try:
    #     session_manager.delete_all_sessions()
    #     logger.info("All sessions cleaned up successfully")
    # except Exception as e:
    #     logger.error(f"Error during cleanup: {e}")

atexit.register(cleanup)
signal.signal(signal.SIGTERM, lambda sig, frame: cleanup())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level=settings.LOG_LEVEL.lower())