from typing import Optional
import os

class Settings:
    """Application settings"""
    
    # Device Configuration
    UDID: str = "F93FBAE5-7175-4AFF-A262-DDEBB8A6D662"
    
    # Video Configuration
    DEFAULT_VIDEO_FPS: int = 60
    VIDEO_QUEUE_SIZE: int = 3
    WEBRTC_QUEUE_SIZE: int = 2
    
    # Quality Settings
    DEFAULT_JPEG_QUALITY: int = 80
    WEBRTC_HIGH_QUALITY: int = 95
    
    # Timeouts
    SCREENSHOT_TIMEOUT: float = 0.5
    TAP_TIMEOUT: float = 2.0
    SWIPE_TIMEOUT: float = 3.0
    TEXT_TIMEOUT: float = 5.0
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Paths
    STATIC_DIR: str = "static"
    TEMP_DIR: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"

settings = Settings()