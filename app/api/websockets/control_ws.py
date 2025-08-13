import json
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logging import logger
from app.services.device_service import DeviceService
from app.services.session_manager import session_manager
from app.models.events import TapEvent, SwipeEvent, TextEvent, ButtonEvent, KeyEvent

class ControlWebSocket:
    def __init__(self):
        self.device_services = {}  # session_id -> DeviceService
    
    async def handle_connection(self, websocket: WebSocket, session_id: str):
        """Handle control WebSocket connection for a specific session"""
        await websocket.accept()
        # logger.info(f"Control WebSocket connected for session: {session_id}")
        
        # Get UDID for this session
        udid = session_manager.get_session_udid(session_id)
        if not udid:
            await websocket.close(code=4004, reason="Session not found")
            return
        
        # Create device service for this session
        device_service = DeviceService(udid)
        self.device_services[session_id] = device_service
        
        try:
            while True:
                message = await websocket.receive_text()
                await self._handle_message(device_service, message)
                
        except WebSocketDisconnect:
            logger.info(f"Control WebSocket disconnected for session: {session_id}")
        except Exception as e:
            logger.error(f"Control WebSocket error for session {session_id}: {e}")
        finally:
            if session_id in self.device_services:
                del self.device_services[session_id]
    
    async def _handle_message(self, device_service: DeviceService, message: str):
        """Handle incoming control messages"""
        try:
            data = json.loads(message)
            event_type = data.get("t")
            
            if event_type == "tap":
                event = TapEvent(**data)
                await device_service.tap(event.x, event.y)
                
            elif event_type == "swipe":
                event = SwipeEvent(**data)
                await device_service.swipe(
                    event.start_x, event.start_y,
                    event.end_x, event.end_y,
                    event.duration
                )
                
            elif event_type == "text":
                event = TextEvent(**data)
                await device_service.input_text(event.text)
                
            elif event_type == "button":
                event = ButtonEvent(**data)
                await device_service.press_button(event.button)
                
            elif event_type == "key":
                event = KeyEvent(**data)
                await device_service.input_key(event.key, event.duration)
                
        except Exception as e:
            logger.error(f"Message handling error: {e}")