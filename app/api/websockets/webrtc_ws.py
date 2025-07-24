import json
import time
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logging import logger
from app.services.webrtc_service import WebRTCService
from app.models.events import WebRTCOffer, WebRTCIceCandidate
import asyncio 

class WebRTCWebSocket:
    def __init__(self, webrtc_service: WebRTCService):
        self.webrtc_service = webrtc_service
        self.active_connections = {}  # Track connection mapping
    
    async def handle_connection(self, websocket: WebSocket):
        """Handle WebRTC signaling WebSocket with ultra-optimized idb streaming"""
        await websocket.accept()
        websocket_id = str(uuid.uuid4())
        logger.info(f"🔵 WebRTC signaling connected: {websocket_id}")
        
        try:
            # Ensure video stream is running with ultra optimization
            if not self.webrtc_service.stream_active:
                logger.info("📹 Starting video stream for WebRTC...")
                success = self.webrtc_service.start_video_stream()
                if not success:
                    logger.error("❌ Failed to start video stream")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "Failed to start video stream",
                        "code": "STREAM_START_FAILED"
                    }))
                    await websocket.close(code=1000, reason="Stream start failed")
                    return
                else:
                    logger.info("✅ Video stream started successfully")
            else:
                logger.info("📹 Video stream already active")
            
            # Wait a moment for stream to stabilize
            import asyncio
            await asyncio.sleep(0.1)
            
            logger.info("⏳ Waiting for initial frames...")
            frames_available = False
            
            for i in range(30):  # Wait up to 3 seconds for initial frames
                await asyncio.sleep(0.1)
                current_frame = self.webrtc_service.get_latest_frame()
                if current_frame is not None:
                    frames_available = True
                    logger.info(f"✅ Initial frames available after {(i+1)*100}ms")
                    break
            
            # Check if we have frames
            frame_status = "available" if frames_available else "not available"
            logger.info(f"📊 Current frame status: {frame_status}")
            
            # Send initial status with more details
            status_message = {
                "type": "status",
                "message": "Ultra-optimized video stream ready",
                "stream_active": self.webrtc_service.stream_active,
                "webrtc_active": self.webrtc_service.webrtc_active,
                "quality_settings": self.webrtc_service.quality_settings,
                "frame_available": current_frame is not None,
                "udid": self.webrtc_service.udid,
                "ready_for_connection": True
            }
            
            await websocket.send_text(json.dumps(status_message))
            logger.info(f"📤 Sent initial status to WebRTC client: {websocket_id}")
            
            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                    logger.info(f"📨 Received WebRTC message: type={data.get('type')} from {websocket_id}")
                    await self._handle_webrtc_message(websocket, websocket_id, data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in WebRTC message: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "Invalid JSON format",
                        "code": "JSON_DECODE_ERROR"
                    }))
                except Exception as e:
                    logger.error(f"WebRTC message handling error: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": str(e),
                        "code": "MESSAGE_HANDLING_ERROR"
                    }))
                    
        except WebSocketDisconnect:
            logger.info(f"🔴 WebRTC WebSocket disconnected: {websocket_id}")
        except Exception as e:
            logger.error(f"❌ WebRTC signaling error: {e}")
        finally:
            # Clean up connections
            await self._cleanup_websocket_connections(websocket_id)
            logger.info(f"🧹 WebRTC signaling cleanup completed: {websocket_id}")
    
    async def _handle_webrtc_message(self, websocket: WebSocket, websocket_id: str, data: dict):
        """Handle WebRTC signaling messages with enhanced error handling"""
        message_type = data.get("type")
        
        try:
            if message_type == "offer":
                logger.info(f"🤝 Handling WebRTC offer from {websocket_id}")
                await self._handle_offer(websocket, websocket_id, data)
            
            elif message_type == "ice-candidate":
                logger.debug(f"🧊 Handling ICE candidate from {websocket_id}")
                await self._handle_ice_candidate(websocket, websocket_id, data)
            
            elif message_type == "quality-change":
                logger.info(f"⚙️ Handling quality change from {websocket_id}")
                await self._handle_quality_change(websocket, data)
            
            elif message_type == "optimize":
                logger.info(f"🚀 Handling optimization request from {websocket_id}")
                await self._handle_optimization_request(websocket, data)
            
            elif message_type == "status-request":
                logger.debug(f"📊 Handling status request from {websocket_id}")
                await self._handle_status_request(websocket)
            
            elif message_type == "debug-request":
                logger.info(f"🐛 Handling debug request from {websocket_id}")
                await self._handle_debug_request(websocket)
            
            elif message_type == "stream-debug":
                logger.info(f"🔍 Handling stream debug request from {websocket_id}")
                await self._handle_stream_debug(websocket)
            
            else:
                logger.warning(f"❓ Unknown WebRTC message type: {message_type} from {websocket_id}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": f"Unknown message type: {message_type}",
                    "code": "UNKNOWN_MESSAGE_TYPE"
                }))
        
        except Exception as e:
            logger.error(f"❌ Error handling {message_type} message from {websocket_id}: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": str(e),
                "code": f"{message_type.upper()}_ERROR"
            }))

    async def _handle_offer(self, websocket: WebSocket, websocket_id: str, data: dict):
        """Simplified offer handler"""
        connection_id = None
        try:
            logger.info(f"🔧 Creating peer connection for {websocket_id}")
            
            # ✅ SIMPLE: Just check if we have any frame
            def has_frames():
                frame = self.webrtc_service.get_latest_frame()
                return frame is not None
            
            # ✅ SHORT wait if no frames
            if not has_frames():
                logger.info("⏳ Waiting briefly for frames...")
                
                for i in range(30):  # 3 seconds max
                    await asyncio.sleep(0.1)
                    if has_frames():
                        logger.info(f"✅ Frames available after {(i+1)*100}ms")
                        break
                else:
                    logger.warning("⚠️ No frames after 3s, proceeding anyway")
            
            # ✅ CREATE connection regardless
            logger.info("🔗 Creating peer connection...")
            connection_id, pc = await self.webrtc_service.create_peer_connection()
            self.active_connections[websocket_id] = connection_id
            
            # ✅ HANDLE offer
            offer_sdp = data.get("sdp")
            if not offer_sdp:
                raise ValueError("Missing SDP")
            
            answer = await self.webrtc_service.handle_offer(pc, {
                "sdp": offer_sdp,
                "type": "offer"
            })
            
            # ✅ SEND response
            response = {
                **answer,
                "connection_id": connection_id,
                "stream_info": {
                    "udid": self.webrtc_service.udid
                }
            }
            
            await websocket.send_text(json.dumps(response))
            logger.info(f"📤 Sent answer: {connection_id}")
            
        except Exception as e:
            logger.error(f"❌ Offer error: {e}")
            
            if connection_id and connection_id in self.webrtc_service.webrtc_connections:
                self.webrtc_service.remove_connection(connection_id)
                if websocket_id in self.active_connections:
                    del self.active_connections[websocket_id]
            
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": f"Offer failed: {str(e)}",
                "code": "OFFER_FAILED"
            }))    

    async def _handle_ice_candidate(self, websocket: WebSocket, websocket_id: str, data: dict):
        """Handle ICE candidate with connection lookup"""
        try:
            # Get connection ID for this websocket
            connection_id = self.active_connections.get(websocket_id)
            
            if not connection_id:
                logger.warning(f"❓ No connection found for websocket: {websocket_id}")
                # Send back info about available connections
                await websocket.send_text(json.dumps({
                    "type": "debug-info",
                    "message": "No connection found for ICE candidate",
                    "available_connections": list(self.active_connections.keys()),
                    "webrtc_connections": list(self.webrtc_service.webrtc_connections.keys())
                }))
                return
            
            # Get the peer connection
            if connection_id in self.webrtc_service.webrtc_connections:
                pc = self.webrtc_service.webrtc_connections[connection_id]
                
                # Log ICE candidate details
                candidate_info = data.get("candidate")
                if isinstance(candidate_info, dict):
                    candidate_str = candidate_info.get("candidate", "")
                else:
                    candidate_str = str(candidate_info) if candidate_info else ""
                
                logger.debug(f"🧊 Processing ICE candidate for {connection_id}: {candidate_str[:50]}...")
                
                await self.webrtc_service.handle_ice_candidate(pc, data)
                
                # Log connection states after ICE candidate
                logger.debug(f"📊 After ICE - Connection: {pc.connectionState}, ICE: {pc.iceConnectionState}")
                
                await websocket.send_text(json.dumps({
                    "type": "ice-candidate-processed",
                    "connection_id": connection_id,
                    "connection_state": pc.connectionState,
                    "ice_connection_state": pc.iceConnectionState
                }))
            else:
                logger.warning(f"❓ Connection not found in service: {connection_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to handle ICE candidate from {websocket_id}: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": f"Failed to handle ICE candidate: {str(e)}",
                "code": "ICE_CANDIDATE_FAILED"
            }))
    
    async def _handle_status_request(self, websocket: WebSocket):
        """Handle status information requests"""
        try:
            status = self.webrtc_service.get_status()
            
            # Add WebSocket-specific status
            status["websocket_info"] = {
                "active_websockets": len(self.active_connections),
                "connection_mapping": self.active_connections,
                "frame_available": self.webrtc_service.get_latest_frame() is not None
            }
            
            await websocket.send_text(json.dumps({
                "type": "status-response",
                **status
            }))
            
        except Exception as e:
            logger.error(f"❌ Failed to get status: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": f"Failed to get status: {str(e)}",
                "code": "STATUS_REQUEST_FAILED"
            }))
    
    # Keep the rest of your methods unchanged...
    async def _handle_quality_change(self, websocket: WebSocket, data: dict):
        """Handle quality preset changes"""
        try:
            quality = data.get("quality", "high")
            result = self.webrtc_service.set_quality_preset(quality)
            
            await websocket.send_text(json.dumps({
                "type": "quality-changed",
                **result
            }))
            
        except Exception as e:
            logger.error(f"Failed to change quality: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": f"Failed to change quality: {str(e)}",
                "code": "QUALITY_CHANGE_FAILED"
            }))
    
    async def _handle_optimization_request(self, websocket: WebSocket, data: dict):
        """Handle optimization requests (max quality, low latency, gaming, etc.)"""
        try:
            optimization_type = data.get("optimization", "balanced")
            target_latency = data.get("target_latency_ms", 100)
            
            result = {}
            
            if optimization_type == "max_quality":
                result = self.webrtc_service.enable_max_quality_mode()
            
            elif optimization_type == "ultra_low_latency":
                result = self.webrtc_service.optimize_for_latency(target_latency)
            
            elif optimization_type == "gaming":
                if hasattr(self.webrtc_service, 'optimize_for_gaming'):
                    result = self.webrtc_service.optimize_for_gaming()
                else:
                    result = self.webrtc_service.optimize_for_latency(150)  # Gaming latency
            
            elif optimization_type == "streaming":
                if hasattr(self.webrtc_service, 'optimize_for_streaming'):
                    result = self.webrtc_service.optimize_for_streaming()
                else:
                    result = self.webrtc_service.enable_max_quality_mode()
            
            else:
                result = {"success": False, "error": f"Unknown optimization: {optimization_type}"}
            
            await websocket.send_text(json.dumps({
                "type": "optimization-applied",
                "optimization": optimization_type,
                **result
            }))
            
        except Exception as e:
            logger.error(f"Failed to apply optimization: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": f"Failed to apply optimization: {str(e)}",
                "code": "OPTIMIZATION_FAILED"
            }))
    
    async def _handle_debug_request(self, websocket: WebSocket):
        """Handle debug information requests"""
        try:
            # Get comprehensive debug info
            debug_info = {
                "status": self.webrtc_service.get_status(),
                "active_websockets": len(self.active_connections),
                "websocket_connections": list(self.active_connections.keys()),
                "connection_mapping": self.active_connections,
                "frame_available": self.webrtc_service.get_latest_frame() is not None
            }
            
            # Add enhanced debug info if available
            if hasattr(self.webrtc_service, 'debug_stream_status'):
                debug_info["stream_debug"] = self.webrtc_service.debug_stream_status()
            
            if hasattr(self.webrtc_service, 'get_performance_report'):
                debug_info["performance_report"] = self.webrtc_service.get_performance_report()
            
            await websocket.send_text(json.dumps({
                "type": "debug-response",
                **debug_info
            }))
            
        except Exception as e:
            logger.error(f"Failed to get debug info: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": f"Failed to get debug info: {str(e)}",
                "code": "DEBUG_REQUEST_FAILED"
            }))
    
    async def _cleanup_websocket_connections(self, websocket_id: str):
        """Clean up connections associated with a websocket"""
        try:
            connection_id = self.active_connections.get(websocket_id)
            
            if connection_id:
                # Remove the WebRTC connection
                self.webrtc_service.remove_connection(connection_id)
                
                # Remove from our tracking
                del self.active_connections[websocket_id]
                
                logger.info(f"🧹 Cleaned up WebRTC connection: {connection_id} for websocket: {websocket_id}")
            
            # If no more active connections, optionally stop the stream
            if not self.active_connections and self.webrtc_service.stream_active:
                # Note: You might want to add a delay here to keep stream running
                # for potential reconnections
                logger.info("📹 No more WebRTC connections, keeping stream running for potential reconnections")
                pass
                
        except Exception as e:
            logger.error(f"❌ Error during WebSocket cleanup: {e}")
    
    def get_connection_count(self) -> int:
        """Get number of active WebSocket connections"""
        return len(self.active_connections)
    
    def get_connection_info(self) -> dict:
        """Get information about active connections"""
        return {
            "websocket_connections": len(self.active_connections),
            "webrtc_connections": len(self.webrtc_service.webrtc_connections),
            "stream_active": self.webrtc_service.stream_active,
            "webrtc_active": self.webrtc_service.webrtc_active,
            "quality_settings": self.webrtc_service.quality_settings,
            "frame_available": self.webrtc_service.get_latest_frame() is not None
        }
    

    # Add this method to the WebRTCWebSocket class:
    async def _handle_stream_debug(self, websocket: WebSocket):
        """Handle detailed stream debugging"""
        try:
            # Get comprehensive stream debug info
            debug_info = {
                "timestamp": time.time(),
                "stream_status": self.webrtc_service.get_status(),
                "frame_status": {
                    "current_frame_available": self.webrtc_service.get_latest_frame() is not None,
                    "frame_queue_size": len(self.webrtc_service.frame_queue) if hasattr(self.webrtc_service, 'frame_queue') else 0
                }
            }
            
            # Add detailed idb process debug info
            if hasattr(self.webrtc_service, 'debug_idb_stream'):
                debug_info["idb_stream_debug"] = self.webrtc_service.debug_idb_stream()
            
            # Test idb connection
            if hasattr(self.webrtc_service, 'test_idb_connection'):
                debug_info["idb_connection_test"] = self.webrtc_service.test_idb_connection()
            
            # Test manual idb video stream
            if hasattr(self.webrtc_service, 'test_idb_video_stream_manual'):
                debug_info["manual_stream_test"] = self.webrtc_service.test_idb_video_stream_manual()
            
            await websocket.send_text(json.dumps({
                "type": "stream-debug-response",
                **debug_info
            }))
            
        except Exception as e:
            logger.error(f"Failed to get stream debug info: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": f"Failed to get stream debug info: {str(e)}",
                "code": "STREAM_DEBUG_FAILED"
            }))