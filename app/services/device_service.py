import subprocess
import re
from typing import Tuple, Optional
from app.config.settings import settings
from app.core.logging import logger
from app.core.exceptions import DeviceNotAccessibleException

class DeviceService:
    """Service for device interactions"""
    
    def __init__(self):
        self.udid = settings.UDID
        self._point_dimensions_cache: Optional[Tuple[int, int]] = None
    
    async def get_point_dimensions(self) -> Tuple[int, int]:
        """Get device point dimensions with caching"""
        if self._point_dimensions_cache:
            return self._point_dimensions_cache
        
        try:
            cmd = ["idb", "describe", "--udid", self.udid]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0:
                width_match = re.search(r'width_points=(\d+)', result.stdout)
                height_match = re.search(r'height_points=(\d+)', result.stdout)
                
                if width_match and height_match:
                    self._point_dimensions_cache = (
                        int(width_match.group(1)), 
                        int(height_match.group(1))
                    )
                    return self._point_dimensions_cache
        except Exception as e:
            logger.error(f"Error getting point dimensions: {e}")
        
        # Default dimensions
        self._point_dimensions_cache = (390, 844)
        return self._point_dimensions_cache
    
    async def tap(self, x: int, y: int) -> bool:
        """Perform tap gesture"""
        try:
            cmd = ["idb", "ui", "tap", str(x), str(y), "--udid", self.udid]
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  timeout=settings.TAP_TIMEOUT)
            
            if result.returncode == 0:
                logger.info(f"✅ Tap: ({x}, {y})")
                return True
            else:
                logger.error(f"❌ Tap failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Tap error: {e}")
            return False
    
    async def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, 
                   duration: float = 0.2) -> bool:
        """Perform swipe gesture"""
        try:
            cmd = [
                "idb", "ui", "swipe", 
                str(start_x), str(start_y), str(end_x), str(end_y),
                "--duration", str(duration), "--udid", self.udid
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  timeout=settings.SWIPE_TIMEOUT)
            
            if result.returncode == 0:
                logger.info(f"✅ Swipe: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
                return True
            else:
                logger.error(f"❌ Swipe failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Swipe error: {e}")
            return False
    
    async def input_text(self, text: str) -> bool:
        """Input text"""
        try:
            cmd = ["idb", "ui", "text", text, "--udid", self.udid]
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  timeout=settings.TEXT_TIMEOUT)
            
            if result.returncode == 0:
                logger.info("✅ Text entered")
                return True
            else:
                logger.error("❌ Text failed")
                return False
        except Exception as e:
            logger.error(f"Text input error: {e}")
            return False
    
    async def press_button(self, button: str) -> bool:
        """Press device button"""
        try:
            button_mapping = {
                'home': 'HOME', 'lock': 'LOCK', 'siri': 'SIRI',
                'side-button': 'SIDE_BUTTON', 'apple-pay': 'APPLE_PAY'
            }
            idb_button = button_mapping.get(button, button.upper())
            
            cmd = ["idb", "ui", "button", idb_button, "--udid", self.udid]
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  timeout=settings.TAP_TIMEOUT)
            
            if result.returncode == 0:
                logger.info(f"✅ Button: {button}")
                return True
            else:
                logger.error(f"❌ Button failed: {button}")
                return False
        except Exception as e:
            logger.error(f"Button error: {e}")
            return False
    
    async def is_accessible(self) -> bool:
        """Check if device is accessible"""
        try:
            cmd = ["idb", "list-targets"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return self.udid in result.stdout
        except Exception:
            return False