import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logging import logger
from app.services.device_service import DeviceService
from app.services.screenshot_service import ScreenshotService
from app.models.responses import ScreenshotResponse
from app.models.events import TapEvent

class ScreenshotWebSocket:
    def __init__(self, device_service: DeviceService, screenshot_service: ScreenshotService):
        self.device_service = device_service
        self.screenshot_service = screenshot_service
    
    async def handle_connection(self, websocket: WebSocket):
        """Handle screenshot mode WebSocket"""
        await websocket.accept()
        logger.info("Screenshot WebSocket connected")
        
        try:
            # Send initial screenshot
            await self._send_screenshot(websocket)
            
            async for message in websocket.iter_text():
                await self._handle_message(websocket, message)
                
        except WebSocketDisconnect:
            logger.info("Screenshot WebSocket disconnected")
        except Exception as e:
            logger.error(f"Screenshot WebSocket error: {e}")
    
    async def _handle_message(self, websocket: WebSocket, message: str):
        """Handle incoming screenshot messages"""
        try:
            data = json.loads(message)
            event_type = data.get("t")
            
            if event_type == "tap":
                event = TapEvent(**data)
                success = await self.device_service.tap(event.x, event.y)
                
                if success:
                    logger.info(f"Screenshot tap: ({event.x}, {event.y})")
                    # Wait a moment for UI to update
                    await asyncio.sleep(0.1)
                    # Send fresh screenshot
                    await self._send_screenshot(websocket)
                    
            elif event_type == "refresh":
                await self._send_screenshot(websocket)
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in screenshot WebSocket")
        except Exception as e:
            logger.error(f"Screenshot message handling error: {e}")
    
    async def _send_screenshot(self, websocket: WebSocket):
        """Send screenshot to client"""
        try:
            screenshot_data = self.screenshot_service.capture_screenshot()
            
            if screenshot_data:
                point_width, point_height = await self.device_service.get_point_dimensions()
                
                screenshot_response = ScreenshotResponse(
                    data=screenshot_data["data"],
                    pixel_width=screenshot_data.get("pixel_width", 390),
                    pixel_height=screenshot_data.get("pixel_height", 844),
                    point_width=point_width,
                    point_height=point_height
                )
                
                await websocket.send_text(screenshot_response.model_dump_json())
            else:
                logger.warning("Failed to capture screenshot")
                
        except Exception as e:
            logger.error(f"Error sending screenshot: {e}")