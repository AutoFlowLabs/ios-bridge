import base64
import io
from PIL import Image
import numpy as np
import cv2
from typing import Dict, Optional
from app.core.logging import logger

class ImageUtils:
    """Image processing utilities"""
    
    @staticmethod
    def encode_image_to_base64(image_data: bytes, quality: int = 80) -> str:
        """Encode image data to base64"""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=quality, optimize=True)
                return base64.b64encode(output.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error(f"Image encoding error: {e}")
            raise
    
    @staticmethod
    def decode_base64_to_array(base64_data: str) -> np.ndarray:
        """Decode base64 image to numpy array"""
        try:
            image_bytes = base64.b64decode(base64_data)
            with Image.open(io.BytesIO(image_bytes)) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                return np.array(img, dtype=np.uint8)
        except Exception as e:
            logger.error(f"Image decoding error: {e}")
            raise
    
    @staticmethod
    def resize_image(img: Image.Image, width: int, height: int, 
                    quality: Image.Resampling = Image.Resampling.LANCZOS) -> Image.Image:
        """Resize image with specified quality"""
        return img.resize((width, height), quality)
    
    @staticmethod
    def optimize_for_streaming(img: Image.Image, max_width: int = 390) -> Image.Image:
        """Optimize image for streaming"""
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = ImageUtils.resize_image(img, max_width, new_height)
        return img