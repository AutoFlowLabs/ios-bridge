import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logging import logger
from app.services.fast_webrtc_service import FastWebRTCService

class WebRTCWebSocket:
    """WebSocket handler for ultra low-latency WebRTC video streaming"""
    
    def __init__(self, webrtc_service: FastWebRTCService):
        self.webrtc_service = webrtc_service
        self.active_connections = {}
    
    async def handle_connection(self, websocket: WebSocket):
        """Handle WebRTC signaling WebSocket for real-time streaming"""
        # WebSocket is already accepted in the route handler - don't accept again
        connection_id = f"realtime_{id(websocket)}"
        
        logger.info(f"Real-time WebRTC signaling connected: {connection_id}")
        
        self.active_connections[connection_id] = {
            "websocket": websocket,
            "peer_connection": None,
            "start_time": asyncio.get_event_loop().time()
        }
        
        try:
            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                    await self._handle_signaling_message(websocket, connection_id, data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in real-time WebRTC message: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                except Exception as e:
                    logger.error(f"Real-time WebRTC message handling error: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error", 
                        "message": str(e)
                    }))
                    
        except WebSocketDisconnect:
            logger.info(f"Real-time WebRTC client disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"Real-time WebRTC signaling error: {e}")
        finally:
            await self._cleanup_connection(connection_id)
    
    async def _handle_signaling_message(self, websocket: WebSocket, connection_id: str, data: dict):
        """Handle WebRTC signaling messages for real-time streaming"""
        message_type = data.get("type")
        
        if message_type == "start-stream":
            # Initialize real-time streaming
            quality = data.get("quality", "medium")
            fps = data.get("fps", 30)
            
            try:
                # Start the video stream
                success = self.webrtc_service.start_video_stream(quality, fps)
                
                if success:
                    await websocket.send_text(json.dumps({
                        "type": "stream-ready",
                        "quality": quality,
                        "fps": fps,
                        "message": "Real-time video stream initialized"
                    }))
                    logger.info(f"Real-time stream started for {connection_id}: {quality}@{fps}fps")
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Failed to start real-time video stream"
                    }))
                    
            except Exception as e:
                logger.error(f"Error starting real-time stream: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Stream initialization failed: {str(e)}"
                }))
        
        elif message_type == "offer":
            # Handle WebRTC offer for real-time streaming
            try:
                conn_id, pc = await self.webrtc_service.create_peer_connection()
                
                # Store peer connection reference
                self.active_connections[connection_id]["peer_connection"] = (conn_id, pc)
                
                # Handle the offer
                answer = await self.webrtc_service.handle_offer(pc, data)
                
                # Send answer back
                response = {
                    "type": "answer",
                    "sdp": answer["sdp"],
                    "connection_id": conn_id
                }
                await websocket.send_text(json.dumps(response))
                
                logger.info(f"WebRTC offer handled for {connection_id}, created peer connection: {conn_id}")
                
            except Exception as e:
                logger.error(f"Error handling WebRTC offer: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Offer handling failed: {str(e)}"
                }))
        
        elif message_type == "ice-candidate":
            # Handle ICE candidate
            conn_info = self.active_connections[connection_id].get("peer_connection")
            if conn_info:
                conn_id, pc = conn_info
                try:
                    await self.webrtc_service.handle_ice_candidate(pc, data)
                    logger.debug(f"ICE candidate processed for {connection_id}")
                except Exception as e:
                    logger.error(f"Error handling ICE candidate: {e}")
            else:
                logger.warning(f"No peer connection found for ICE candidate from {connection_id}")
        
        elif message_type == "quality-change":
            # Change streaming quality in real-time
            quality = data.get("quality", "medium")
            try:
                result = self.webrtc_service.set_quality(quality)
                await websocket.send_text(json.dumps({
                    "type": "quality-changed",
                    "result": result
                }))
                logger.info(f"Quality changed to {quality} for {connection_id}")
            except Exception as e:
                logger.error(f"Error changing quality: {e}")
        
        elif message_type == "fps-change":
            # Change FPS in real-time
            fps = data.get("fps", 30)
            try:
                result = self.webrtc_service.set_fps(fps)
                await websocket.send_text(json.dumps({
                    "type": "fps-changed",
                    "result": result
                }))
                logger.info(f"FPS changed to {fps} for {connection_id}")
            except Exception as e:
                logger.error(f"Error changing FPS: {e}")
        
        elif message_type == "get-status":
            # Get streaming status
            try:
                status = self.webrtc_service.get_status()
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "data": status
                }))
            except Exception as e:
                logger.error(f"Error getting status: {e}")
        
        elif message_type == "stop-stream":
            # Stop real-time streaming
            try:
                self.webrtc_service.stop_video_stream()
                await websocket.send_text(json.dumps({
                    "type": "stream-stopped",
                    "message": "Real-time video stream stopped"
                }))
                logger.info(f"Real-time stream stopped for {connection_id}")
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")
        
        else:
            logger.warning(f"Unknown message type: {message_type} from {connection_id}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }))
    
    async def _cleanup_connection(self, connection_id: str):
        """Clean up connection and associated resources"""
        if connection_id in self.active_connections:
            conn_info = self.active_connections[connection_id]
            
            # Clean up peer connection
            if conn_info.get("peer_connection"):
                peer_conn_id, pc = conn_info["peer_connection"]
                try:
                    self.webrtc_service.remove_connection(peer_conn_id)
                    await pc.close()
                    logger.info(f"Cleaned up peer connection: {peer_conn_id}")
                except Exception as e:
                    logger.error(f"Error cleaning up peer connection: {e}")
            
            # Remove from active connections
            del self.active_connections[connection_id]
            logger.info(f"Real-time WebRTC connection cleaned up: {connection_id}")
    
    def get_connection_stats(self) -> dict:
        """Get statistics about active connections"""
        current_time = asyncio.get_event_loop().time()
        stats = {
            "total_connections": len(self.active_connections),
            "connections": []
        }
        
        for conn_id, conn_info in self.active_connections.items():
            stats["connections"].append({
                "id": conn_id,
                "duration": current_time - conn_info["start_time"],
                "has_peer_connection": conn_info.get("peer_connection") is not None
            })
        
        return stats