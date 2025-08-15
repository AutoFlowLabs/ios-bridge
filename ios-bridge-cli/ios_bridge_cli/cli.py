"""
Main CLI interface for iOS Bridge CLI tool
"""
import click
import sys
import os
import signal
import time
import subprocess
import psutil
import platform
from typing import Optional
from pathlib import Path

from .client import IOSBridgeClient
from .app_manager import ElectronAppManager
from .exceptions import IOSBridgeError, SessionNotFoundError, ConnectionError


class CLIContext:
    """Shared context for CLI commands"""
    def __init__(self):
        self.client: Optional[IOSBridgeClient] = None
        self.app_manager: Optional[ElectronAppManager] = None
        self.cleanup_handlers = []

    def add_cleanup_handler(self, handler):
        """Add a cleanup handler to be called on exit"""
        self.cleanup_handlers.append(handler)

    def cleanup(self):
        """Run all cleanup handlers"""
        click.echo("🧹 Starting cleanup process...")
        
        # Cleanup recordings first
        if self.client:
            try:
                click.echo("🎬 Stopping any active recordings...")
                import requests
                import time
                
                # Get server URL from client config - handle both old and new client attributes
                server_url = getattr(self.client, 'server_url', None) or getattr(self.client, 'base_url', None)
                if not server_url and hasattr(self.client, 'host') and hasattr(self.client, 'port'):
                    # Fallback for old client structure
                    server_url = f"http://{self.client.host}:{self.client.port}"
                
                if server_url:
                    # Call cleanup endpoint with timeout
                    response = requests.post(
                        f"{server_url}/api/sessions/cleanup-recordings",
                        timeout=3,  # Reduced timeout for faster exit
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code == 200:
                        click.echo("✅ Recording cleanup completed")
                    else:
                        click.echo(f"⚠️ Recording cleanup returned status {response.status_code}")
                else:
                    click.echo("⚠️ Could not determine server URL for cleanup")
                    
            except Exception as e:
                click.echo(f"⚠️ Error during recording cleanup: {e}")
                # Don't let cleanup errors prevent exit
        
        # Stop app manager with force termination
        if self.app_manager:
            try:
                click.echo("🖥️ Stopping desktop app...")
                self.app_manager.stop()
            except Exception as e:
                click.echo(f"⚠️ Error stopping app manager: {e}")
                # Force kill app manager process if it exists
                try:
                    if hasattr(self.app_manager, 'process') and self.app_manager.process:
                        click.echo("⚡ Force terminating desktop app...")
                        self.app_manager.process.kill()
                except:
                    pass
        
        # Run other cleanup handlers
        for handler in self.cleanup_handlers:
            try:
                handler()
            except Exception as e:
                click.echo(f"Cleanup error: {e}", err=True)
        
        click.echo("✅ Cleanup completed")


# Global context instance
cli_context = CLIContext()


def signal_handler(signum, frame):
    """Handle Ctrl+C and other signals"""
    # Only handle signals if not already in cleanup
    if not getattr(signal_handler, 'cleanup_in_progress', False):
        signal_handler.cleanup_in_progress = True
        click.echo("\n🛑 Shutting down iOS Bridge CLI...")
        
        # Set a timeout for cleanup - force exit after 5 seconds
        def force_exit():
            import time
            time.sleep(5)
            click.echo("⚡ Force exiting due to cleanup timeout...")
            os._exit(1)
        
        import threading
        timeout_thread = threading.Thread(target=force_exit, daemon=True)
        timeout_thread.start()
        
        try:
            cli_context.cleanup()
        except Exception as e:
            click.echo(f"⚠️ Error during cleanup: {e}")
        finally:
            # Force exit to ensure we don't get stuck
            os._exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def load_default_server():
    """Load default server from config file"""
    try:
        config_file = Path.home() / '.ios-bridge-cli' / 'config.json'
        if config_file.exists():
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('default_server', 'http://localhost:8000')
    except Exception:
        pass
    return 'http://localhost:8000'


@click.group()
@click.option('--server', '-s', 
              default=None,
              help='iOS Bridge server URL (overrides saved default)')
@click.option('--verbose', '-v', 
              is_flag=True, 
              help='Enable verbose output')
@click.pass_context
def cli(ctx, server: str, verbose: bool):
    """iOS Bridge CLI - Desktop streaming client for iOS simulators
    
    Works on all platforms:
    • macOS: Full functionality (local server + remote client)
    • Windows/Linux: Remote client only
    
    For remote servers: ios-bridge connect <server-url> --save
    """
    
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Use provided server or load from config
    if server is None:
        server = load_default_server()
    
    ctx.obj['server'] = server
    ctx.obj['verbose'] = verbose
    
    # Show platform-specific info
    current_platform = platform.system()
    is_local_server = server.startswith('http://localhost') or server.startswith('http://127.0.0.1')
    
    if verbose:
        click.echo(f"🖥️  Platform: {current_platform}")
        click.echo(f"🔗 Server: {server}")
        
        if current_platform.lower() != 'darwin' and is_local_server:
            click.echo("💡 Tip: Use 'ios-bridge remote-help' for connecting to remote servers")


def get_client(ctx):
    """Get or create the IOSBridge client"""
    if not cli_context.client:
        server = ctx.obj['server']
        verbose = ctx.obj['verbose']
        cli_context.client = IOSBridgeClient(server, verbose=verbose)
        
        if verbose:
            click.echo(f"🔗 Connecting to iOS Bridge server: {server}")
    
    return cli_context.client


def resolve_session_id(ctx, session_id):
    """Resolve session ID with auto-detection for single session scenarios"""
    if session_id:
        return session_id
    
    # Auto-detect session if not provided
    try:
        sessions = get_client(ctx).list_sessions()
        
        if not sessions:
            raise SessionNotFoundError("No active sessions found")
        elif len(sessions) == 1:
            auto_session_id = sessions[0]['session_id']
            click.echo(f"🎯 Auto-detected session: {auto_session_id}")
            return auto_session_id
        else:
            raise SessionNotFoundError(
                f"Multiple sessions found ({len(sessions)}). Please specify a session ID:\n" +
                "\n".join([f"  • {s['session_id']} - {s.get('device_type', 'Unknown')}" for s in sessions]) +
                f"\n\nUse: ios-bridge list  # to see all sessions"
            )
    except Exception as e:
        if isinstance(e, SessionNotFoundError):
            raise
        raise SessionNotFoundError(f"Failed to auto-detect session: {e}")


def find_ios_bridge_server():
    """Find the iOS Bridge server directory"""
    # Look for the server in common locations relative to CLI
    cli_dir = Path(__file__).parent.parent.parent
    
    possible_paths = [
        # If CLI is in ios-bridge/ios-bridge-cli/
        cli_dir.parent / "ios-bridge" / "run.py",
        cli_dir.parent / "run.py",
        
        # If CLI is installed separately but server is in common locations
        Path.home() / "ios-bridge" / "run.py",
        Path.cwd() / "run.py",
        
        # Check current directory and parent directories
        Path.cwd() / "ios-bridge" / "run.py",
        Path.cwd().parent / "ios-bridge" / "run.py",
    ]
    
    for path in possible_paths:
        if path.exists():
            return path.parent
    
    return None


def get_server_processes():
    """Get running iOS Bridge server processes"""
    processes = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    # Look for Python processes running iOS Bridge server
                    if ('python' in proc.info['name'].lower() and 
                        ('run.py' in cmdline or 'app.main:app' in cmdline or 
                         'ios-bridge' in cmdline or 'uvicorn' in cmdline)):
                        # Check if it's likely our server by looking for port 8000 or iOS Bridge
                        if ('8000' in cmdline or 'ios' in cmdline.lower() or 
                            'bridge' in cmdline.lower() or 'app.main' in cmdline):
                            processes.append({
                                'pid': proc.info['pid'],
                                'cmdline': cmdline
                            })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        # If psutil fails, return empty list
        pass
    
    return processes


def is_macos():
    """Check if running on macOS"""
    return platform.system().lower() == 'darwin'


def check_server_command_available():
    """Check if server management commands are available on this platform"""
    if not is_macos():
        click.echo("❌ Server management commands are only available on macOS", err=True)
        click.echo("💡 The iOS Bridge server requires macOS and Xcode/iOS Simulator")
        click.echo("🌐 To connect to a remote server, use: --server https://your-server.com", err=True)
        sys.exit(1)


@cli.command()
@click.argument('session_id', required=False)
@click.option('--quality', '-q',
              type=click.Choice(['low', 'medium', 'high', 'ultra']),
              default='high',
              help='Video streaming quality')
@click.option('--fullscreen', '-f',
              is_flag=True,
              help='Start in fullscreen mode')
@click.option('--always-on-top', '-t',
              is_flag=True,
              help='Keep window always on top')
@click.pass_context
def stream(ctx, session_id: str, quality: str, fullscreen: bool, always_on_top: bool):
    """Stream and control an iOS simulator session in a desktop window (auto-downloads desktop app)"""
    
    server = ctx.obj['server']
    verbose = ctx.obj['verbose']
    
    try:
        # Auto-detect session ID if not provided
        session_id = resolve_session_id(ctx, session_id)
        
        click.echo(f"🚀 Starting iOS Bridge streaming for session: {session_id}")
        
        # Validate session exists
        session_info = get_client(ctx).get_session_info(session_id)
        if not session_info:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        if verbose:
            click.echo(f"📱 Session info: {session_info.get('device_type', 'Unknown')} "
                      f"iOS {session_info.get('ios_version', 'Unknown')}")
        
        # Force production mode when installed via pip to use auto-download
        # Only use dev_mode when explicitly running from source directory
        file_path = Path(__file__).resolve()
        
        # Multiple ways to detect pip/wheel installation
        is_pip_install = (
            'site-packages' in str(file_path) or
            'dist-packages' in str(file_path) or  # Debian/Ubuntu
            '.egg' in str(file_path) or
            '/usr/local/lib/python' in str(file_path) or
            '/usr/lib/python' in str(file_path) or
            str(file_path).endswith('.whl') or  # Direct wheel install
            '/lib/python' in str(file_path)  # Any lib/python path
        )
        
        # Check if running from actual source checkout (very strict)
        current_dir = Path.cwd()
        running_from_source_dir = (
            current_dir.name == "ios-bridge-cli" and
            (current_dir / "pyproject.toml").exists() and
            (current_dir / ".git").exists() and
            str(file_path).startswith(str(current_dir))
        )
        
        # ALWAYS use production mode unless running directly from source directory
        # This ensures pip installs, wheel installs, and local builds all use production mode
        dev_mode = running_from_source_dir and not is_pip_install
        
        if verbose:
            mode = "development (bundled source)" if dev_mode else "production (auto-download)"
            click.echo(f"🔧 Running in {mode} mode")
            click.echo(f"🔍 Debug info:")
            click.echo(f"   File path: {file_path}")
            click.echo(f"   Current dir: {current_dir}")
            click.echo(f"   Is pip install: {is_pip_install}")
            click.echo(f"   Running from source dir: {running_from_source_dir}")
            click.echo(f"   Current dir name: {current_dir.name}")
            click.echo(f"   Pyproject exists: {(current_dir / 'pyproject.toml').exists()}")
            click.echo(f"   Git dir exists: {(current_dir / '.git').exists()}")
        
        # Initialize Electron app manager
        cli_context.app_manager = ElectronAppManager(verbose=verbose, dev_mode=dev_mode)
        
        # Add cleanup handler
        cli_context.add_cleanup_handler(lambda: cli_context.app_manager.stop() if cli_context.app_manager else None)
        
        # Start the Electron app
        config = {
            'sessionId': session_id,
            'serverUrl': server,
            'quality': quality,
            'fullscreen': fullscreen,
            'alwaysOnTop': always_on_top,
            'sessionInfo': session_info
        }
        
        click.echo("🖥️  Opening desktop streaming window...")
        
        # This will block until the window is closed
        try:
            return_code = cli_context.app_manager.start(config)
            if return_code != 0 and verbose:
                click.echo(f"⚠️  Desktop app exited with code: {return_code}")
        except KeyboardInterrupt:
            # Don't call cleanup here - let the global signal handler handle it
            # This prevents double cleanup which causes the infinite loop
            pass
        
    except SessionNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except ConnectionError as e:
        click.echo(f"🔌 Connection error: {e}", err=True)
        sys.exit(1)
    except IOSBridgeError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n🛑 Stream interrupted by user")
        sys.exit(0)
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', '-f',
              type=click.Choice(['json', 'table']),
              default='table',
              help='Output format')
@click.pass_context
def list(ctx, format: str):
    """List all available iOS simulator sessions"""
    
    verbose = ctx.obj['verbose']
    
    try:
        sessions = get_client(ctx).list_sessions()
        
        if not sessions:
            click.echo("📱 No active sessions found")
            return
        
        if format == 'json':
            import json
            click.echo(json.dumps(sessions, indent=2))
        else:
            # Table format - show full session IDs
            click.echo("📱 Active iOS Bridge Sessions:")
            click.echo("-" * 120)
            click.echo(f"{'Session ID':<40} {'Device Type':<25} {'iOS Version':<15} {'Status':<10}")
            click.echo("-" * 120)
            
            for session in sessions:
                session_id = session['session_id']
                device_type = session.get('device_type', 'Unknown')[:24]  # Truncate device type if too long
                ios_version = session.get('ios_version', 'Unknown')[:14]  # Truncate iOS version if too long
                status = 'Online' if session.get('status') == 'healthy' else 'Offline'
                
                click.echo(f"{session_id:<40} {device_type:<25} {ios_version:<15} {status:<10}")
            
            click.echo(f"\n📊 Total: {len(sessions)} sessions")
            
            # Helpful tip for single session
            if len(sessions) == 1:
                click.echo(f"💡 Tip: Since you have only one session, you can use commands without specifying the session ID:")
                click.echo(f"   ios-bridge stream")
                click.echo(f"   ios-bridge info") 
                click.echo(f"   ios-bridge terminate")
            
    except ConnectionError as e:
        click.echo(f"🔌 Connection error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Error listing sessions: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('session_id', required=False)
@click.pass_context
def info(ctx, session_id: str):
    """Show detailed information about a session"""
    
    verbose = ctx.obj['verbose']
    
    try:
        # Auto-detect session ID if not provided
        session_id = resolve_session_id(ctx, session_id)
        
        session_info = get_client(ctx).get_session_info(session_id)
        if not session_info:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        click.echo(f"📱 Session Information: {session_id}")
        click.echo("-" * 50)
        
        info_items = [
            ("Device Type", session_info.get('device_type', 'Unknown')),
            ("iOS Version", session_info.get('ios_version', 'Unknown')),
            ("Device Name", session_info.get('device_name', 'Unknown')),
            ("Status", 'Online' if session_info.get('status') == 'healthy' else 'Offline'),
            ("UDID", session_info.get('udid', 'Unknown')),
            ("Created", f"{session_info.get('uptime', 0):.1f}s ago"),
            ("Installed Apps", len(session_info.get('installed_apps', {}))),
        ]
        
        for key, value in info_items:
            click.echo(f"{key:<15}: {value}")
        
        # Show installed apps if any
        installed_apps = session_info.get('installed_apps', {})
        if installed_apps:
            click.echo("\n📦 Installed Apps:")
            for bundle_id, app_info in installed_apps.items():
                click.echo(f"  • {app_info.get('name', bundle_id)} ({bundle_id})")
    
    except SessionNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Error getting session info: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('session_id', required=False)
@click.option('--output', '-o',
              default='screenshot.png',
              help='Output file path')
@click.pass_context
def screenshot(ctx, session_id: str, output: str):
    """Take a screenshot of the iOS simulator"""
    
    verbose = ctx.obj['verbose']
    
    try:
        # Auto-detect session ID if not provided
        session_id = resolve_session_id(ctx, session_id)
        
        # Validate session exists
        session_info = get_client(ctx).get_session_info(session_id)
        if not session_info:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        click.echo(f"📸 Taking screenshot of session: {session_id}")
        
        # Take screenshot
        success = get_client(ctx).take_screenshot(session_id, output)
        
        if success:
            # Get file size
            file_size = os.path.getsize(output) / 1024  # KB
            click.echo(f"✅ Screenshot saved: {output} ({file_size:.1f} KB)")
        else:
            click.echo("❌ Failed to take screenshot", err=True)
            sys.exit(1)
    
    except SessionNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Error taking screenshot: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', '-f',
              type=click.Choice(['json', 'table']),
              default='table',
              help='Output format')
@click.pass_context
def devices(ctx, format: str):
    """List available device types and iOS versions"""
    
    verbose = ctx.obj['verbose']
    
    try:
        configurations = get_client(ctx).get_configurations()
        
        if not configurations:
            click.echo("📱 No device configurations available")
            return
        
        device_types = configurations.get('device_types', [])
        ios_versions = configurations.get('ios_versions', [])
        
        if format == 'json':
            import json
            click.echo(json.dumps(configurations, indent=2))
        else:
            # Table format
            click.echo("📱 Available iOS Device Configurations:")
            click.echo("-" * 60)
            
            click.echo("Device Types:")
            for device in device_types:
                click.echo(f"  • {device}")
            
            click.echo(f"\niOS Versions:")
            for version in ios_versions:
                click.echo(f"  • {version}")
            
            click.echo(f"\n📊 Total: {len(device_types)} device types, {len(ios_versions)} iOS versions")
            
    except ConnectionError as e:
        click.echo(f"🔌 Connection error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Error listing device configurations: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('device_type')
@click.argument('ios_version')
@click.option('--wait', '-w',
              is_flag=True,
              help='Wait for session to be fully ready')
@click.pass_context
def create(ctx, device_type: str, ios_version: str, wait: bool):
    """Create a new iOS simulator session"""
    
    verbose = ctx.obj['verbose']
    
    try:
        click.echo(f"🚀 Creating iOS simulator session...")
        click.echo(f"   Device: {device_type}")
        click.echo(f"   iOS Version: {ios_version}")
        
        if verbose:
            click.echo("🔍 Validating device configuration...")
        
        # Validate device configuration exists
        configurations = get_client(ctx).get_configurations()
        available_devices = configurations.get('device_types', [])
        available_versions = configurations.get('ios_versions', [])
        
        if device_type not in available_devices:
            click.echo(f"❌ Device type '{device_type}' not available", err=True)
            click.echo(f"Available devices: {', '.join(available_devices)}")
            sys.exit(1)
        
        if ios_version not in available_versions:
            click.echo(f"❌ iOS version '{ios_version}' not available", err=True)
            click.echo(f"Available versions: {', '.join(available_versions)}")
            sys.exit(1)
        
        # Create the session
        result = get_client(ctx).create_session(device_type, ios_version)
        
        if result:
            session_id = result['session_id']
            session_info = result.get('session_info', {})
            
            click.echo(f"✅ Session created successfully!")
            click.echo(f"   Session ID: {session_id}")
            click.echo(f"   Device: {session_info.get('device_type', device_type)}")
            click.echo(f"   iOS Version: {session_info.get('ios_version', ios_version)}")
            click.echo(f"   UDID: {session_info.get('udid', 'Unknown')}")
            
            if wait:
                click.echo("⏳ Waiting for session to be ready...")
                time.sleep(3)  # Give the simulator time to boot
                
                # Validate the session is accessible
                if get_client(ctx).validate_session(session_id):
                    click.echo("✅ Session is ready and accessible!")
                else:
                    click.echo("⚠️  Session created but may still be booting...")
            
            click.echo(f"\n🎮 To stream this session, run:")
            click.echo(f"   ios-bridge stream {session_id}")
            
        else:
            click.echo("❌ Failed to create session", err=True)
            sys.exit(1)
    
    except ConnectionError as e:
        click.echo(f"🔌 Connection error: {e}", err=True)
        sys.exit(1)
    except IOSBridgeError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Error creating session: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('session_id', required=False)
@click.option('--force', '-f',
              is_flag=True,
              help='Force termination without confirmation')
@click.pass_context
def terminate(ctx, session_id: str, force: bool):
    """Terminate an iOS simulator session"""
    
    verbose = ctx.obj['verbose']
    
    try:
        # Auto-detect session ID if not provided
        session_id = resolve_session_id(ctx, session_id)
        
        # Get session info first
        session_info = get_client(ctx).get_session_info(session_id)
        if not session_info:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        if verbose:
            click.echo(f"📱 Session info: {session_info.get('device_type', 'Unknown')} "
                      f"iOS {session_info.get('ios_version', 'Unknown')}")
        
        # Confirm termination unless forced
        if not force:
            device_name = f"{session_info.get('device_type', 'Unknown')} iOS {session_info.get('ios_version', 'Unknown')}"
            if not click.confirm(f"⚠️  Are you sure you want to terminate session {session_id[:12]}... ({device_name})?"):
                click.echo("🛑 Termination cancelled")
                return
        
        click.echo(f"🛑 Terminating session: {session_id}")
        
        # Terminate the session
        success = get_client(ctx).delete_session(session_id)
        
        if success:
            click.echo(f"✅ Session {session_id} terminated successfully")
        else:
            click.echo(f"❌ Failed to terminate session {session_id}", err=True)
            sys.exit(1)
    
    except SessionNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except ConnectionError as e:
        click.echo(f"🔌 Connection error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Error terminating session: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--port', '-p',
              default=8000,
              help='Port to run the server on')
@click.option('--host',
              default='0.0.0.0',
              help='Host to bind the server to')
@click.option('--server-path',
              help='Path to iOS Bridge server directory (auto-detected if not specified)')
@click.option('--background', '-b',
              is_flag=True,
              help='Run server in background')
@click.pass_context
def start_server(ctx, port: int, host: str, server_path: str, background: bool):
    """Start the iOS Bridge server (macOS only)"""
    
    check_server_command_available()
    verbose = ctx.obj['verbose']
    
    try:
        # Find server directory
        if server_path:
            server_dir = Path(server_path)
            if not server_dir.exists():
                click.echo(f"❌ Server path does not exist: {server_path}", err=True)
                sys.exit(1)
        else:
            server_dir = find_ios_bridge_server()
            if not server_dir:
                click.echo("❌ iOS Bridge server not found!", err=True)
                click.echo("Please specify the server path with --server-path or ensure the server is in one of these locations:")
                click.echo("  • ~/ios-bridge/")
                click.echo("  • Current directory")
                click.echo("  • Parent directory")
                sys.exit(1)
        
        run_py = server_dir / "run.py"
        if not run_py.exists():
            click.echo(f"❌ run.py not found in {server_dir}", err=True)
            sys.exit(1)
        
        if verbose:
            click.echo(f"📁 Server directory: {server_dir}")
            click.echo(f"🚀 Starting server on {host}:{port}")
        
        # Check if server is already running
        existing_processes = get_server_processes()
        for proc in existing_processes:
            if str(port) in proc['cmdline']:
                click.echo(f"⚠️  Server appears to already be running on port {port} (PID: {proc['pid']})")
                click.echo(f"   Command: {proc['cmdline']}")
                if not click.confirm("Do you want to continue anyway?"):
                    sys.exit(0)
                break
        
        click.echo(f"🚀 Starting iOS Bridge server on {host}:{port}...")
        
        # Prepare environment
        env = os.environ.copy()
        
        # Build command
        cmd = [
            sys.executable, 
            str(run_py),
            "--host", host,
            "--port", str(port)
        ]
        
        if background:
            # Run in background
            process = subprocess.Popen(
                cmd,
                cwd=server_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Wait a moment to see if it starts successfully
            time.sleep(2)
            
            if process.poll() is None:
                click.echo(f"✅ Server started in background (PID: {process.pid})")
                click.echo(f"🌐 Server URL: http://localhost:{port}")
                click.echo(f"📋 To stop: ios-bridge kill-server")
            else:
                click.echo("❌ Server failed to start in background", err=True)
                sys.exit(1)
        else:
            # Run in foreground
            click.echo(f"🌐 Server will be available at: http://localhost:{port}")
            click.echo("📋 Press Ctrl+C to stop the server")
            
            try:
                subprocess.run(cmd, cwd=server_dir, env=env)
            except KeyboardInterrupt:
                click.echo("\n🛑 Server stopped by user")
    
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Error starting server: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--force', '-f',
              is_flag=True,
              help='Force kill without confirmation')
@click.option('--all', '-a',
              is_flag=True,
              help='Kill all iOS Bridge server processes')
@click.pass_context
def kill_server(ctx, force: bool, all: bool):
    """Stop the iOS Bridge server (macOS only)"""
    
    check_server_command_available()
    verbose = ctx.obj['verbose']
    
    try:
        processes = get_server_processes()
        
        if not processes:
            click.echo("📱 No iOS Bridge server processes found running")
            return
        
        if verbose:
            click.echo(f"🔍 Found {len(processes)} server process(es)")
        
        for i, proc in enumerate(processes, 1):
            click.echo(f"{i}. PID {proc['pid']}: {proc['cmdline']}")
        
        # Confirm unless forced
        if not force and not all:
            if len(processes) == 1:
                if not click.confirm(f"🛑 Kill server process {processes[0]['pid']}?"):
                    click.echo("🛑 Operation cancelled")
                    return
            else:
                click.echo("\nWhich process would you like to kill?")
                click.echo("0. All processes")
                choice = click.prompt("Enter number", type=int, default=0)
                
                if choice == 0:
                    all = True
                elif 1 <= choice <= len(processes):
                    processes = [processes[choice - 1]]
                else:
                    click.echo("❌ Invalid choice", err=True)
                    return
        
        if all and not force:
            if not click.confirm(f"🛑 Kill all {len(processes)} server processes?"):
                click.echo("🛑 Operation cancelled")
                return
        
        # Kill the processes
        killed_count = 0
        failed_count = 0
        
        for proc in processes:
            try:
                pid = proc['pid']
                process = psutil.Process(pid)
                
                if verbose:
                    click.echo(f"🛑 Killing process {pid}...")
                
                # Try graceful termination first
                process.terminate()
                
                try:
                    # Wait up to 3 seconds for graceful shutdown
                    process.wait(timeout=3)
                    click.echo(f"✅ Successfully stopped server (PID: {pid})")
                    killed_count += 1
                except psutil.TimeoutExpired:
                    # Force kill if graceful shutdown failed
                    if verbose:
                        click.echo(f"⚡ Force killing process {pid}...")
                    process.kill()
                    click.echo(f"✅ Force killed server (PID: {pid})")
                    killed_count += 1
                    
            except psutil.NoSuchProcess:
                if verbose:
                    click.echo(f"⚠️  Process {proc['pid']} was already terminated")
                killed_count += 1
            except psutil.AccessDenied:
                click.echo(f"❌ Access denied killing process {proc['pid']}", err=True)
                failed_count += 1
            except Exception as e:
                click.echo(f"❌ Error killing process {proc['pid']}: {e}", err=True)
                failed_count += 1
        
        click.echo(f"\n📊 Summary: {killed_count} killed, {failed_count} failed")
        
        if killed_count > 0:
            click.echo("✅ iOS Bridge server stopped")
    
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Error stopping server: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def server_status(ctx):
    """Check iOS Bridge server status (local or remote)"""
    
    verbose = ctx.obj['verbose']
    server_url = ctx.obj['server']
    
    # Check if we're checking a remote server
    is_remote = not (server_url.startswith('http://localhost') or server_url.startswith('http://127.0.0.1'))
    
    if is_remote:
        click.echo(f"🌐 Checking remote iOS Bridge server: {server_url}")
    else:
        click.echo(f"🖥️  Checking local iOS Bridge server: {server_url}")
    
    try:
        click.echo("📱 iOS Bridge Server Status")
        click.echo("-" * 40)
        
        # Only check for local processes if checking localhost
        if not is_remote and is_macos():
            processes = get_server_processes()
            
            if processes:
                click.echo(f"🟢 Found {len(processes)} local server process(es) running:")
                for i, proc in enumerate(processes, 1):
                    click.echo(f"  {i}. PID {proc['pid']}: {proc['cmdline'][:80]}{'...' if len(proc['cmdline']) > 80 else ''}")
            else:
                click.echo("🔴 No local server processes found")
        elif is_remote:
            click.echo("🌐 Checking remote server (process info not available)")
        else:
            click.echo("ℹ️  Local process checking only available on macOS")
        
        # Test HTTP connection
        click.echo(f"\n🌐 Testing connection to {server_url}...")
        try:
            client = IOSBridgeClient(server_url, verbose=False)
            # The client constructor tests the connection
            click.echo("✅ Server is responding to HTTP requests")
            
            # Get some basic info
            try:
                configurations = client.get_configurations()
                if configurations:
                    device_count = len(configurations.get('device_types', []))
                    version_count = len(configurations.get('ios_versions', []))
                    click.echo(f"📱 Available: {device_count} device types, {version_count} iOS versions")
                
                sessions = client.list_sessions()
                click.echo(f"🎮 Active sessions: {len(sessions)}")
                
            except Exception as e:
                if verbose:
                    click.echo(f"⚠️  Could not get server details: {e}")
        
        except ConnectionError as e:
            click.echo(f"🔴 Server not responding: {e}")
        except Exception as e:
            click.echo(f"🔴 Connection error: {e}")
    
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Error checking server status: {e}", err=True)


@cli.command()
@click.argument('server_url')
@click.option('--save', '-s',
              is_flag=True,
              help='Save this server as default')
@click.pass_context
def connect(ctx, server_url: str, save: bool):
    """Connect to a remote iOS Bridge server"""
    
    verbose = ctx.obj['verbose']
    
    try:
        # Validate and normalize URL
        if not server_url.startswith(('http://', 'https://')):
            server_url = f'https://{server_url}'
        
        click.echo(f"🌐 Connecting to remote iOS Bridge server: {server_url}")
        
        # Test connection
        client = IOSBridgeClient(server_url, verbose=verbose)
        
        # Get server information
        configurations = client.get_configurations()
        sessions = client.list_sessions()
        
        click.echo(f"✅ Successfully connected to remote server!")
        click.echo(f"📱 Available: {len(configurations.get('device_types', []))} device types, {len(configurations.get('ios_versions', []))} iOS versions")
        click.echo(f"🎮 Active sessions: {len(sessions)}")
        
        if save:
            # Save server URL to config file
            config_dir = Path.home() / '.ios-bridge-cli'
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / 'config.json'
            
            config = {'default_server': server_url}
            
            import json
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            click.echo(f"💾 Saved {server_url} as default server")
            click.echo(f"📋 Config saved to: {config_file}")
        
        click.echo(f"\n🚀 You can now use all commands with this server:")
        click.echo(f"   ios-bridge --server {server_url} devices")
        click.echo(f"   ios-bridge --server {server_url} create \"iPhone 14 Pro\" \"18.2\"")
        click.echo(f"   ios-bridge --server {server_url} stream <session_id>")
        
        if save:
            click.echo(f"\n💡 Since you saved it as default, you can also use:")
            click.echo(f"   ios-bridge devices")
            click.echo(f"   ios-bridge create \"iPhone 14 Pro\" \"18.2\"")
    
    except ConnectionError as e:
        click.echo(f"❌ Failed to connect to server: {e}", err=True)
        click.echo(f"💡 Make sure the server URL is correct and accessible")
        sys.exit(1)
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"💥 Connection error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def remote_help(ctx):
    """Show help for connecting to remote iOS Bridge servers"""
    
    click.echo("🌐 iOS Bridge CLI - Remote Server Connection")
    click.echo("=" * 50)
    
    current_platform = platform.system()
    click.echo(f"🖥️  Platform: {current_platform}")
    
    if current_platform.lower() != 'darwin':
        click.echo("💡 Server management is only available on macOS")
        click.echo("   On Windows/Linux, you can only connect to remote servers")
    
    click.echo("\n📡 Connecting to Remote Servers:")
    click.echo("=" * 35)
    
    examples = [
        ("Production Server", "ios-bridge connect https://ios-bridge.yourcompany.com --save"),
        ("Development Server", "ios-bridge connect https://dev.ios-bridge.com:8443"),
        ("Custom Port", "ios-bridge connect https://server.com:9000 --save"),
        ("Check Status", "ios-bridge --server https://your-server.com server-status"),
        ("List Devices", "ios-bridge --server https://your-server.com devices"),
        ("Create Session", "ios-bridge --server https://your-server.com create \"iPhone 14\" \"18.2\""),
        ("Stream Session", "ios-bridge --server https://your-server.com stream <session_id>")
    ]
    
    for title, command in examples:
        click.echo(f"\n• {title}:")
        click.echo(f"  {command}")
    
    click.echo("\n🔧 Configuration:")
    click.echo("=" * 15)
    click.echo("• Save default server: Use --save flag with connect command")
    click.echo("• Config location: ~/.ios-bridge-cli/config.json")
    click.echo("• Override default: Use --server flag with any command")
    
    click.echo("\n🚀 Deployment Information:")
    click.echo("=" * 25)
    click.echo("• iOS Bridge server requires macOS (iOS Simulator dependency)")
    click.echo("• Deploy server on macOS instances (cloud or on-premises)")
    click.echo("• CLI works on Windows/Linux/macOS to connect to remote servers")
    click.echo("• WebSocket support required (ports 80/443 typically)")
    
    click.echo("\n💼 Enterprise Usage:")
    click.echo("=" * 18)
    click.echo("• Deploy server centrally on macOS")
    click.echo("• Teams connect from any OS using CLI")
    click.echo("• Sessions persist across CLI connections")
    click.echo("• Multiple users can share same server instance")



@cli.command()
def version():
    """Show version information"""
    from . import __version__
    click.echo(f"iOS Bridge CLI v{__version__}")


def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"💥 Fatal error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()