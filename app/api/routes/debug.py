from fastapi import APIRouter, HTTPException
from app.services.device_service import DeviceService
from app.services.screenshot_service import ScreenshotService
from app.services.session_manager import session_manager

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/screenshot/{session_id}")
async def debug_screenshot(session_id: str):
    """Debug screenshot endpoint for a specific session"""
    udid = session_manager.get_session_udid(session_id)
    if not udid:
        raise HTTPException(status_code=404, detail="Session not found")
    
    screenshot_service = ScreenshotService(udid)
    screenshot = screenshot_service.capture_screenshot()
    return {
        "success": screenshot is not None,
        "session_id": session_id,
        "udid": udid,
        "data_length": len(screenshot["data"]) if screenshot else 0,
        "dimensions": f"{screenshot['pixel_width']}x{screenshot['pixel_height']}" if screenshot else "unknown",
        "format": "jpeg" if screenshot else "unknown"
    }

@router.get("/tap/{session_id}/{x}/{y}")
async def debug_tap(session_id: str, x: int, y: int):
    """Debug tap endpoint for a specific session"""
    udid = session_manager.get_session_udid(session_id)
    if not udid:
        raise HTTPException(status_code=404, detail="Session not found")
    
    device_service = DeviceService(udid)
    success = await device_service.tap(x, y)
    return {"success": success, "session_id": session_id, "udid": udid, "x": x, "y": y}

@router.get("/home/{session_id}")
async def debug_home(session_id: str):
    """Debug home button for a specific session"""
    udid = session_manager.get_session_udid(session_id)
    if not udid:
        raise HTTPException(status_code=404, detail="Session not found")
    
    device_service = DeviceService(udid)
    success = await device_service.press_button("home")
    return {"success": success, "session_id": session_id, "udid": udid, "button": "home"}

@router.get("/lock/{session_id}")
async def debug_lock(session_id: str):
    """Debug lock button for a specific session"""
    udid = session_manager.get_session_udid(session_id)
    if not udid:
        raise HTTPException(status_code=404, detail="Session not found")
    
    device_service = DeviceService(udid)
    success = await device_service.press_button("lock")
    return {"success": success, "session_id": session_id, "udid": udid, "button": "lock"}

@router.get("/siri/{session_id}")
async def debug_siri(session_id: str):
    """Debug siri button for a specific session"""
    udid = session_manager.get_session_udid(session_id)
    if not udid:
        raise HTTPException(status_code=404, detail="Session not found")
    
    device_service = DeviceService(udid)
    success = await device_service.press_button("siri")
    return {"success": success, "session_id": session_id, "udid": udid, "button": "siri"}