import json
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logging import logger
from app.services.device_service import DeviceService
from app.models.events import TapEvent, SwipeEvent, TextEvent, ButtonEvent

class ControlWebSocket:
    def __init__(self):
        self.device_service = DeviceService()
    
    async def handle_connection(self, websocket: WebSocket):
        """Handle control WebSocket connection"""
        await websocket.accept()
        logger.info("Control WebSocket connected")
        
        try:
            while True:
                message = await websocket.receive_text()
                await self._handle_message(message)
                
        except WebSocketDisconnect:
            logger.info("Control WebSocket disconnected")
        except Exception as e:
            logger.error(f"Control WebSocket error: {e}")
    
    async def _handle_message(self, message: str):
        """Handle incoming control messages"""
        try:
            data = json.loads(message)
            event_type = data.get("t")
            
            if event_type == "tap":
                event = TapEvent(**data)
                await self.device_service.tap(event.x, event.y)
                
            elif event_type == "swipe":
                event = SwipeEvent(**data)
                await self.device_service.swipe(
                    event.start_x, event.start_y,
                    event.end_x, event.end_y,
                    event.duration
                )
                
            elif event_type == "text":
                event = TextEvent(**data)
                await self.device_service.input_text(event.text)
                
            elif event_type == "button":
                event = ButtonEvent(**data)
                await self.device_service.press_button(event.button)
                
        except Exception as e:
            logger.error(f"Message handling error: {e}")