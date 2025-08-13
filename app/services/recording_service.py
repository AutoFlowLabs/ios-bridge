import subprocess
import tempfile
import os
import signal
import time
import shutil
from typing import Optional, Dict
from app.config.settings import settings
from app.core.logging import logger
from app.utils.system_utils import SystemUtils

class RecordingService:
    """Service for video recording with dynamic UDID support"""
    
    def __init__(self, udid: Optional[str] = None):
        self.udid = udid
        self.recording_process: Optional[subprocess.Popen] = None
        self.recording_file: Optional[str] = None
        self.is_recording = False
    
    def set_udid(self, udid: str):
        """Set the UDID for this service instance"""
        self.udid = udid
    
    def start_recording(self) -> Dict[str, any]:
        """Start video recording"""
        if not self.udid:
            logger.error("No UDID set for video recording")
            return {"success": False, "error": "No UDID set"}
            
        if self.is_recording:
            logger.warning("Recording already in progress")
            return {"success": False, "error": "Recording already in progress"}
            
        try:
            # Create temporary file for recording
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                self.recording_file = temp_file.name
            
            # Start idb record-video command
            cmd = ["idb", "record-video", self.recording_file, "--udid", self.udid]
            
            logger.info(f"Starting video recording: {' '.join(cmd)}")
            
            self.recording_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group for proper termination
            )
            
            # Give it a moment to start
            time.sleep(0.5)
            
            # Check if process is still running
            if self.recording_process.poll() is None:
                self.is_recording = True
                logger.info(f"✅ Video recording started for UDID: {self.udid}")
                return {
                    "success": True,
                    "message": "Recording started",
                    "file_path": self.recording_file
                }
            else:
                # Process failed to start
                stdout, stderr = self.recording_process.communicate()
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"❌ Recording failed to start: {error_msg}")
                self._cleanup_recording()
                return {"success": False, "error": f"Recording failed to start: {error_msg}"}
                
        except Exception as e:
            logger.error(f"Recording start error for UDID {self.udid}: {e}")
            self._cleanup_recording()
            return {"success": False, "error": str(e)}
    
    def stop_recording(self) -> Dict[str, any]:
        """Stop video recording and return file path"""
        if not self.is_recording or not self.recording_process:
            logger.warning("No recording in progress")
            return {"success": False, "error": "No recording in progress"}
            
        try:
            # Send SIGTERM to the process group to stop recording gracefully
            if self.recording_process.poll() is None:
                os.killpg(os.getpgid(self.recording_process.pid), signal.SIGTERM)
                
                # Wait for process to finish (idb will write the file on exit)
                try:
                    self.recording_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't stop gracefully
                    logger.warning("Recording process didn't stop gracefully, force killing")
                    os.killpg(os.getpgid(self.recording_process.pid), signal.SIGKILL)
                    self.recording_process.wait()
            
            # Check if recording file was created and has content
            if self.recording_file and os.path.exists(self.recording_file):
                file_size = os.path.getsize(self.recording_file)
                if file_size > 0:
                    logger.info(f"✅ Recording stopped. File: {self.recording_file} ({file_size} bytes)")
                    
                    # Return the file path for download
                    result = {
                        "success": True,
                        "message": "Recording stopped successfully",
                        "file_path": self.recording_file,
                        "file_size": file_size
                    }
                    
                    # Don't cleanup yet - file will be cleaned up after download
                    self.is_recording = False
                    self.recording_process = None
                    
                    return result
                else:
                    logger.error("Recording file is empty")
                    self._cleanup_recording()
                    return {"success": False, "error": "Recording file is empty"}
            else:
                logger.error("Recording file not found")
                self._cleanup_recording()
                return {"success": False, "error": "Recording file not found"}
                
        except Exception as e:
            logger.error(f"Recording stop error for UDID {self.udid}: {e}")
            self._cleanup_recording()
            return {"success": False, "error": str(e)}
    
    def _cleanup_recording(self):
        """Clean up recording resources"""
        self.is_recording = False
        
        if self.recording_process:
            try:
                if self.recording_process.poll() is None:
                    os.killpg(os.getpgid(self.recording_process.pid), signal.SIGKILL)
                    self.recording_process.wait()
            except:
                pass
            self.recording_process = None
        
        if self.recording_file and os.path.exists(self.recording_file):
            try:
                os.unlink(self.recording_file)
            except:
                pass
            self.recording_file = None
    
    def cleanup_recording_file(self, file_path: str):
        """Clean up recording file after download"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up recording file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up recording file {file_path}: {e}")
    
    def is_recording_active(self) -> bool:
        """Check if recording is currently active"""
        return self.is_recording and self.recording_process and self.recording_process.poll() is None
    
    def force_stop(self):
        """Force stop recording (called on app shutdown)"""
        if self.is_recording:
            logger.info("Force stopping recording due to app shutdown")
            
            try:
                # Try to stop gracefully first to save the video
                if self.recording_process and self.recording_process.poll() is None:
                    logger.info("Attempting graceful recording stop...")
                    
                    # Send SIGTERM to stop recording gracefully
                    os.killpg(os.getpgid(self.recording_process.pid), signal.SIGTERM)
                    
                    # Wait a bit longer for the file to be written
                    try:
                        self.recording_process.wait(timeout=8)  # Increased timeout
                        logger.info("Recording process stopped gracefully")
                        
                        # Check if file was created
                        if self.recording_file and os.path.exists(self.recording_file):
                            file_size = os.path.getsize(self.recording_file)
                            if file_size > 0:
                                # Move file to user's Downloads folder
                                try:
                                    from pathlib import Path
                                    
                                    downloads_dir = Path.home() / "Downloads"
                                    timestamp = int(time.time())
                                    session_id = self.udid[:8] if self.udid else "unknown"
                                    final_filename = f"ios-recording-emergency_{session_id}_{timestamp}.mp4"
                                    final_path = downloads_dir / final_filename
                                    
                                    shutil.move(self.recording_file, final_path)
                                    logger.info(f"📹 Emergency recording saved to: {final_path}")
                                    print(f"📹 Emergency recording saved to: {final_path}")
                                    
                                except Exception as move_error:
                                    logger.error(f"Failed to move recording file: {move_error}")
                                    logger.info(f"Recording file left at: {self.recording_file} ({file_size} bytes)")
                                    print(f"📹 Recording file saved at: {self.recording_file}")
                                
                                return
                        
                    except subprocess.TimeoutExpired:
                        logger.warning("Recording process didn't stop gracefully, force killing")
                        os.killpg(os.getpgid(self.recording_process.pid), signal.SIGKILL)
                        self.recording_process.wait()
                        
            except Exception as e:
                logger.error(f"Error during force stop: {e}")
            
            finally:
                self.is_recording = False
                self.recording_process = None