import subprocess
import tempfile
import os
from typing import Dict, Optional
from app.config.settings import settings
from app.core.logging import logger

class SystemUtils:
    """System utility functions"""
    
    @staticmethod
    def get_simulator_window_info() -> Dict[str, int]:
        """Get iOS Simulator window position and size"""
        try:
            script = '''
            tell application "System Events"
                tell process "Simulator"
                    try
                        set frontWindow to first window
                        set windowPosition to position of frontWindow
                        set windowSize to size of frontWindow
                        return (item 1 of windowPosition) & "," & (item 2 of windowPosition) & "," & (item 1 of windowSize) & "," & (item 2 of windowSize)
                    on error
                        return "error"
                    end try
                end tell
            end tell
            '''
            
            cmd = ["osascript", "-e", script]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and "error" not in result.stdout:
                coords = result.stdout.strip().split(",")
                if len(coords) == 4:
                    x, y, width, height = map(int, coords)
                    screen_x = x + 20
                    screen_y = y + 100
                    screen_width = width - 40
                    screen_height = height - 120
                    
                    return {
                        "x": max(0, screen_x),
                        "y": max(0, screen_y),
                        "width": max(300, screen_width),
                        "height": max(500, screen_height)
                    }
        except Exception as e:
            logger.warning(f"Could not get simulator window info: {e}")
        
        return {"x": 100, "y": 100, "width": 390, "height": 844}
    
    @staticmethod
    def create_temp_file(suffix: str = '.png') -> tempfile.NamedTemporaryFile:
        """Create a temporary file"""
        return tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    
    @staticmethod
    def cleanup_temp_file(filepath: str):
        """Safely cleanup temporary file"""
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception as e:
            logger.debug(f"Could not cleanup temp file {filepath}: {e}")