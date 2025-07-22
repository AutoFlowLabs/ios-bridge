from pydantic import BaseModel
from typing import Optional, Dict, Any

class StatusResponse(BaseModel):
    udid: str
    simulator_accessible: bool
    video_streaming: bool
    video_clients: int
    webrtc_active: bool
    webrtc_connections: int
    queue_size: int
    capture_method: str
    status: str

class VideoFrame(BaseModel):
    type: str = "video_frame"
    data: str
    pixel_width: int
    pixel_height: int
    point_width: int
    point_height: int
    frame: int
    timestamp: float
    fps: int
    format: str = "jpeg"

class ScreenshotResponse(BaseModel):
    type: str = "screenshot"
    data: str
    pixel_width: int
    pixel_height: int
    point_width: int
    point_height: int
    format: str = "jpeg"

class QualityResponse(BaseModel):
    success: bool
    quality: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    error: Optional[str] = None