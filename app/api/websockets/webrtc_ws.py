import json
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logging import logger
from app.services.webrtc_service import WebRTCService
from app.models.events import WebRTCOffer, WebRTCIceCandidate

class WebRTCWebSocket:
    def __init__(self, webrtc_service: WebRTCService):
        self.webrtc_service = webrtc_service
    
    async def handle_connection(self, websocket: WebSocket):
        """Handle WebRTC signaling WebSocket"""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        logger.info(f"WebRTC signaling connected: {connection_id}")
        
        try:
            # Start capture if not already running
            if not self.webrtc_service.webrtc_active:
                self.webrtc_service.start_webrtc_capture()
            
            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                    await self._handle_webrtc_message(websocket, connection_id, data)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in WebRTC message")
                except Exception as e:
                    logger.error(f"WebRTC message handling error: {e}")
                    
        except Exception as e:
            logger.error(f"WebRTC signaling error: {e}")
        finally:
            # Clean up connection
            self.webrtc_service.remove_connection(connection_id)
            logger.info(f"WebRTC signaling disconnected: {connection_id}")
    
    async def _handle_webrtc_message(self, websocket: WebSocket, connection_id: str, data: dict):
        """Handle WebRTC signaling messages"""
        message_type = data.get("type")
        
        if message_type == "offer":
            # Create new peer connection
            conn_id, pc = await self.webrtc_service.create_peer_connection()
            
            # Handle the offer
            answer = await self.webrtc_service.handle_offer(pc, data)
            
            # Send answer back
            await websocket.send_text(json.dumps(answer))
            
        elif message_type == "ice-candidate":
            # Get existing connection
            if connection_id in self.webrtc_service.webrtc_connections:
                pc = self.webrtc_service.webrtc_connections[connection_id]
                await self.webrtc_service.handle_ice_candidate(pc, data)