from pydantic import BaseModel
from typing import Optional, Dict, Any

class TapEvent(BaseModel):
    t: str = "tap"
    x: int
    y: int

class SwipeEvent(BaseModel):
    t: str = "swipe"
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    duration: Optional[float] = 0.2

class TextEvent(BaseModel):
    t: str = "text"
    text: str

class ButtonEvent(BaseModel):
    t: str = "button"
    button: str

class KeyEvent(BaseModel):
    t: str = "key"
    key: str
    duration: Optional[float] = None

class RefreshEvent(BaseModel):
    t: str = "refresh"

class WebRTCOffer(BaseModel):
    type: str = "offer"
    sdp: str

class WebRTCAnswer(BaseModel):
    type: str = "answer"
    sdp: str

class WebRTCIceCandidate(BaseModel):
    type: str = "ice-candidate"
    candidate: Dict[str, Any]