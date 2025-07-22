class IOSRemoteControlException(Exception):
    """Base exception for iOS Remote Control"""
    pass

class DeviceNotAccessibleException(IOSRemoteControlException):
    """Device is not accessible"""
    pass

class VideoCaptureException(IOSRemoteControlException):
    """Video capture failed"""
    pass

class WebRTCException(IOSRemoteControlException):
    """WebRTC related exception"""
    pass

class ScreenshotException(IOSRemoteControlException):
    """Screenshot capture failed"""
    pass