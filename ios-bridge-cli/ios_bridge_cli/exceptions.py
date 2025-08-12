"""
Custom exceptions for iOS Bridge CLI
"""


class IOSBridgeError(Exception):
    """Base exception for iOS Bridge CLI errors"""
    pass


class ConnectionError(IOSBridgeError):
    """Raised when connection to iOS Bridge server fails"""
    pass


class SessionNotFoundError(IOSBridgeError):
    """Raised when a session ID is not found"""
    pass


class ElectronAppError(IOSBridgeError):
    """Raised when Electron app fails to start or communicate"""
    pass


class StreamingError(IOSBridgeError):
    """Raised when video streaming fails"""
    pass