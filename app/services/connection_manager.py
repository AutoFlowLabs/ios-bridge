"""
Connection Manager for handling concurrent WebSocket and WebRTC connections
Optimized for cloud deployment with multiple users
"""

import asyncio
import weakref
import time
from typing import Dict, List, Set
from collections import defaultdict
import logging
from contextlib import asynccontextmanager

from app.core.logging import logger
from app.config.settings import settings

class ConnectionManager:
    """Manages concurrent WebSocket and WebRTC connections efficiently"""
    
    def __init__(self, max_connections_per_session: int = None):
        # Connection tracking
        self.active_connections: Dict[str, Set[weakref.ref]] = defaultdict(set)
        self.connection_stats: Dict[str, dict] = {}
        if max_connections_per_session is None:
            try:
                self.max_connections_per_session = settings.MAX_CONNECTIONS_PER_SESSION
            except:
                self.max_connections_per_session = 10  # fallback
        else:
            self.max_connections_per_session = max_connections_per_session
        
        # Rate limiting
        self.connection_rate_limits: Dict[str, List[float]] = defaultdict(list)
        self.rate_limit_window = 60  # seconds
        try:
            self.max_connections_per_minute = settings.MAX_CONNECTIONS_PER_MINUTE
        except:
            self.max_connections_per_minute = 20  # fallback
        
        # Cleanup tracking
        self.cleanup_tasks: Set[asyncio.Task] = set()
        self.last_cleanup = time.time()
        try:
            self.cleanup_interval = settings.CONNECTION_CLEANUP_INTERVAL
        except:
            self.cleanup_interval = 30  # fallback
        self._cleanup_task = None
    
    def start_background_tasks(self):
        """Start background cleanup task when event loop is available"""
        if self._cleanup_task is None:
            try:
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
                logger.info("🧹 ConnectionManager background cleanup started")
            except RuntimeError:
                logger.warning("Cannot start background tasks - no event loop running")
    
    async def stop_background_tasks(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("🧹 ConnectionManager background cleanup stopped")
    
    async def register_connection(self, session_id: str, connection_type: str, 
                                connection_obj, client_ip: str = None) -> bool:
        """Register a new connection with rate limiting and validation"""
        
        # Rate limiting check
        if not self._check_rate_limit(session_id, client_ip):
            logger.warning(f"Rate limit exceeded for session {session_id} from {client_ip}")
            return False
        
        # Connection limit check
        if len(self.active_connections[session_id]) >= self.max_connections_per_session:
            logger.warning(f"Connection limit exceeded for session {session_id}")
            return False
        
        # Register connection using weak reference to prevent memory leaks
        connection_ref = weakref.ref(connection_obj, 
                                   lambda ref: self._on_connection_cleanup(session_id, ref))
        
        self.active_connections[session_id].add(connection_ref)
        
        # Update stats
        if session_id not in self.connection_stats:
            self.connection_stats[session_id] = {
                'total_connections': 0,
                'active_connections': 0,
                'connection_types': defaultdict(int),
                'first_connection': time.time(),
                'last_connection': time.time()
            }
        
        stats = self.connection_stats[session_id]
        stats['total_connections'] += 1
        stats['active_connections'] = len(self.active_connections[session_id])
        stats['connection_types'][connection_type] += 1
        stats['last_connection'] = time.time()
        
        logger.info(f"✅ Registered {connection_type} connection for session {session_id} "
                   f"({stats['active_connections']}/{self.max_connections_per_session})")
        
        return True
    
    def _check_rate_limit(self, session_id: str, client_ip: str) -> bool:
        """Check if connection is within rate limits"""
        current_time = time.time()
        rate_key = f"{session_id}:{client_ip}" if client_ip else session_id
        
        # Clean old entries
        self.connection_rate_limits[rate_key] = [
            conn_time for conn_time in self.connection_rate_limits[rate_key]
            if current_time - conn_time < self.rate_limit_window
        ]
        
        # Check rate limit
        if len(self.connection_rate_limits[rate_key]) >= self.max_connections_per_minute:
            return False
        
        # Add current connection
        self.connection_rate_limits[rate_key].append(current_time)
        return True
    
    def _on_connection_cleanup(self, session_id: str, connection_ref):
        """Callback when connection is garbage collected"""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(connection_ref)
            
            # Update stats
            if session_id in self.connection_stats:
                self.connection_stats[session_id]['active_connections'] = \
                    len(self.active_connections[session_id])
    
    def unregister_connection(self, session_id: str, connection_obj):
        """Manually unregister a connection"""
        if session_id in self.active_connections:
            # Find and remove the connection reference
            to_remove = None
            for conn_ref in self.active_connections[session_id]:
                if conn_ref() is connection_obj:
                    to_remove = conn_ref
                    break
            
            if to_remove:
                self.active_connections[session_id].discard(to_remove)
                
                # Update stats
                if session_id in self.connection_stats:
                    self.connection_stats[session_id]['active_connections'] = \
                        len(self.active_connections[session_id])
                
                logger.info(f"🔌 Unregistered connection for session {session_id}")
    
    def get_session_connections(self, session_id: str) -> List:
        """Get all active connections for a session"""
        if session_id not in self.active_connections:
            return []
        
        # Return only live connections (weak refs that still point to objects)
        live_connections = []
        dead_refs = set()
        
        for conn_ref in self.active_connections[session_id]:
            conn_obj = conn_ref()
            if conn_obj is not None:
                live_connections.append(conn_obj)
            else:
                dead_refs.add(conn_ref)
        
        # Clean up dead references
        self.active_connections[session_id] -= dead_refs
        
        return live_connections
    
    def get_connection_stats(self, session_id: str = None) -> dict:
        """Get connection statistics"""
        if session_id:
            return self.connection_stats.get(session_id, {})
        
        # Global stats
        total_sessions = len(self.active_connections)
        total_connections = sum(len(conns) for conns in self.active_connections.values())
        
        return {
            'total_sessions': total_sessions,
            'total_connections': total_connections,
            'sessions': dict(self.connection_stats),
            'rate_limit_buckets': len(self.connection_rate_limits)
        }
    
    async def cleanup_session(self, session_id: str):
        """Clean up all connections for a session"""
        if session_id in self.active_connections:
            connections = self.get_session_connections(session_id)
            
            # Close all connections
            for conn in connections:
                try:
                    if hasattr(conn, 'close'):
                        await conn.close()
                    elif hasattr(conn, 'disconnect'):
                        await conn.disconnect()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            
            # Clear tracking
            del self.active_connections[session_id]
            if session_id in self.connection_stats:
                del self.connection_stats[session_id]
            
            logger.info(f"🧹 Cleaned up session {session_id}")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of dead connections and old rate limit data"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_dead_connections()
                self._cleanup_rate_limits()
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def _cleanup_dead_connections(self):
        """Remove dead connection references"""
        sessions_to_clean = []
        
        for session_id in list(self.active_connections.keys()):
            dead_refs = set()
            
            for conn_ref in self.active_connections[session_id]:
                if conn_ref() is None:
                    dead_refs.add(conn_ref)
            
            # Remove dead references
            self.active_connections[session_id] -= dead_refs
            
            # Clean up empty sessions
            if not self.active_connections[session_id]:
                sessions_to_clean.append(session_id)
        
        # Remove empty sessions
        for session_id in sessions_to_clean:
            if session_id in self.active_connections:
                del self.active_connections[session_id]
        
        logger.debug(f"🧹 Cleaned up {len(sessions_to_clean)} empty sessions")
    
    def _cleanup_rate_limits(self):
        """Clean up old rate limit entries"""
        current_time = time.time()
        
        for rate_key in list(self.connection_rate_limits.keys()):
            self.connection_rate_limits[rate_key] = [
                conn_time for conn_time in self.connection_rate_limits[rate_key]
                if current_time - conn_time < self.rate_limit_window
            ]
            
            # Remove empty buckets
            if not self.connection_rate_limits[rate_key]:
                del self.connection_rate_limits[rate_key]

# Global connection manager instance
connection_manager = ConnectionManager()

@asynccontextmanager
async def managed_connection(session_id: str, connection_type: str, 
                           connection_obj, client_ip: str = None):
    """Context manager for automatically managing connection lifecycle"""
    
    # Register connection
    if not await connection_manager.register_connection(
        session_id, connection_type, connection_obj, client_ip
    ):
        raise Exception(f"Failed to register {connection_type} connection for session {session_id}")
    
    try:
        yield connection_obj
    finally:
        # Unregister connection
        connection_manager.unregister_connection(session_id, connection_obj)