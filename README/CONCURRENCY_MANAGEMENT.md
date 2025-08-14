# iOS Bridge Concurrency and Resource Management

## Overview

This document explains the concurrency management and resource optimization systems implemented in iOS Bridge for cloud deployment with multiple concurrent users. These systems ensure reliable performance, prevent resource leaks, and provide robust connection handling for production environments.

## Table of Contents

1. [Connection Management System](#connection-management-system)
2. [Resource Management System](#resource-management-system)
3. [Integration Architecture](#integration-architecture)
4. [Performance Monitoring](#performance-monitoring)
5. [Cloud Deployment Considerations](#cloud-deployment-considerations)
6. [Configuration and Tuning](#configuration-and-tuning)

---

## Connection Management System

### 1. Core Features

The `ConnectionManager` (`app/services/connection_manager.py`) provides:

- **Rate Limiting**: Prevents connection flooding
- **Connection Pooling**: Efficient connection reuse
- **Automatic Cleanup**: Memory leak prevention
- **Session Isolation**: Secure multi-user support
- **Weak References**: Automatic garbage collection

### 2. Connection Limits and Rate Limiting

```python
# Configuration (app/config/settings.py)
MAX_CONNECTIONS_PER_SESSION = 10        # Per session limit
MAX_CONNECTIONS_PER_MINUTE = 20         # Rate limiting window
CONNECTION_CLEANUP_INTERVAL = 30        # Cleanup frequency (seconds)
```

#### Rate Limiting Implementation
```python
def _check_rate_limit(self, session_id: str, client_ip: str) -> bool:
    """
    Prevents connection flooding by tracking connections per minute
    Uses sliding window approach for accurate rate limiting
    """
    current_time = time.time()
    rate_key = f"{session_id}:{client_ip}"
    
    # Clean old entries (sliding window)
    self.connection_rate_limits[rate_key] = [
        conn_time for conn_time in self.connection_rate_limits[rate_key]
        if current_time - conn_time < self.rate_limit_window
    ]
    
    # Check if under limit
    return len(self.connection_rate_limits[rate_key]) < self.max_connections_per_minute
```

### 3. Managed Connection Context

```python
# Usage example
async with managed_connection(session_id, "video_websocket", websocket, client_ip):
    # Connection is automatically tracked and cleaned up
    video_service = await resource_manager.get_video_service(udid, client_id)
    await handle_video_streaming(websocket, video_service)
# Connection is automatically unregistered when context exits
```

#### Benefits:
- **Automatic Registration**: Connections are tracked on entry
- **Rate Limit Enforcement**: Connections denied if limits exceeded
- **Automatic Cleanup**: Resources released on exit (normal or exception)
- **Memory Safety**: Uses weak references to prevent memory leaks

### 4. Connection Statistics and Monitoring

```python
# Real-time connection stats
{
    "total_sessions": 5,
    "total_connections": 23,
    "sessions": {
        "session_123": {
            "total_connections": 8,
            "active_connections": 3,
            "connection_types": {
                "video_websocket": 2,
                "webrtc_websocket": 1,
                "control_websocket": 0
            },
            "first_connection": 1691234567.123,
            "last_connection": 1691234589.456
        }
    },
    "rate_limit_buckets": 12
}
```

---

## Resource Management System

### 1. Core Features

The `ResourceManager` (`app/services/resource_manager.py`) provides:

- **Service Pooling**: Reuse video services across connections
- **Memory Monitoring**: Automatic cleanup based on memory usage
- **Idle Detection**: Clean up unused services
- **Client Tracking**: Track which clients use which services
- **Performance Metrics**: Service creation/destruction tracking

### 2. Service Pooling Architecture

```python
# Service lifecycle management
class ResourceManager:
    def __init__(self):
        # Service pools for reuse
        self.video_services: Dict[str, VideoService] = {}
        self.webrtc_services: Dict[str, FastWebRTCService] = {}
        
        # Client tracking for reference counting
        self.service_clients: Dict[str, set] = defaultdict(set)
        self.service_last_used: Dict[str, float] = {}
```

#### Service Acquisition
```python
async def get_video_service(self, udid: str, client_id: str) -> VideoService:
    """
    Get or create video service with intelligent pooling
    - Reuses existing services when possible
    - Tracks client usage for reference counting
    - Handles service initialization errors gracefully
    """
    
    if udid not in self.video_services:
        # Create new service
        video_service = VideoService(udid)
        
        # Validate service starts successfully
        if not video_service.start_video_capture():
            raise Exception(f"Failed to start video capture for device {udid}")
        
        self.video_services[udid] = video_service
        self.metrics['services_created'] += 1
    
    # Track client usage
    self.service_clients[udid].add(client_id)
    self.service_last_used[udid] = time.time()
    
    return self.video_services[udid]
```

#### Service Release
```python
async def release_video_service(self, udid: str, client_id: str):
    """
    Release service when client disconnects
    - Removes client from tracking
    - Marks service for cleanup if no active clients
    - Implements graceful degradation
    """
    
    if udid in self.service_clients:
        self.service_clients[udid].discard(client_id)
        
        # Mark for cleanup if no active clients
        if not self.service_clients[udid]:
            self.service_last_used[udid] = time.time()
```

### 3. Memory Management and Monitoring

```python
# Configuration
MAX_MEMORY_MB = 2048                    # Memory limit
SERVICE_IDLE_TIMEOUT = 300              # 5 minutes
MEMORY_CHECK_INTERVAL = 30              # 30 seconds
```

#### Memory Monitoring Loop
```python
async def _memory_monitor(self):
    """
    Continuous memory monitoring with tiered cleanup strategy
    """
    while True:
        memory_stats = self.get_memory_usage()
        
        # Warning threshold (80% of limit)
        if memory_stats['rss_mb'] > self.max_memory_mb * 0.8:
            logger.warning(f"High memory usage: {memory_stats['rss_mb']:.1f}MB")
            await self.cleanup_idle_services()
            gc.collect()
        
        # Critical threshold (100% of limit)
        if memory_stats['rss_mb'] > self.max_memory_mb:
            logger.error(f"Critical memory usage: {memory_stats['rss_mb']:.1f}MB")
            await self._emergency_cleanup()
```

#### Emergency Cleanup Strategy
```python
async def _emergency_cleanup(self):
    """
    Emergency cleanup when memory is critical
    - Prioritizes services with fewer active clients
    - Only cleans up services with zero active clients
    - Implements intelligent service selection
    """
    
    # Sort services by client count (cleanup least used first)
    services_by_clients = []
    for udid in self.video_services:
        client_count = len(self.service_clients[udid])
        services_by_clients.append((client_count, 'video', udid))
    
    services_by_clients.sort(key=lambda x: x[0])
    
    # Cleanup up to 3 services with no active clients
    for client_count, service_type, udid in services_by_clients[:3]:
        if client_count == 0:
            await self._cleanup_service(service_type, udid)
```

### 4. Performance Metrics and Statistics

```python
# Resource manager statistics
{
    "video_services": 3,
    "webrtc_services": 2,
    "total_clients": 8,
    "metrics": {
        "services_created": 15,
        "services_destroyed": 12,
        "memory_cleanups": 3,
        "client_connections": 127,
        "client_disconnections": 119
    },
    "memory": {
        "rss_mb": 1247.3,
        "vms_mb": 2048.7,
        "percent": 12.4,
        "limit_mb": 2048,
        "available_mb": 800.7
    }
}
```

---

## Integration Architecture

### 1. WebSocket Endpoint Integration

```python
@app.websocket("/ws/{session_id}/video")
async def video_websocket(websocket: WebSocket, session_id: str):
    """Video WebSocket with full management integration"""
    
    # Validate session
    udid = session_manager.get_session_udid(session_id)
    if not udid:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    await websocket.accept()
    
    # Extract client information for rate limiting
    client_ip = getattr(websocket.client, 'host', None) if websocket.client else None
    
    # Use managed connection context
    async with managed_connection(session_id, "video_websocket", websocket, client_ip):
        # Get pooled video service
        video_service = await resource_manager.get_video_service(udid, f"video_ws_{session_id}")
        device_service = DeviceService(udid)
        
        video_ws = VideoWebSocket(video_service, device_service)
        await video_ws.handle_connection_managed(websocket)
    
    # Automatic cleanup when context exits
    await resource_manager.release_video_service(udid, f"video_ws_{session_id}")
```

### 2. Service Lifecycle Management

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client        │    │ Connection       │    │ Resource        │
│   Connection    │    │ Manager          │    │ Manager         │
│                 │    │                  │    │                 │
│                 │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ WebSocket       │───▶│ │Rate Limiting │ │───▶│ │Service Pool │ │
│ Connection      │    │ │Connection    │ │    │ │Video/WebRTC │ │
│                 │    │ │Tracking      │ │    │ │Services     │ │
│                 │    │ └──────────────┘ │    │ └─────────────┘ │
│                 │    │        │         │    │        │        │
│                 │    │ ┌──────▼──────┐  │    │ ┌──────▼──────┐ │
│ Disconnect      │◀───│ │Auto Cleanup │  │◀───│ │Memory       │ │
│                 │    │ │Weak Refs    │  │    │ │Monitoring   │ │
└─────────────────┘    │ └─────────────┘  │    │ └─────────────┘ │
                       └──────────────────┘    └─────────────────┘
```

### 3. Application Startup and Shutdown

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")
    try:
        session_manager._recover_orphaned_simulators()
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
    
    yield
    
    # Shutdown - Clean up all managed resources
    logger.info("Application shutting down...")
    await resource_manager.cleanup_all_services()
    
    # Log final statistics
    connection_stats = connection_manager.get_connection_stats()
    resource_stats = resource_manager.get_service_stats()
    logger.info(f"Final connection stats: {connection_stats}")
    logger.info(f"Final resource stats: {resource_stats}")
```

---

## Performance Monitoring

### 1. Health Check Endpoint

```http
GET /health
```

```json
{
    "status": "healthy",
    "service": "iOS Remote Control",
    "total_sessions": 5,
    "connections": {
        "total_sessions": 5,
        "total_connections": 23,
        "rate_limit_buckets": 12
    },
    "resources": {
        "video_services": 3,
        "webrtc_services": 2,
        "total_clients": 8,
        "memory": {
            "rss_mb": 1247.3,
            "percent": 12.4,
            "limit_mb": 2048
        }
    }
}
```

### 2. Detailed Statistics Endpoint

```http
GET /stats
```

```json
{
    "success": true,
    "timestamp": 1691234567.123,
    "connection_manager": {
        "total_sessions": 5,
        "total_connections": 23,
        "sessions": {
            "session_123": {
                "total_connections": 8,
                "active_connections": 3,
                "connection_types": {
                    "video_websocket": 2,
                    "webrtc_websocket": 1
                }
            }
        }
    },
    "resource_manager": {
        "video_services": 3,
        "webrtc_services": 2,
        "metrics": {
            "services_created": 15,
            "services_destroyed": 12,
            "memory_cleanups": 3
        },
        "memory": {
            "rss_mb": 1247.3,
            "available_mb": 800.7
        }
    }
}
```

### 3. Real-time Monitoring Logs

```
2025-08-13 10:15:23,456 - app.services.connection_manager - INFO - ✅ Registered video_websocket connection for session abc123 (3/10)
2025-08-13 10:15:23,478 - app.services.resource_manager - INFO - 🎥 Creating new VideoService for device 419CE000-76DA-467A-A29F-E4B62087C8AD
2025-08-13 10:15:35,123 - app.services.resource_manager - DEBUG - 📊 Memory usage: 1247.3MB (12.4%)
2025-08-13 10:16:45,789 - app.services.resource_manager - INFO - 🔄 VideoService for 419CE000-76DA-467A-A29F-E4B62087C8AD marked for cleanup (no active clients)
2025-08-13 10:17:15,456 - app.services.resource_manager - INFO - 🧹 Cleaning up idle VideoService for 419CE000-76DA-467A-A29F-E4B62087C8AD
```

---

## Cloud Deployment Considerations

### 1. Scalability Design

#### Horizontal Scaling
- **Session Isolation**: Each session is independent and can be load-balanced
- **Stateless Design**: Connection and resource managers are per-instance
- **Resource Limits**: Configurable memory and connection limits per instance

#### Vertical Scaling  
- **Memory Management**: Automatic cleanup prevents memory leaks
- **Service Pooling**: Efficient resource reuse for high concurrency
- **Performance Monitoring**: Real-time metrics for scaling decisions

### 2. Production Configuration

```python
# Production settings (app/config/settings.py)
class ProductionSettings:
    # Increased limits for cloud deployment
    MAX_CONNECTIONS_PER_SESSION = 15        # Higher per-session limit
    MAX_CONNECTIONS_PER_MINUTE = 50         # Higher rate limit
    MAX_MEMORY_MB = 4096                    # 4GB memory limit
    SERVICE_IDLE_TIMEOUT = 600              # 10-minute idle timeout
    CONNECTION_CLEANUP_INTERVAL = 60        # More frequent cleanup
    MEMORY_CHECK_INTERVAL = 30              # Regular memory monitoring
```

### 3. Cloud-Specific Optimizations

#### Load Balancer Configuration
```nginx
# nginx.conf example
upstream ios_bridge_backend {
    # Sticky sessions for WebSocket connections
    ip_hash;
    server 10.0.1.10:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8000 max_fails=3 fail_timeout=30s;
}

server {
    location /ws/ {
        proxy_pass http://ios_bridge_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

#### Container Resource Limits
```yaml
# docker-compose.yml
services:
  ios-bridge:
    image: ios-bridge:latest
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
    environment:
      - MAX_MEMORY_MB=3584  # Leave 512MB for system
      - MAX_CONNECTIONS_PER_SESSION=15
      - MAX_CONNECTIONS_PER_MINUTE=50
```

### 4. Monitoring and Alerting

#### Key Metrics to Monitor
- **Connection Count**: Total active connections per instance
- **Memory Usage**: RSS memory consumption vs. limits
- **Service Pool Size**: Number of active video/WebRTC services
- **Rate Limit Violations**: Connection attempts denied per minute
- **Error Rates**: WebSocket connection failures and service startup failures

#### Alert Thresholds
```yaml
alerts:
  - name: high_memory_usage
    condition: memory_usage_percent > 80
    severity: warning
    
  - name: critical_memory_usage
    condition: memory_usage_percent > 95
    severity: critical
    
  - name: connection_limit_exceeded
    condition: rate_limit_violations > 10/minute
    severity: warning
    
  - name: service_startup_failures
    condition: service_creation_failures > 5/minute
    severity: critical
```

---

## Configuration and Tuning

### 1. Performance Tuning Guidelines

#### Memory-Optimized Configuration
```python
# For memory-constrained environments
MAX_MEMORY_MB = 1024                    # 1GB limit
SERVICE_IDLE_TIMEOUT = 180              # 3-minute timeout
MAX_CONNECTIONS_PER_SESSION = 5         # Lower connection limit
MEMORY_CHECK_INTERVAL = 15              # Frequent memory checks
```

#### High-Concurrency Configuration
```python
# For high-concurrency environments
MAX_CONNECTIONS_PER_SESSION = 25        # Higher per-session limit
MAX_CONNECTIONS_PER_MINUTE = 100        # Higher rate limit
MAX_MEMORY_MB = 8192                    # 8GB memory limit
SERVICE_IDLE_TIMEOUT = 900              # 15-minute timeout
```

#### Low-Latency Configuration
```python
# For latency-sensitive applications
CONNECTION_CLEANUP_INTERVAL = 10        # Aggressive cleanup
MEMORY_CHECK_INTERVAL = 10              # Frequent monitoring
SERVICE_IDLE_TIMEOUT = 60               # Quick service cleanup
```

### 2. Environment-Specific Settings

#### Development Environment
```bash
export MAX_MEMORY_MB=512
export MAX_CONNECTIONS_PER_SESSION=3
export SERVICE_IDLE_TIMEOUT=60
export LOG_LEVEL=DEBUG
```

#### Staging Environment
```bash
export MAX_MEMORY_MB=2048
export MAX_CONNECTIONS_PER_SESSION=10
export SERVICE_IDLE_TIMEOUT=300
export LOG_LEVEL=INFO
```

#### Production Environment
```bash
export MAX_MEMORY_MB=4096
export MAX_CONNECTIONS_PER_SESSION=15
export MAX_CONNECTIONS_PER_MINUTE=50
export SERVICE_IDLE_TIMEOUT=600
export LOG_LEVEL=WARNING
```

### 3. Monitoring and Optimization

#### Key Performance Indicators (KPIs)
1. **Connection Success Rate**: >99% connection establishment success
2. **Memory Efficiency**: <80% memory utilization under normal load
3. **Service Reuse Rate**: >70% of services reused from pool
4. **Cleanup Effectiveness**: <5% memory growth per hour
5. **Rate Limit Compliance**: <1% connections denied due to rate limits

#### Optimization Strategies
1. **Service Pool Sizing**: Monitor service creation/destruction ratio
2. **Memory Threshold Tuning**: Adjust cleanup thresholds based on usage patterns
3. **Connection Limit Adjustment**: Balance between user experience and resource usage
4. **Idle Timeout Optimization**: Find optimal balance between responsiveness and resource conservation

---

## Summary

The iOS Bridge concurrency and resource management systems provide a robust foundation for cloud deployment with multiple concurrent users. Key benefits include:

- **Reliability**: Automatic cleanup prevents resource leaks and memory issues
- **Scalability**: Configurable limits and efficient pooling support high concurrency
- **Monitoring**: Comprehensive metrics and health checks enable proactive management
- **Production-Ready**: Battle-tested patterns for cloud deployment and operations

These systems ensure that your iOS Bridge deployment can handle concurrent users reliably while maintaining optimal performance and resource utilization in cloud environments.