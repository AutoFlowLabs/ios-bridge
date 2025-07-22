from fastapi import APIRouter
from app.services.device_service import DeviceService
from app.services.screenshot_service import ScreenshotService

router = APIRouter(prefix="/debug", tags=["debug"])

device_service = DeviceService()
screenshot_service = ScreenshotService()

@router.get("/screenshot")
async def debug_screenshot():
    """Debug screenshot endpoint"""
    screenshot = screenshot_service.capture_screenshot()
    return {
        "success": screenshot is not None,
        "data_length": len(screenshot["data"]) if screenshot else 0,
        "dimensions": f"{screenshot['pixel_width']}x{screenshot['pixel_height']}" if screenshot else "unknown",
        "format": "jpeg" if screenshot else "unknown"
    }

@router.get("/tap/{x}/{y}")
async def debug_tap(x: int, y: int):
    """Debug tap endpoint"""
    success = await device_service.tap(x, y)
    return {"success": success, "x": x, "y": y}

@router.get("/home")
async def debug_home():
    """Debug home button"""
    success = await device_service.press_button("home")
    return {"success": success, "button": "home"}

@router.get("/lock")
async def debug_lock():
    """Debug lock button"""
    success = await device_service.press_button("lock")
    return {"success": success, "button": "lock"}

@router.get("/siri")
async def debug_siri():
    """Debug siri button"""
    success = await device_service.press_button("siri")
    return {"success": success, "button": "siri"}