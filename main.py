import socket
import atexit
import signal
import sys
import time

from SimulaotrStreamServer import EnhancediOSSimulatorManager

def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def cleanup_on_exit():
    """Cleanup function - PRESERVE simulators"""
    print("\n🧹 Cleaning up server resources (preserving simulators)...")
    try:
        if 'simulator_manager' in globals() and simulator_manager.remote_server:
            simulator_manager.stop_remote_server()  # This only stops server, not simulators
        print(f"💾 {len(simulator_manager.active_sessions) if 'simulator_manager' in globals() else 0} simulator sessions preserved")
    except Exception as e:
        print(f"⚠️  Cleanup error: {e}")
    print("✅ Server cleanup completed - simulators still running")

def force_kill_port(port):
    """Force kill any process using the specified port"""
    try:
        import subprocess
        # Find process using the port
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"🔪 Killing process {pid} using port {port}")
                    subprocess.run(['kill', '-9', pid], check=False)
                    time.sleep(1)
        return True
    except Exception as e:
        print(f"⚠️  Error killing port {port}: {e}")
        return False

def check_port_available(port):
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False

# Register cleanup function
atexit.register(cleanup_on_exit)

# Handle keyboard interrupt more gracefully
def signal_handler(signum, frame):
    print(f"\n🛑 Received signal {signum}, shutting down server (preserving simulators)...")
    cleanup_on_exit()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Check if port is already in use and clean it up
PORT = 5002
if not check_port_available(PORT):
    print(f"⚠️  Port {PORT} is already in use. Attempting to free it...")
    if force_kill_port(PORT):
        time.sleep(2)  # Give it time to release
        if check_port_available(PORT):
            print(f"✅ Port {PORT} is now available")
        else:
            print(f"❌ Could not free port {PORT}. Trying a different port...")
            # Find an available port
            for test_port in range(5002, 5020):
                if check_port_available(test_port):
                    PORT = test_port
                    print(f"✅ Using port {PORT} instead")
                    break

# Create enhanced simulator manager
simulator_manager = EnhancediOSSimulatorManager()

# Check for existing simulators first
existing_sessions = len(simulator_manager.active_sessions)
if existing_sessions > 0:
    print(f"🔄 Found {existing_sessions} existing simulator sessions")
    for session_id, session in simulator_manager.active_sessions.items():
        print(f"   📲 {session.device_type} (iOS {session.ios_version}) - {session_id[:8]}")
else:
    # Start a new simulator only if none exist
    try:
        session_id = simulator_manager.start_simulator("iPhone 14", "18.2")
        print(f"✅ New simulator started with session ID: {session_id}")
    except Exception as e:
        print(f"❌ Failed to start simulator: {e}")
        session_id = None

# Start remote server with hot reload support
print(f"🚀 Starting server on port {PORT} with hot reload...")

# For hot reload, we run the server directly (blocking mode)
try:
    local_ip = get_local_ip()
    print("\n🌐 Remote control server will start at:")
    print(f"   Local: http://localhost:{PORT}")
    print(f"   Network: http://{local_ip}:{PORT}")
    print("🔄 Hot reload enabled - server will restart on file changes")
    print("📱 Existing simulators will be preserved across restarts!")
    print("\n💡 To stop server, press Ctrl+C...")
    
    # Start with hot reload (this blocks)
    simulator_manager.start_remote_server(host="0.0.0.0", port=PORT, reload=True)
    
except KeyboardInterrupt:
    print("\n🛑 Server stopped by user")
    cleanup_on_exit()
except Exception as e:
    print(f"\n❌ Server error: {e}")
    cleanup_on_exit()