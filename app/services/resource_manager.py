"""
Resource Manager for efficient handling of video services and memory management
Optimized for concurrent users and cloud deployment
"""

import asyncio
import gc
import psutil
import time
import threading
from typing import Dict, Optional, List
from collections import defaultdict

from app.core.logging import logger
from app.config.settings import settings
from app.services.video_service import VideoService
from app.services.fast_webrtc_service import FastWebRTCService

class ResourceManager:
    """Manages video services and system resources efficiently for multiple users"""
    
    def __init__(self, max_memory_mb: int = None):
        # Video service pools
        self.video_services: Dict[str, VideoService] = {}
        self.webrtc_services: Dict[str, FastWebRTCService] = {}
        
        # Resource tracking
        self.service_clients: Dict[str, set] = defaultdict(set)
        self.service_last_used: Dict[str, float] = {}
        if max_memory_mb is None:
            try:
                self.max_memory_mb = settings.MAX_MEMORY_MB
            except:
                self.max_memory_mb = 2048  # fallback
        else:
            self.max_memory_mb = max_memory_mb
        
        # Cleanup configuration
        try:
            self.idle_timeout = settings.SERVICE_IDLE_TIMEOUT
        except:
            self.idle_timeout = 300  # fallback 5 minutes
        self.cleanup_interval = 60  # 1 minute
        try:
            self.memory_check_interval = settings.MEMORY_CHECK_INTERVAL
        except:
            self.memory_check_interval = 30  # fallback
        
        # Performance metrics
        self.metrics = {
            'services_created': 0,
            'services_destroyed': 0,
            'memory_cleanups': 0,
            'client_connections': 0,
            'client_disconnections': 0
        }
        
        # Background tasks
        self._cleanup_task = None
        self._memory_monitor_task = None
        
        logger.info(f"🎛️ ResourceManager initialized with {self.max_memory_mb}MB memory limit")
    
    def start_background_tasks(self):
        """Start background monitoring tasks when event loop is available"""
        if self._cleanup_task is None and self._memory_monitor_task is None:
            try:
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
                self._memory_monitor_task = asyncio.create_task(self._memory_monitor())
                logger.info("🎛️ ResourceManager background tasks started")
            except RuntimeError:
                logger.warning("Cannot start background tasks - no event loop running")
    
    async def stop_background_tasks(self):
        """Stop background monitoring tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        if self._memory_monitor_task:
            self._memory_monitor_task.cancel()
            try:
                await self._memory_monitor_task
            except asyncio.CancelledError:
                pass
            self._memory_monitor_task = None
        
        logger.info("🎛️ ResourceManager background tasks stopped")
    
    async def get_video_service(self, udid: str, client_id: str) -> VideoService:
        """Get or create a video service for the specified device"""
        
        if udid not in self.video_services:
            # Create new video service
            logger.info(f"🎥 Creating new VideoService for device {udid}")
            
            video_service = VideoService(udid)
            self.video_services[udid] = video_service
            self.metrics['services_created'] += 1
            
            # Start video capture
            if not video_service.start_video_capture():
                logger.error(f"❌ Failed to start video capture for {udid}")
                del self.video_services[udid]
                raise Exception(f"Failed to start video capture for device {udid}")
        
        # Track client usage
        self.service_clients[udid].add(client_id)
        self.service_last_used[udid] = time.time()
        self.metrics['client_connections'] += 1
        
        logger.debug(f"📊 VideoService for {udid} now has {len(self.service_clients[udid])} clients")
        
        return self.video_services[udid]
    
    async def get_webrtc_service(self, udid: str, client_id: str) -> FastWebRTCService:
        """Get or create a WebRTC service for the specified device"""
        
        if udid not in self.webrtc_services:
            # Create new WebRTC service
            logger.info(f"🚀 Creating new FastWebRTCService for device {udid}")
            
            webrtc_service = FastWebRTCService(udid)
            self.webrtc_services[udid] = webrtc_service
            self.metrics['services_created'] += 1
        
        # Track client usage
        self.service_clients[f"webrtc_{udid}"].add(client_id)
        self.service_last_used[f"webrtc_{udid}"] = time.time()
        self.metrics['client_connections'] += 1
        
        return self.webrtc_services[udid]
    
    async def release_video_service(self, udid: str, client_id: str):
        """Release a video service when client disconnects"""
        
        if udid in self.service_clients:
            self.service_clients[udid].discard(client_id)
            self.metrics['client_disconnections'] += 1
            
            logger.debug(f"📊 VideoService for {udid} now has {len(self.service_clients[udid])} clients")
            
            # If no more clients, mark for potential cleanup
            if not self.service_clients[udid]:
                self.service_last_used[udid] = time.time()
                logger.info(f"🔄 VideoService for {udid} marked for cleanup (no active clients)")
    
    async def release_webrtc_service(self, udid: str, client_id: str):
        """Release a WebRTC service when client disconnects"""
        
        webrtc_key = f"webrtc_{udid}"
        if webrtc_key in self.service_clients:
            self.service_clients[webrtc_key].discard(client_id)
            self.metrics['client_disconnections'] += 1
            
            # If no more clients, mark for potential cleanup
            if not self.service_clients[webrtc_key]:
                self.service_last_used[webrtc_key] = time.time()
                logger.info(f"🔄 FastWebRTCService for {udid} marked for cleanup (no active clients)")
    
    async def cleanup_idle_services(self):
        """Clean up services that have been idle for too long"""
        current_time = time.time()
        services_to_cleanup = []
        
        # Check video services
        for udid in list(self.video_services.keys()):
            if (udid in self.service_last_used and 
                not self.service_clients[udid] and
                current_time - self.service_last_used[udid] > self.idle_timeout):
                
                services_to_cleanup.append(('video', udid))
        
        # Check WebRTC services
        for udid in list(self.webrtc_services.keys()):
            webrtc_key = f"webrtc_{udid}"
            if (webrtc_key in self.service_last_used and 
                not self.service_clients[webrtc_key] and
                current_time - self.service_last_used[webrtc_key] > self.idle_timeout):
                
                services_to_cleanup.append(('webrtc', udid))
        
        # Cleanup idle services
        for service_type, udid in services_to_cleanup:
            await self._cleanup_service(service_type, udid)
    
    async def _cleanup_service(self, service_type: str, udid: str):
        """Clean up a specific service"""
        try:
            if service_type == 'video' and udid in self.video_services:
                logger.info(f"🧹 Cleaning up idle VideoService for {udid}")
                
                video_service = self.video_services[udid]
                video_service.stop_video_capture()
                del self.video_services[udid]
                
                # Clean up tracking
                if udid in self.service_clients:
                    del self.service_clients[udid]
                if udid in self.service_last_used:
                    del self.service_last_used[udid]
                
                self.metrics['services_destroyed'] += 1
                
            elif service_type == 'webrtc' and udid in self.webrtc_services:
                logger.info(f"🧹 Cleaning up idle FastWebRTCService for {udid}")
                
                webrtc_service = self.webrtc_services[udid]
                webrtc_service.stop_video_stream()
                del self.webrtc_services[udid]
                
                # Clean up tracking
                webrtc_key = f"webrtc_{udid}"
                if webrtc_key in self.service_clients:
                    del self.service_clients[webrtc_key]
                if webrtc_key in self.service_last_used:
                    del self.service_last_used[webrtc_key]
                
                self.metrics['services_destroyed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up {service_type} service for {udid}: {e}")
    
    async def cleanup_all_services(self):
        """Clean up all services (for shutdown)"""
        logger.info("🧹 Cleaning up all services...")
        
        # Stop all video services
        for udid, video_service in list(self.video_services.items()):
            try:
                video_service.stop_video_capture()
            except Exception as e:
                logger.error(f"Error stopping video service for {udid}: {e}")
        
        # Stop all WebRTC services
        for udid, webrtc_service in list(self.webrtc_services.items()):
            try:
                webrtc_service.stop_video_stream()
            except Exception as e:
                logger.error(f"Error stopping WebRTC service for {udid}: {e}")
        
        # Clear all tracking
        self.video_services.clear()
        self.webrtc_services.clear()
        self.service_clients.clear()
        self.service_last_used.clear()
        
        # Stop background tasks
        await self.stop_background_tasks()
    
    def get_memory_usage(self) -> dict:
        """Get current memory usage statistics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': process.memory_percent(),
            'limit_mb': self.max_memory_mb,
            'available_mb': self.max_memory_mb - (memory_info.rss / 1024 / 1024)
        }
    
    def get_service_stats(self) -> dict:
        """Get service statistics"""
        total_clients = sum(len(clients) for clients in self.service_clients.values())
        
        return {
            'video_services': len(self.video_services),
            'webrtc_services': len(self.webrtc_services),
            'total_clients': total_clients,
            'metrics': self.metrics.copy(),
            'memory': self.get_memory_usage()
        }
    
    async def _periodic_cleanup(self):
        """Background task for periodic cleanup"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_idle_services()
                
                # Force garbage collection periodically
                gc.collect()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in periodic cleanup: {e}")
    
    async def _memory_monitor(self):
        """Background task for memory monitoring"""
        while True:
            try:
                await asyncio.sleep(self.memory_check_interval)
                
                memory_stats = self.get_memory_usage()
                
                # Log memory usage periodically
                if memory_stats['rss_mb'] > 100:  # Only log if using significant memory
                    logger.debug(f"📊 Memory usage: {memory_stats['rss_mb']:.1f}MB "
                               f"({memory_stats['percent']:.1f}%)")
                
                # Force cleanup if memory usage is too high
                if memory_stats['rss_mb'] > self.max_memory_mb * 0.8:  # 80% threshold
                    logger.warning(f"⚠️ High memory usage: {memory_stats['rss_mb']:.1f}MB, "
                                 f"forcing cleanup...")
                    
                    await self.cleanup_idle_services()
                    gc.collect()
                    self.metrics['memory_cleanups'] += 1
                
                # Emergency cleanup if memory usage is critical
                if memory_stats['rss_mb'] > self.max_memory_mb:
                    logger.error(f"🚨 Critical memory usage: {memory_stats['rss_mb']:.1f}MB, "
                               f"emergency cleanup...")
                    
                    # Cleanup services with fewest clients first
                    services_by_clients = []
                    for udid in self.video_services:
                        client_count = len(self.service_clients[udid])
                        services_by_clients.append((client_count, 'video', udid))
                    
                    for udid in self.webrtc_services:
                        webrtc_key = f"webrtc_{udid}"
                        client_count = len(self.service_clients[webrtc_key])
                        services_by_clients.append((client_count, 'webrtc', udid))
                    
                    # Sort by client count and cleanup services with fewer clients
                    services_by_clients.sort(key=lambda x: x[0])
                    
                    for client_count, service_type, udid in services_by_clients[:3]:  # Cleanup up to 3 services
                        if client_count == 0:  # Only cleanup services with no active clients
                            await self._cleanup_service(service_type, udid)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in memory monitor: {e}")

# Global resource manager instance
resource_manager = ResourceManager()