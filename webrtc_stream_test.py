import asyncio
import subprocess
import threading
import time
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiohttp import web
import json
import numpy as np
from av import VideoFrame
import logging
import tempfile
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class iOSVideoTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.frame_queue = asyncio.Queue(maxsize=3)
        self.running = False
        self.width = 375
        self.height = 812
        self.temp_fifo = None
        
    async def start_stream(self):
        """Start the iOS video stream capture"""
        if self.running:
            return
            
        self.running = True
        
        # Create a named pipe (FIFO) for better stream handling
        self.temp_fifo = tempfile.mktemp(suffix='.h264')
        try:
            os.mkfifo(self.temp_fifo)
        except:
            # Fallback for systems that don't support mkfifo
            self.temp_fifo = tempfile.NamedTemporaryFile(suffix='.h264', delete=False).name
        
        # Start background thread to read frames
        self.frame_thread = threading.Thread(target=self._read_frames, daemon=True)
        self.frame_thread.start()
        
        logger.info(f"iOS video stream started - Resolution: {self.width}x{self.height}")
            
    def _read_frames(self):
        """Improved frame reading with better H.264 handling"""
        
        # First, start the idb process to write to our FIFO
        idb_cmd = [
            'idb', 'video-stream', 
            '--udid', '00D37893-4642-4961-B136-AF2542685B1A',
            '--format', 'h264',
            '--fps', '30'
        ]
        
        idb_process = None
        ffmpeg_process = None
        
        try:
            # Start writing H.264 stream to file
            idb_thread = threading.Thread(target=self._write_h264_stream, args=(idb_cmd,))
            idb_thread.daemon = True
            idb_thread.start()
            
            # Give it a moment to start writing
            time.sleep(2)
            
            # Use ffmpeg with better H.264 handling
            ffmpeg_cmd = [
                'ffmpeg',
                '-fflags', '+genpts',           # Generate presentation timestamps
                '-flags', 'low_delay',          # Low delay mode
                '-probesize', '32',             # Reduce probing
                '-analyzeduration', '0',        # Don't analyze duration
                '-f', 'h264',                   # Input format
                '-i', self.temp_fifo,           # Input file
                '-vf', f'scale={self.width}:{self.height}',  # Scale to exact size
                '-f', 'rawvideo',               # Output format
                '-pix_fmt', 'rgb24',            # Pixel format
                '-r', '30',                     # Output frame rate
                '-'                             # Output to stdout
            ]
            
            logger.info("Starting ffmpeg process...")
            ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0  # Unbuffered
            )
            
            frame_size = self.width * self.height * 3
            frame_count = 0
            consecutive_errors = 0
            max_consecutive_errors = 10
            
            logger.info("Beginning frame capture...")
            
            while self.running and consecutive_errors < max_consecutive_errors:
                try:
                    # Read frame with timeout
                    raw_frame = ffmpeg_process.stdout.read(frame_size)
                    
                    if len(raw_frame) != frame_size:
                        if len(raw_frame) == 0:
                            logger.warning("No data from ffmpeg")
                            consecutive_errors += 1
                            time.sleep(0.1)
                            continue
                        else:
                            logger.warning(f"Incomplete frame: got {len(raw_frame)}, expected {frame_size}")
                            consecutive_errors += 1
                            continue
                    
                    # Reset error counter on successful read
                    consecutive_errors = 0
                    
                    # Convert to numpy array
                    frame_array = np.frombuffer(raw_frame, dtype=np.uint8)
                    frame = frame_array.reshape((self.height, self.width, 3))
                    
                    # Validate frame (check if it's not all zeros or corrupted)
                    if self._is_valid_frame(frame):
                        # Add frame to queue (drop old frames if queue is full)
                        try:
                            while self.frame_queue.qsize() >= 3:
                                try:
                                    self.frame_queue.get_nowait()
                                except:
                                    break
                            self.frame_queue.put_nowait(frame.copy())
                            frame_count += 1
                            
                            if frame_count % 100 == 0:
                                logger.info(f"Processed {frame_count} valid frames")
                        except Exception as e:
                            logger.error(f"Error adding frame to queue: {e}")
                    else:
                        logger.debug("Skipped invalid frame")
                        
                except Exception as e:
                    if self.running:
                        logger.error(f"Error reading frame: {e}")
                        consecutive_errors += 1
                        time.sleep(0.1)
                    else:
                        break
                        
        except Exception as e:
            logger.error(f"Error in frame reading process: {e}")
        finally:
            logger.info("Cleaning up frame reading process...")
            if ffmpeg_process:
                try:
                    ffmpeg_process.terminate()
                    ffmpeg_process.wait(timeout=5)
                except:
                    ffmpeg_process.kill()
            
            # Cleanup temp file
            if self.temp_fifo and os.path.exists(self.temp_fifo):
                try:
                    os.unlink(self.temp_fifo)
                except:
                    pass
    
    def _write_h264_stream(self, cmd):
        """Write H.264 stream to temporary file"""
        try:
            with open(self.temp_fifo, 'wb') as f:
                process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.PIPE)
                while self.running:
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                process.terminate()
        except Exception as e:
            logger.error(f"Error writing H.264 stream: {e}")
    
    def _is_valid_frame(self, frame):
        """Check if frame is valid (not corrupted)"""
        try:
            # Check if frame is not all zeros
            if np.all(frame == 0):
                return False
            
            # Check if frame has reasonable variance (not corrupted)
            variance = np.var(frame)
            if variance < 10:  # Very low variance might indicate corruption
                return False
            
            # Check for reasonable pixel value distribution
            mean_val = np.mean(frame)
            if mean_val < 5 or mean_val > 250:  # Extreme values
                return False
                
            return True
        except:
            return False
    
    async def recv(self):
        """Get the next video frame for WebRTC"""
        pts, time_base = await self.next_timestamp()
        
        try:
            # Try to get a frame with a reasonable timeout
            frame_array = await asyncio.wait_for(self.frame_queue.get(), timeout=1.0)
            
            # Create VideoFrame
            frame = VideoFrame.from_ndarray(frame_array, format='rgb24')
            frame.pts = pts
            frame.time_base = time_base
            
            return frame
            
        except asyncio.TimeoutError:
            # Create a simple pattern instead of black frame to indicate no data
            pattern_frame = self._create_pattern_frame()
            frame = VideoFrame.from_ndarray(pattern_frame, format='rgb24')
            frame.pts = pts
            frame.time_base = time_base
            return frame
        except Exception as e:
            logger.error(f"Error in recv: {e}")
            # Return pattern frame on error
            pattern_frame = self._create_pattern_frame()
            frame = VideoFrame.from_ndarray(pattern_frame, format='rgb24')
            frame.pts = pts
            frame.time_base = time_base
            return frame
    
    def _create_pattern_frame(self):
        """Create a test pattern frame to indicate no video data"""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Add a simple pattern
        frame[::20, :] = [64, 64, 64]  # Horizontal lines
        frame[:, ::20] = [64, 64, 64]  # Vertical lines
        # Add text area (simple rectangle)
        frame[400:450, 150:225] = [128, 128, 128]
        return frame
    
    def stop(self):
        """Stop the video stream"""
        logger.info("Stopping video stream...")
        self.running = False

# Keep the same WebRTCServer class as before
class WebRTCServer:
    def __init__(self):
        self.pcs = set()
        self.video_track = None
        
    async def offer(self, request):
        """Handle WebRTC offer from client"""
        try:
            params = await request.json()
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
            
            pc = RTCPeerConnection()
            self.pcs.add(pc)
            
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection state is {pc.connectionState}")
                if pc.connectionState == "failed" or pc.connectionState == "closed":
                    await pc.close()
                    self.pcs.discard(pc)
            
            # Create or reuse video track
            if not self.video_track or not self.video_track.running:
                self.video_track = iOSVideoTrack()
                await self.video_track.start_stream()
            
            pc.addTrack(self.video_track)
            
            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            return web.Response(
                content_type="application/json",
                text=json.dumps({
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type
                })
            )
            
        except Exception as e:
            logger.error(f"Error handling offer: {e}")
            return web.Response(status=500, text=str(e))
    
    async def index(self, request):
        """Serve the HTML page"""
        try:
            with open('index.html', 'r') as f:
                content = f.read()
            return web.Response(content_type="text/html", text=content)
        except FileNotFoundError:
            return web.Response(status=404, text="index.html not found")
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up WebRTC connections...")
        coros = [pc.close() for pc in self.pcs]
        await asyncio.gather(*coros, return_exceptions=True)
        self.pcs.clear()
        
        if self.video_track:
            self.video_track.stop()

async def main():
    server = WebRTCServer()
    
    app = web.Application()
    app.router.add_get("/", server.index)
    app.router.add_post("/offer", server.offer)
    app.router.add_static('/', path='.', name='static')
    
    async def cleanup_handler(app):
        await server.cleanup()
    
    app.on_cleanup.append(cleanup_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()
    
    logger.info("Server started at http://localhost:8080")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await cleanup_handler(app)

if __name__ == "__main__":
    asyncio.run(main())