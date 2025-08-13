import json
import time
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logging import logger
from app.services.video_service import VideoService
from app.services.device_service import DeviceService
from app.models.responses import VideoFrame

class VideoWebSocket:
    def __init__(self, video_service: VideoService, device_service: DeviceService):
        self.video_service = video_service
        self.device_service = device_service
    
    async def handle_connection(self, websocket: WebSocket):
        """Handle video WebSocket connection"""
        await websocket.accept()
        logger.info("Video WebSocket connected")
        
        await self._handle_video_streaming(websocket)
    
    async def handle_connection_managed(self, websocket: WebSocket):
        """Handle video WebSocket connection with managed resources (no websocket.accept())"""
        logger.info("Video WebSocket connected (managed)")
        
        await self._handle_video_streaming(websocket)
    
    async def _handle_video_streaming(self, websocket: WebSocket):
        """Core video streaming logic"""
        self.video_service.add_client(websocket)
        
        try:
            frame_count = 0
            fps_counter = []
            last_fps_update = time.time()
            point_width, point_height = await self.device_service.get_point_dimensions()
            
            while True:
                frame_data = self.video_service.get_frame(timeout=0.05)
                
                if frame_data:
                    frame_count += 1
                    current_time = time.time()
                    
                    # Calculate FPS
                    fps_counter.append(current_time)
                    fps_counter = [t for t in fps_counter if current_time - t < 1.0]
                    current_fps = len(fps_counter)
                    
                    # Create video frame response
                    video_frame = VideoFrame(
                        data=frame_data["data"],
                        pixel_width=frame_data.get("pixel_width", 390),
                        pixel_height=frame_data.get("pixel_height", 844),
                        point_width=point_width,
                        point_height=point_height,
                        frame=frame_count,
                        timestamp=frame_data["timestamp"],
                        fps=current_fps,
                        format=frame_data.get("format", "jpeg")
                    )
                    
                    await websocket.send_text(video_frame.model_dump_json())
                    
                    # Log performance
                    if current_time - last_fps_update > 3:
                        # logger.info(f"🎥 Video streaming: {current_fps} FPS, Queue: {self.video_service.video_frame_queue.qsize()}")
                        last_fps_update = current_time
                else:
                    await asyncio.sleep(0.01)
                    
        except WebSocketDisconnect:
            logger.info("Video WebSocket disconnected")
        except Exception as e:
            logger.error(f"Video WebSocket error: {e}")
        finally:
            self.video_service.remove_client(websocket)