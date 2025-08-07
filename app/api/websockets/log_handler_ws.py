import asyncio
import json
import subprocess
import time
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.services.session_manager import session_manager
from app.core.logging import logger

class LogStreamManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.log_processes: Dict[str, subprocess.Popen] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Connect a WebSocket client for log streaming"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        
        self.active_connections[session_id].add(websocket)
        logger.info(f"Log WebSocket connected for session {session_id}")
        
        # Start log streaming if this is the first connection
        if len(self.active_connections[session_id]) == 1:
            await self._start_log_stream(session_id)
    
    async def disconnect(self, websocket: WebSocket, session_id: str):
        """Disconnect a WebSocket client"""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            
            # Stop log streaming if no more connections
            if not self.active_connections[session_id]:
                await self._stop_log_stream(session_id)
                del self.active_connections[session_id]
        
        logger.info(f"Log WebSocket disconnected for session {session_id}")
    
    async def _start_log_stream(self, session_id: str):
        """Start streaming logs for a session"""
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found for log streaming")
            return
        
        try:
            # Use simctl for iOS Simulator logging
            command = [
                'xcrun', 'simctl', 'spawn', session.udid,
                'log', 'stream', 
                '--style', 'compact',
                '--color', 'none',
                '--level', 'debug'
            ]
            
            logger.info(f"Starting log stream with command: {' '.join(command)}")
            
            # Start the log process
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self.log_processes[session_id] = process
            logger.info(f"Started log streaming process for session {session_id}")
            
            # Start reading logs in background
            asyncio.create_task(self._read_logs(session_id, process))
            
        except Exception as e:
            logger.error(f"Failed to start log stream for session {session_id}: {e}")
            # Send error message to connected clients
            await self._broadcast_error(session_id, f"Failed to start log stream: {str(e)}")
    
    async def _stop_log_stream(self, session_id: str):
        """Stop streaming logs for a session"""
        if session_id in self.log_processes:
            process = self.log_processes[session_id]
            try:
                process.terminate()
                # Wait a bit for graceful termination
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            except Exception as e:
                logger.error(f"Error stopping log process: {e}")
            
            del self.log_processes[session_id]
            logger.info(f"Stopped log streaming for session {session_id}")
    
    async def _read_logs(self, session_id: str, process: subprocess.Popen):
        """Read logs from process and broadcast to WebSocket clients"""
        logger.info(f"Starting to read logs for session {session_id}")
        try:
            while process.poll() is None:
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    logger.debug(f"Log line received: {line}")
                    
                    # Parse log line and create structured message
                    log_message = self._parse_log_line(line)
                    
                    # Broadcast to all connected clients
                    await self._broadcast_message(session_id, log_message)
                
                await asyncio.sleep(0.01)  # Small delay to prevent overwhelming
                
        except Exception as e:
            logger.error(f"Error reading logs for session {session_id}: {e}")
            await self._broadcast_error(session_id, f"Log reading error: {str(e)}")
        finally:
            # Ensure process cleanup
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except:
                    try:
                        process.kill()
                        process.wait()
                    except:
                        pass
            logger.info(f"Log reading stopped for session {session_id}")
    
    async def _broadcast_message(self, session_id: str, message: dict):
        """Broadcast message to all connected clients for a session"""
        if session_id not in self.active_connections:
            return
        
        dead_connections = set()
        message_json = json.dumps(message)
        
        for websocket in self.active_connections[session_id].copy():
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                dead_connections.add(websocket)
        
        # Remove dead connections
        for dead_conn in dead_connections:
            self.active_connections[session_id].discard(dead_conn)
    
    async def _broadcast_error(self, session_id: str, error_message: str):
        """Broadcast error message to all connected clients"""
        error_msg = {
            "type": "error",
            "message": error_message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        await self._broadcast_message(session_id, error_msg)
    
    def _parse_log_line(self, line: str) -> dict:
        """Parse a log line into structured format"""
        try:
            # Basic log line parsing for iOS simulator logs
            # Format is usually: timestamp process[pid] <level>: message
            parts = line.split(' ', 3)
            
            if len(parts) >= 4:
                timestamp_str = f"{parts[0]} {parts[1]}"
                process_info = parts[2]  # Contains process[pid]
                message = parts[3] if len(parts) > 3 else ""
                
                # Extract process name and PID
                if '[' in process_info and ']' in process_info:
                    process_name = process_info.split('[')[0]
                    pid_part = process_info.split('[')[1].split(']')[0]
                else:
                    process_name = process_info
                    pid_part = ""
                
                # Determine log level
                level = "info"
                if "error" in message.lower() or "<Error>" in message:
                    level = "error"
                elif "warning" in message.lower() or "<Warning>" in message:
                    level = "warning"
                elif "debug" in message.lower() or "<Debug>" in message:
                    level = "debug"
                
                return {
                    "type": "log",
                    "timestamp": timestamp_str,
                    "process": process_name,
                    "pid": pid_part,
                    "level": level,
                    "message": message,
                    "raw_line": line
                }
            else:
                return {
                    "type": "log",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "process": "unknown",
                    "pid": "",
                    "level": "info",
                    "message": line,
                    "raw_line": line
                }
                
        except Exception as e:
            logger.error(f"Error parsing log line '{line}': {e}")
            return {
                "type": "log",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "process": "unknown",
                "pid": "",
                "level": "info",
                "message": line,
                "raw_line": line
            }

# Global log stream manager
log_stream_manager = LogStreamManager()

async def handle_log_websocket(websocket: WebSocket, session_id: str):
    """Handle log WebSocket connections"""
    logger.info(f"New log WebSocket connection for session: {session_id}")
    
    try:
        await log_stream_manager.connect(websocket, session_id)
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for messages from client (like filter commands)
                message = await websocket.receive_text()
                data = json.loads(message)
                
                logger.info(f"Received log WebSocket message: {data}")
                
                if data.get("type") == "filter":
                    # Handle log filtering requests
                    await handle_log_filter(websocket, session_id, data)
                elif data.get("type") == "clear":
                    # Send clear command to client
                    await websocket.send_text(json.dumps({"type": "clear"}))
                    
            except WebSocketDisconnect:
                logger.info(f"Log WebSocket disconnected for session: {session_id}")
                break
            except Exception as e:
                logger.error(f"Error handling log WebSocket message: {e}")
                break
    
    except Exception as e:
        logger.error(f"Log WebSocket error for session {session_id}: {e}")
    finally:
        await log_stream_manager.disconnect(websocket, session_id)

async def handle_log_filter(websocket: WebSocket, session_id: str, filter_data: dict):
    """Handle log filtering commands"""
    try:
        # Send acknowledgment that filter was applied
        response = {
            "type": "filter_applied",
            "filter": filter_data.get("filter", ""),
            "level": filter_data.get("level", "all")
        }
        await websocket.send_text(json.dumps(response))
        logger.info(f"Applied log filter for session {session_id}: {filter_data}")
        
    except Exception as e:
        logger.error(f"Error applying log filter: {e}")