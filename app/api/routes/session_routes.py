import io
import shutil
import subprocess
import time
import zipfile
from fastapi import APIRouter, HTTPException, Response, UploadFile, File, Form
from typing import List, Optional
import tempfile
import os
from app.services.session_manager import session_manager
from app.models.responses import *
from app.core.logging import logger

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.get("/configurations")
async def get_configurations():
    """Get available device types and iOS versions"""
    try:
        configurations = session_manager.get_available_configurations()
        return {
            "success": True,
            "configurations": configurations
        }
    except Exception as e:
        logger.error(f"Error getting configurations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
@router.post("/create")
async def create_session(device_type: str = Form(...), ios_version: str = Form(...)):
    """Create a new simulator session"""
    try:
        session_id = session_manager.create_session(device_type, ios_version)
        session_info = session_manager.get_session_info(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "session_info": session_info
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_sessions():
    """List all active sessions"""
    try:
        sessions = session_manager.list_sessions()
        return {
            "success": True,
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recover-orphaned")
async def recover_orphaned_simulators():
    """Manually trigger recovery of orphaned simulators"""
    try:
        recovered_count = session_manager.recover_orphaned_simulators()
        return {
            "success": True,
            "message": f"Recovered {recovered_count} orphaned simulator sessions",
            "recovered_count": recovered_count
        }
    except Exception as e:
        logger.error(f"Error recovering orphaned simulators: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}")
async def get_session_info(session_id: str):
    """Get detailed information about a session"""
    try:
        session_info = session_manager.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "success": True,
            "session": session_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a simulator session"""
    try:
        success = session_manager.delete_session(session_id)
        return {
            "success": success,
            "message": f"Session {session_id} deleted" if success else "Failed to delete session"
        }
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/")
async def delete_all_sessions():
    """Delete all simulator sessions"""
    try:
        count = session_manager.delete_all_sessions()
        return {
            "success": True,
            "deleted_count": count,
            "message": f"Deleted {count} sessions"
        }
    except Exception as e:
        logger.error(f"Error deleting all sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/{session_id}/apps/install")
async def install_app(
    session_id: str, 
    ipa_file: UploadFile = File(None),
    app_bundle: UploadFile = File(None)
):
    """Install an IPA file or ZIP file containing APP bundle to a session"""
    try:
        # Validate session exists
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Determine which file was uploaded
        if ipa_file and ipa_file.filename:
            uploaded_file = ipa_file
            file_type = 'ipa'
        elif app_bundle and app_bundle.filename:
            uploaded_file = app_bundle  
            file_type = 'zip'
        else:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            
            if file_type == 'ipa':
                # Handle IPA file - save and use SessionManager
                temp_file_path = os.path.join(temp_dir, uploaded_file.filename)
                
                # Save uploaded IPA file
                with open(temp_file_path, 'wb') as f:
                    content = await uploaded_file.read()
                    f.write(content)
                
                # Use SessionManager's install_app method
                result = session_manager.install_app(session_id, temp_file_path)
                
            elif file_type == 'zip':
                # Handle ZIP file containing .app bundle
                temp_zip_path = os.path.join(temp_dir, uploaded_file.filename)
                
                # Save uploaded ZIP file
                with open(temp_zip_path, 'wb') as f:
                    content = await uploaded_file.read()
                    f.write(content)
                
                # Extract ZIP file
                extract_dir = os.path.join(temp_dir, 'extracted')
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Find the .app bundle in extracted files
                app_bundle_path = None
                for item in os.listdir(extract_dir):
                    item_path = os.path.join(extract_dir, item)
                    if item.endswith('.app') and os.path.isdir(item_path):
                        app_bundle_path = item_path
                        break
                
                if not app_bundle_path:
                    raise HTTPException(
                        status_code=400, 
                        detail="No .app bundle found in ZIP file"
                    )
                
                # Use SessionManager's install_app method
                result = session_manager.install_app(session_id, app_bundle_path)
        
        # Check the result from SessionManager
        if result['success']:
            return {
                "success": True,
                "message": result.get('message', f"{file_type.upper()} installed successfully"),
                "app_info": result.get('app_info'),
                "compatibility": result.get('compatibility'),
                "installed_app": result.get('installed_app')
            }
        else:
            # Return the detailed error from SessionManager
            raise HTTPException(
                status_code=500,
                detail=result.get('message', f"Failed to install {file_type.upper()}")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing app: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/apps/install-and-launch")
async def install_and_launch_app(
    session_id: str, 
    ipa_file: UploadFile = File(None),
    app_bundle: UploadFile = File(None)
):
    """Install an IPA file or ZIP file containing APP bundle to a session and immediately launch it"""
    try:
        # Validate session exists
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Determine which file was uploaded
        if ipa_file and ipa_file.filename:
            uploaded_file = ipa_file
            file_type = 'ipa'
        elif app_bundle and app_bundle.filename:
            uploaded_file = app_bundle  
            file_type = 'zip'
        else:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        # Get the list of apps BEFORE installation to compare
        try:
            apps_before = session_manager.list_installed_apps(session_id)
            apps_before_bundle_ids = set()
            if apps_before:
                for app in apps_before:
                    if isinstance(app, dict):
                        bundle_id = app.get('bundle_id')
                    else:
                        bundle_id = getattr(app, 'bundle_id', None)
                    if bundle_id:
                        apps_before_bundle_ids.add(bundle_id)
            logger.info(f"Apps before installation: {len(apps_before_bundle_ids)} apps")
        except Exception as e:
            logger.error(f"Failed to get apps list before installation: {e}")
            apps_before_bundle_ids = set()
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            
            if file_type == 'ipa':
                # Handle IPA file - save and use SessionManager
                temp_file_path = os.path.join(temp_dir, uploaded_file.filename)
                
                # Save uploaded IPA file
                with open(temp_file_path, 'wb') as f:
                    content = await uploaded_file.read()
                    f.write(content)
                
                # Use SessionManager's install_app method
                install_result = session_manager.install_app(session_id, temp_file_path)
                
            elif file_type == 'zip':
                # Handle ZIP file containing .app bundle
                temp_zip_path = os.path.join(temp_dir, uploaded_file.filename)
                
                # Save uploaded ZIP file
                with open(temp_zip_path, 'wb') as f:
                    content = await uploaded_file.read()
                    f.write(content)
                
                # Extract ZIP file
                extract_dir = os.path.join(temp_dir, 'extracted')
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Find the .app bundle in extracted files
                app_bundle_path = None
                for item in os.listdir(extract_dir):
                    item_path = os.path.join(extract_dir, item)
                    if item.endswith('.app') and os.path.isdir(item_path):
                        app_bundle_path = item_path
                        break
                
                if not app_bundle_path:
                    raise HTTPException(
                        status_code=400, 
                        detail="No .app bundle found in ZIP file"
                    )
                
                # Use SessionManager's install_app method
                install_result = session_manager.install_app(session_id, app_bundle_path)
        
        # Check the installation result
        if not install_result['success']:
            raise HTTPException(
                status_code=500,
                detail=install_result.get('message', f"Failed to install {file_type.upper()}")
            )
        
        # Try multiple ways to get the bundle ID
        bundle_id = None
        
        # Method 1: From installed_app
        if 'installed_app' in install_result and install_result['installed_app']:
            if isinstance(install_result['installed_app'], dict):
                bundle_id = install_result['installed_app'].get('bundle_id')
            else:
                # If it's an object with attributes
                bundle_id = getattr(install_result['installed_app'], 'bundle_id', None)
        
        # Method 2: From app_info
        if not bundle_id and 'app_info' in install_result and install_result['app_info']:
            if isinstance(install_result['app_info'], dict):
                bundle_id = install_result['app_info'].get('bundle_id')
            else:
                # If it's an object with attributes
                bundle_id = getattr(install_result['app_info'], 'bundle_id', None)
        
        # Method 3: Find the newly installed app by comparing before/after lists
        if not bundle_id:
            logger.info("Attempting to find bundle ID by comparing before/after apps lists")
            try:
                # Get the list of apps AFTER installation
                apps_after = session_manager.list_installed_apps(session_id)
                if apps_after:
                    # Find apps that weren't there before
                    for app in apps_after:
                        if isinstance(app, dict):
                            app_bundle_id = app.get('bundle_id')
                            app_name = app.get('app_name', 'Unknown')
                        else:
                            app_bundle_id = getattr(app, 'bundle_id', None)
                            app_name = getattr(app, 'app_name', 'Unknown')
                        
                        # If this bundle_id wasn't in the before list, it's the new app
                        if app_bundle_id and app_bundle_id not in apps_before_bundle_ids:
                            logger.info(f"Found newly installed app: {app_name} with bundle_id: {app_bundle_id}")
                            bundle_id = app_bundle_id
                            break
                        
            except Exception as e:
                logger.error(f"Failed to compare apps lists for bundle ID extraction: {e}")
        
        # Method 4: Parse from app path if it's a .app bundle installation
        if not bundle_id and file_type == 'zip':
            try:
                # Try to extract bundle ID from Info.plist in the app bundle
                info_plist_path = os.path.join(app_bundle_path, 'Info.plist')
                if os.path.exists(info_plist_path):
                    import plistlib
                    with open(info_plist_path, 'rb') as f:
                        plist_data = plistlib.load(f)
                        bundle_id = plist_data.get('CFBundleIdentifier')
                        logger.info(f"Extracted bundle ID from Info.plist: {bundle_id}")
            except Exception as e:
                logger.error(f"Failed to extract bundle ID from Info.plist: {e}")
        
        # Method 5: Fallback - look for apps with specific patterns
        if not bundle_id:
            logger.info("Using fallback method to find bundle ID")
            try:
                apps_after = session_manager.list_installed_apps(session_id)
                if apps_after:
                    # Look for apps that match common patterns for user-installed apps
                    for app in apps_after:
                        if isinstance(app, dict):
                            app_bundle_id = app.get('bundle_id', '')
                            app_name = app.get('app_name', '')
                        else:
                            app_bundle_id = getattr(app, 'bundle_id', '')
                            app_name = getattr(app, 'app_name', '')
                        
                        # Look for non-Apple bundle IDs or apps that match our naming
                        if (app_bundle_id and 
                            (not app_bundle_id.startswith('com.apple.') or 
                             'calculator' in app_name.lower() or 
                             'calculator' in app_bundle_id.lower() or
                             'nativebridge' in app_bundle_id.lower())):
                            logger.info(f"Fallback found potential app: {app_name} with bundle_id: {app_bundle_id}")
                            bundle_id = app_bundle_id
                            break
                            
            except Exception as e:
                logger.error(f"Fallback method failed: {e}")
        
        if not bundle_id:
            # Log the full install result for debugging
            logger.error(f"Could not determine bundle ID. Install result: {install_result}")
            raise HTTPException(
                status_code=500,
                detail="App installed successfully but could not determine bundle ID for launch. Check logs for details."
            )
        
        # Launch the app
        logger.info(f"Attempting to launch app with bundle ID: {bundle_id}")
        launch_success = session_manager.launch_app(session_id, bundle_id)
        
        if launch_success:
            return {
                "success": True,
                "message": f"{file_type.upper()} installed and launched successfully",
                "bundle_id": bundle_id,
                "app_info": install_result.get('app_info'),
                "compatibility": install_result.get('compatibility'),
                "installed_app": install_result.get('installed_app'),
                "launched": True
            }
        else:
            # App was installed but launch failed
            return {
                "success": True,
                "message": f"{file_type.upper()} installed successfully but failed to launch automatically",
                "bundle_id": bundle_id,
                "app_info": install_result.get('app_info'),
                "compatibility": install_result.get('compatibility'),
                "installed_app": install_result.get('installed_app'),
                "launched": False,
                "launch_error": "Launch command failed"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing and launching app: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/{session_id}/apps")
async def list_apps(session_id: str):
    """List installed apps in a session"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        apps = session_manager.list_installed_apps(session_id)
        return {
            "success": True,
            "apps": apps
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing apps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/apps/{bundle_id}/launch")
async def launch_app(session_id: str, bundle_id: str):
    """Launch an app in a session"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        success = session_manager.launch_app(session_id, bundle_id)
        return {
            "success": success,
            "message": f"App {bundle_id} launched" if success else "Failed to launch app"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error launching app: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/apps/{bundle_id}/terminate")
async def terminate_app(session_id: str, bundle_id: str):
    """Terminate an app in a session"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        success = session_manager.terminate_app(session_id, bundle_id)
        return {
            "success": success,
            "message": f"App {bundle_id} terminated" if success else "Failed to terminate app"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating app: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/apps/install-and-launch")
async def install_and_launch_app(
    session_id: str, 
    ipa_file: UploadFile = File(None),
    app_bundle: UploadFile = File(None)
):
    """Install an IPA file or ZIP file containing APP bundle to a session and immediately launch it"""
    try:
        # Validate session exists
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Determine which file was uploaded
        if ipa_file and ipa_file.filename:
            uploaded_file = ipa_file
            file_type = 'ipa'
        elif app_bundle and app_bundle.filename:
            uploaded_file = app_bundle  
            file_type = 'zip'
        else:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        # Get the list of apps BEFORE installation to compare
        try:
            apps_before = session_manager.list_installed_apps(session_id)
            apps_before_bundle_ids = set()
            if apps_before:
                for app in apps_before:
                    if isinstance(app, dict):
                        bundle_id = app.get('bundle_id')
                    else:
                        bundle_id = getattr(app, 'bundle_id', None)
                    if bundle_id:
                        apps_before_bundle_ids.add(bundle_id)
            logger.info(f"Apps before installation: {len(apps_before_bundle_ids)} apps")
        except Exception as e:
            logger.error(f"Failed to get apps list before installation: {e}")
            apps_before_bundle_ids = set()
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            
            if file_type == 'ipa':
                # Handle IPA file - save and use SessionManager
                temp_file_path = os.path.join(temp_dir, uploaded_file.filename)
                
                # Save uploaded IPA file
                with open(temp_file_path, 'wb') as f:
                    content = await uploaded_file.read()
                    f.write(content)
                
                # Use SessionManager's install_app method
                install_result = session_manager.install_app(session_id, temp_file_path)
                
            elif file_type == 'zip':
                # Handle ZIP file containing .app bundle
                temp_zip_path = os.path.join(temp_dir, uploaded_file.filename)
                
                # Save uploaded ZIP file
                with open(temp_zip_path, 'wb') as f:
                    content = await uploaded_file.read()
                    f.write(content)
                
                # Extract ZIP file
                extract_dir = os.path.join(temp_dir, 'extracted')
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Find the .app bundle in extracted files
                app_bundle_path = None
                for item in os.listdir(extract_dir):
                    item_path = os.path.join(extract_dir, item)
                    if item.endswith('.app') and os.path.isdir(item_path):
                        app_bundle_path = item_path
                        break
                
                if not app_bundle_path:
                    raise HTTPException(
                        status_code=400, 
                        detail="No .app bundle found in ZIP file"
                    )
                
                # Use SessionManager's install_app method
                install_result = session_manager.install_app(session_id, app_bundle_path)
        
        # Check the installation result
        if not install_result['success']:
            raise HTTPException(
                status_code=500,
                detail=install_result.get('message', f"Failed to install {file_type.upper()}")
            )
        
        # Try multiple ways to get the bundle ID
        bundle_id = None
        
        # Method 1: From installed_app
        if 'installed_app' in install_result and install_result['installed_app']:
            if isinstance(install_result['installed_app'], dict):
                bundle_id = install_result['installed_app'].get('bundle_id')
            else:
                # If it's an object with attributes
                bundle_id = getattr(install_result['installed_app'], 'bundle_id', None)
        
        # Method 2: From app_info
        if not bundle_id and 'app_info' in install_result and install_result['app_info']:
            if isinstance(install_result['app_info'], dict):
                bundle_id = install_result['app_info'].get('bundle_id')
            else:
                # If it's an object with attributes
                bundle_id = getattr(install_result['app_info'], 'bundle_id', None)
        
        # Method 3: Find the newly installed app by comparing before/after lists
        if not bundle_id:
            logger.info("Attempting to find bundle ID by comparing before/after apps lists")
            try:
                # Get the list of apps AFTER installation
                apps_after = session_manager.list_installed_apps(session_id)
                if apps_after:
                    # Find apps that weren't there before
                    for app in apps_after:
                        if isinstance(app, dict):
                            app_bundle_id = app.get('bundle_id')
                            app_name = app.get('app_name', 'Unknown')
                        else:
                            app_bundle_id = getattr(app, 'bundle_id', None)
                            app_name = getattr(app, 'app_name', 'Unknown')
                        
                        # If this bundle_id wasn't in the before list, it's the new app
                        if app_bundle_id and app_bundle_id not in apps_before_bundle_ids:
                            logger.info(f"Found newly installed app: {app_name} with bundle_id: {app_bundle_id}")
                            bundle_id = app_bundle_id
                            break
                        
            except Exception as e:
                logger.error(f"Failed to compare apps lists for bundle ID extraction: {e}")
        
        # Method 4: Parse from app path if it's a .app bundle installation
        if not bundle_id and file_type == 'zip':
            try:
                # Try to extract bundle ID from Info.plist in the app bundle
                info_plist_path = os.path.join(app_bundle_path, 'Info.plist')
                if os.path.exists(info_plist_path):
                    import plistlib
                    with open(info_plist_path, 'rb') as f:
                        plist_data = plistlib.load(f)
                        bundle_id = plist_data.get('CFBundleIdentifier')
                        logger.info(f"Extracted bundle ID from Info.plist: {bundle_id}")
            except Exception as e:
                logger.error(f"Failed to extract bundle ID from Info.plist: {e}")
        
        # Method 5: Fallback - look for apps with specific patterns
        if not bundle_id:
            logger.info("Using fallback method to find bundle ID")
            try:
                apps_after = session_manager.list_installed_apps(session_id)
                if apps_after:
                    # Look for apps that match common patterns for user-installed apps
                    for app in apps_after:
                        if isinstance(app, dict):
                            app_bundle_id = app.get('bundle_id', '')
                            app_name = app.get('app_name', '')
                        else:
                            app_bundle_id = getattr(app, 'bundle_id', '')
                            app_name = getattr(app, 'app_name', '')
                        
                        # Look for non-Apple bundle IDs or apps that match our naming
                        if (app_bundle_id and 
                            (not app_bundle_id.startswith('com.apple.') or 
                             'calculator' in app_name.lower() or 
                             'calculator' in app_bundle_id.lower() or
                             'nativebridge' in app_bundle_id.lower())):
                            logger.info(f"Fallback found potential app: {app_name} with bundle_id: {app_bundle_id}")
                            bundle_id = app_bundle_id
                            break
                            
            except Exception as e:
                logger.error(f"Fallback method failed: {e}")
        
        if not bundle_id:
            # Log the full install result for debugging
            logger.error(f"Could not determine bundle ID. Install result: {install_result}")
            raise HTTPException(
                status_code=500,
                detail="App installed successfully but could not determine bundle ID for launch. Check logs for details."
            )
        
        # Launch the app
        logger.info(f"Attempting to launch app with bundle ID: {bundle_id}")
        launch_success = session_manager.launch_app(session_id, bundle_id)
        
        if launch_success:
            return {
                "success": True,
                "message": f"{file_type.upper()} installed and launched successfully",
                "bundle_id": bundle_id,
                "app_info": install_result.get('app_info'),
                "compatibility": install_result.get('compatibility'),
                "installed_app": install_result.get('installed_app'),
                "launched": True
            }
        else:
            # App was installed but launch failed
            return {
                "success": True,
                "message": f"{file_type.upper()} installed successfully but failed to launch automatically",
                "bundle_id": bundle_id,
                "app_info": install_result.get('app_info'),
                "compatibility": install_result.get('compatibility'),
                "installed_app": install_result.get('installed_app'),
                "launched": False,
                "launch_error": "Launch command failed"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing and launching app: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# Replace the uninstall_app endpoint around line 600:

@router.delete("/{session_id}/apps/{bundle_id}")
async def uninstall_app(session_id: str, bundle_id: str):
    """Uninstall an app from a session"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if app is installed first and get app name
        app_name = None
        if not session_manager.is_app_installed(session_id, bundle_id):
            raise HTTPException(
                status_code=404,
                detail=f"App with bundle ID '{bundle_id}' not found"
            )
        
        # Get app name before uninstalling
        try:
            apps = session_manager.list_installed_apps(session_id)
            if apps:
                for app in apps:
                    if isinstance(app, dict):
                        app_bundle_id = app.get('bundle_id')
                        app_name = app.get('app_name', 'Unknown App')
                    else:
                        app_bundle_id = getattr(app, 'bundle_id', None)
                        app_name = getattr(app, 'app_name', 'Unknown App')
                    
                    if app_bundle_id == bundle_id:
                        break
        except Exception as e:
            logger.warning(f"Could not get app name for {bundle_id}: {e}")
        
        # Use SessionManager method (returns boolean)
        success = session_manager.uninstall_app(session_id, bundle_id)
        
        if success:
            return {
                "success": True,
                "message": f"App '{app_name or bundle_id}' uninstalled successfully",
                "bundle_id": bundle_id,
                "app_name": app_name
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to uninstall app '{app_name or bundle_id}'"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uninstalling app: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/refresh")
async def refresh_sessions():
    """Refresh session states and remove invalid ones"""
    removed_count = session_manager.refresh_session_states()
    return {
        "message": f"Refreshed sessions, removed {removed_count} invalid sessions",
        "removed_count": removed_count
    }

@router.post("/cleanup")
async def cleanup_storage():
    """Clean up old storage files"""
    session_manager.cleanup_storage()
    return {"message": "Storage cleanup completed"}

@router.get("/storage/info")
async def get_storage_info():
    """Get information about session storage"""
    storage_dir = session_manager.storage_dir
    sessions_file = session_manager.sessions_file
    
    storage_info = {
        "storage_directory": str(storage_dir),
        "sessions_file": str(sessions_file),
        "sessions_file_exists": sessions_file.exists(),
        "active_sessions_count": len(session_manager.active_sessions)
    }
    
    if sessions_file.exists():
        storage_info["sessions_file_size"] = sessions_file.stat().st_size
        storage_info["sessions_file_modified"] = sessions_file.stat().st_mtime
    
    # Count backup files
    backup_files = list(storage_dir.glob("sessions_backup_*.json"))
    storage_info["backup_files_count"] = len(backup_files)
    
    return storage_info


@router.post("/{session_id}/url/open")
async def open_url(session_id: str, url: str = Form(...)):
    """Open a URL on the simulator (web URL or custom URL scheme)"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Validate URL
        url = url.strip()
        if not url:
            raise HTTPException(status_code=400, detail="URL cannot be empty")
        
        # Check for potentially dangerous URLs
        dangerous_patterns = ['file:///', 'javascript:', 'data:', 'vbscript:']
        if any(pattern in url.lower() for pattern in dangerous_patterns):
            raise HTTPException(status_code=400, detail="URL scheme not allowed for security reasons")
        
        success = session_manager.open_url(session_id, url)
        
        return {
            "success": success,
            "message": f"URL opened successfully: {url}" if success else f"Failed to open URL: {url}",
            "url": url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error opening URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/url/schemes")
async def get_url_schemes(session_id: str):
    """Get information about supported URL schemes"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        schemes_info = session_manager.get_url_scheme_info(session_id)
        return schemes_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting URL schemes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Replace the existing screenshot save endpoint with this:

@router.post("/{session_id}/screenshot/download")
async def download_screenshot(session_id: str, filename: str = Form(None)):
    """Take a screenshot and return it for download"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get the session's UDID
        session = session_manager.get_session(session_id)
        udid = session.udid
        
        # Generate filename if not provided
        if not filename:
            timestamp = int(time.time())
            filename = f"screenshot_{session_id[:8]}_{timestamp}.png"
        elif not filename.endswith('.png'):
            filename += '.png'
        
        # Create temporary file for screenshot
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Take screenshot using simctl
            command = ['xcrun', 'simctl', 'io', udid, 'screenshot', temp_path]
            success, output = session_manager.ios_manager._run_command(command)
            
            if success and os.path.exists(temp_path):
                # Read the screenshot file
                with open(temp_path, 'rb') as f:
                    screenshot_data = f.read()
                
                # Return as downloadable PNG response
                from fastapi.responses import Response
                return Response(
                    content=screenshot_data,
                    media_type="image/png",
                    headers={
                        "Content-Disposition": f"attachment; filename={filename}",
                        "Content-Length": str(len(screenshot_data))
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to take screenshot: {output}"
                )
                
        finally:
            # Clean up temporary file immediately after reading
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
    

@router.get("/{session_id}/screenshot")
async def get_screenshot(session_id: str):
    """Take a screenshot and return it as response"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get the session's UDID
        session = session_manager.get_session(session_id)
        udid = session.udid
        
        # Create temporary file for screenshot
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Take screenshot using simctl
            command = ['xcrun', 'simctl', 'io', udid, 'screenshot', temp_path]
            success, output = session_manager.ios_manager._run_command(command)
            
            if success and os.path.exists(temp_path):
                # Read the screenshot file
                with open(temp_path, 'rb') as f:
                    screenshot_data = f.read()
                
                # Return as PNG response
                return Response(
                    content=screenshot_data,
                    media_type="image/png",
                    headers={
                        "Content-Disposition": f"attachment; filename=screenshot_{session_id[:8]}.png"
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to take screenshot: {output}"
                )
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/orientation")
async def change_orientation(session_id: str, orientation: str = Form(...)):
    """Change the simulator's orientation"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Validate orientation
        valid_orientations = ['portrait', 'landscape', 'portraitupsidedown', 'landscaperight', 'landscapeleft']
        if orientation.lower() not in valid_orientations:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid orientation. Must be one of: {', '.join(valid_orientations)}"
            )
        
        # Get the session's UDID
        session = session_manager.get_session(session_id)
        udid = session.udid
        
        # Map orientation names to simctl values
        orientation_map = {
            'portrait': 'portrait',
            'landscape': 'landscape',
            'portraitupsidedown': 'portraitupsidedown', 
            'landscaperight': 'landscaperight',
            'landscapeleft': 'landscapeleft'
        }
        
        simctl_orientation = orientation_map.get(orientation.lower(), orientation.lower())
        
        # Change orientation using simctl
        command = ['xcrun', 'simctl', 'device', udid, 'orientation', simctl_orientation]
        success, output = session_manager.ios_manager._run_command(command)
        
        if success:
            logger.info(f"Changed orientation to {orientation} for session {session_id}")
            return {
                "success": True,
                "message": f"Orientation changed to {orientation}",
                "orientation": orientation
            }
        else:
            logger.error(f"Failed to change orientation: {output}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to change orientation: {output}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing orientation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Add these endpoints to your existing session_routes.py

@router.get("/{session_id}/logs")
async def get_recent_logs(
    session_id: str, 
    lines: int = 100,
    level: str = "all",
    process: str = None
):
    """Get recent logs from the simulator"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_manager.get_session(session_id)
        
        # Build log command
        command = [
            'xcrun', 'simctl', 'spawn', session.udid,
            'log', 'show',
            '--last', f'{lines}',
            '--style', 'compact'
        ]
        
        # Add level filter
        if level and level != "all":
            level_map = {
                "error": "error",
                "warning": "info",
                "info": "info", 
                "debug": "debug"
            }
            if level in level_map:
                command.extend(['--level', level_map[level]])
        
        # Add process filter
        if process:
            command.extend(['--predicate', f'process == "{process}"'])
        
        # Execute command
        success, output = session_manager.ios_manager._run_command(command)
        
        if success:
            # Parse log lines
            log_lines = []
            for line in output.split('\n'):
                if line.strip():
                    parsed_line = _parse_log_line(line.strip())
                    log_lines.append(parsed_line)
            
            return {
                "success": True,
                "logs": log_lines[-lines:],  # Return last N lines
                "total_lines": len(log_lines)
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get logs: {output}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/logs/clear")
async def clear_logs(session_id: str):
    """Clear simulator logs"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_manager.get_session(session_id)
        
        # Clear logs using log erase command
        command = [
            'xcrun', 'simctl', 'spawn', session.udid,
            'log', 'erase'
        ]
        
        success, output = session_manager.ios_manager._run_command(command)
        
        return {
            "success": success,
            "message": "Logs cleared successfully" if success else f"Failed to clear logs: {output}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@router.get("/{session_id}/logs/processes")
async def get_log_processes(session_id: str):
    """Get list of processes that are generating logs"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_manager.get_session(session_id)
        
        # Get process list
        command = [
            'xcrun', 'simctl', 'spawn', session.udid,
            'ps', 'aux'
        ]
        
        success, output = session_manager.ios_manager._run_command(command)
        
        if success:
            processes = []
            lines = output.split('\n')[1:]  # Skip header
            
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 11:  # Standard ps output format
                        processes.append({
                            "pid": parts[1],
                            "process": parts[10],
                            "cpu": parts[2],
                            "memory": parts[3]
                        })
            
            return {
                "success": True,
                "processes": processes
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get processes: {output}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _parse_log_line(line: str) -> dict:
    """Helper function to parse log lines"""
    try:
        parts = line.split(' ', 3)
        
        if len(parts) >= 4:
            timestamp_str = f"{parts[0]} {parts[1]}"
            process_info = parts[2]
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
                "timestamp": timestamp_str,
                "process": process_name,
                "pid": pid_part,
                "level": level,
                "message": message
            }
        else:
            return {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "process": "unknown",
                "pid": "",
                "level": "info",
                "message": line
            }
            
    except Exception:
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "process": "unknown",
            "pid": "",
            "level": "info",
            "message": line
        }
    
# Add this endpoint after your existing endpoints

# Replace the set_mock_location endpoint with this corrected version:

@router.post("/{session_id}/location/set")
async def set_mock_location(
    session_id: str, 
    latitude: float = Form(...), 
    longitude: float = Form(...)
):
    """Set mock location for the simulator"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Validate coordinates
        if not (-90 <= latitude <= 90):
            raise HTTPException(
                status_code=400, 
                detail="Latitude must be between -90 and 90 degrees"
            )
        
        if not (-180 <= longitude <= 180):
            raise HTTPException(
                status_code=400, 
                detail="Longitude must be between -180 and 180 degrees"
            )
        
        session = session_manager.get_session(session_id)
        udid = session.udid
        
        # Set location using simctl - coordinates must be passed as a single comma-separated argument
        coordinate_pair = f"{latitude},{longitude}"
        command = [
            'xcrun', 'simctl', 'location', udid, 'set', coordinate_pair
        ]
        
        logger.info(f"Setting location with command: {' '.join(command)}")
        success, output = session_manager.ios_manager._run_command(command)
        
        if success:
            logger.info(f"Set mock location to {latitude}, {longitude} for session {session_id}")
            return {
                "success": True,
                "message": f"Location set to {latitude}, {longitude}",
                "latitude": latitude,
                "longitude": longitude,
                "coordinate_pair": coordinate_pair
            }
        else:
            logger.error(f"Failed to set location: {output}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to set location: {output}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting location: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/location/clear")
async def clear_mock_location(session_id: str):
    """Clear mock location for the simulator (revert to default)"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_manager.get_session(session_id)
        udid = session.udid
        
        # Clear location using simctl
        command = [
            'xcrun', 'simctl', 'location', udid, 'clear'
        ]
        
        success, output = session_manager.ios_manager._run_command(command)
        
        if success:
            logger.info(f"Cleared mock location for session {session_id}")
            return {
                "success": True,
                "message": "Mock location cleared"
            }
        else:
            logger.error(f"Failed to clear location: {output}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to clear location: {output}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing location: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/location/presets")
async def get_location_presets(session_id: str):
    """Get predefined location presets"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Predefined location presets
        presets = [
            {
                "name": "San Francisco, CA",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "description": "San Francisco Bay Area"
            },
            {
                "name": "New York, NY",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "description": "New York City"
            },
            {
                "name": "London, UK",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "description": "London, United Kingdom"
            },
            {
                "name": "Tokyo, Japan",
                "latitude": 35.6762,
                "longitude": 139.6503,
                "description": "Tokyo, Japan"
            },
            {
                "name": "Sydney, Australia",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "description": "Sydney, Australia"
            },
            {
                "name": "Paris, France",
                "latitude": 48.8566,
                "longitude": 2.3522,
                "description": "Paris, France"
            },
            {
                "name": "Berlin, Germany",
                "latitude": 52.5200,
                "longitude": 13.4050,
                "description": "Berlin, Germany"
            },
            {
                "name": "Mumbai, India",
                "latitude": 19.0760,
                "longitude": 72.8777,
                "description": "Mumbai, India"
            },
            {
                "name": "Beijing, China",
                "latitude": 39.9042,
                "longitude": 116.4074,
                "description": "Beijing, China"
            },
            {
                "name": "São Paulo, Brazil",
                "latitude": -23.5505,
                "longitude": -46.6333,
                "description": "São Paulo, Brazil"
            }
        ]
        
        return {
            "success": True,
            "presets": presets
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting location presets: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Add this new endpoint for setting predefined locations:

@router.post("/{session_id}/location/set-predefined")
async def set_predefined_location(
    session_id: str, 
    location_name: str = Form(...)
):
    """Set a predefined location for the simulator"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Predefined locations supported by simctl
        predefined_locations = [
            "Apple", "City Bicycle Ride", "City Run", "Freeway Drive", 
            "Hand", "None", "Custom Location"
        ]
        
        session = session_manager.get_session(session_id)
        udid = session.udid
        
        # Set predefined location using simctl
        command = [
            'xcrun', 'simctl', 'location', udid, 'set', location_name
        ]
        
        logger.info(f"Setting predefined location with command: {' '.join(command)}")
        success, output = session_manager.ios_manager._run_command(command)
        
        if success:
            logger.info(f"Set predefined location '{location_name}' for session {session_id}")
            return {
                "success": True,
                "message": f"Location set to '{location_name}'",
                "location_name": location_name
            }
        else:
            logger.error(f"Failed to set predefined location: {output}")
            # If predefined location fails, provide helpful message
            if location_name not in predefined_locations:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown predefined location '{location_name}'. Available: {', '.join(predefined_locations)}"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to set location: {output}"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting predefined location: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/location/predefined")
async def get_predefined_locations(session_id: str):
    """Get list of predefined locations supported by the simulator"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        predefined_locations = [
            {
                "name": "Apple",
                "description": "Apple Park, Cupertino"
            },
            {
                "name": "City Bicycle Ride", 
                "description": "Simulated bicycle ride through city"
            },
            {
                "name": "City Run",
                "description": "Simulated running route through city"
            },
            {
                "name": "Freeway Drive",
                "description": "Simulated freeway driving route"
            },
            {
                "name": "Hand",
                "description": "Manual location control"
            },
            {
                "name": "None",
                "description": "No location services"
            }
        ]
        
        return {
            "success": True,
            "predefined_locations": predefined_locations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting predefined locations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/media/photos/add")
async def add_photos(
    session_id: str,
    photos: List[UploadFile] = File(...)
):
    """Add photos to simulator's photo library"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not photos:
            raise HTTPException(status_code=400, detail="No photos provided")
        
        # Save uploaded photos temporarily
        temp_paths = []
        try:
            for photo in photos:
                if not photo.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.heic', '.heif')):
                    raise HTTPException(status_code=400, detail=f"Invalid photo format: {photo.filename}")
                
                # Create temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(photo.filename)[1]) as temp_file:
                    content = await photo.read()
                    temp_file.write(content)
                    temp_paths.append(temp_file.name)
            
            # Add photos using session manager
            success = session_manager.ios_manager.add_photos(session_id, *temp_paths)
            
            if success:
                return {
                    "success": True,
                    "message": f"Successfully added {len(photos)} photo(s)",
                    "count": len(photos),
                    "photos": [photo.filename for photo in photos]
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to add photos to simulator")
                
        finally:
            # Clean up temp files
            for temp_path in temp_paths:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding photos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/media/videos/add")
async def add_videos(
    session_id: str,
    videos: List[UploadFile] = File(...)
):
    """Add videos to simulator's photo library"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not videos:
            raise HTTPException(status_code=400, detail="No videos provided")
        
        # Save uploaded videos temporarily
        temp_paths = []
        try:
            for video in videos:
                if not video.filename.lower().endswith(('.mp4', '.mov', '.m4v', '.avi', '.mkv')):
                    raise HTTPException(status_code=400, detail=f"Invalid video format: {video.filename}")
                
                # Create temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video.filename)[1]) as temp_file:
                    content = await video.read()
                    temp_file.write(content)
                    temp_paths.append(temp_file.name)
            
            # Add videos using session manager
            success = session_manager.ios_manager.add_videos(session_id, *temp_paths)
            
            if success:
                return {
                    "success": True,
                    "message": f"Successfully added {len(videos)} video(s)",
                    "count": len(videos),
                    "videos": [video.filename for video in videos]
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to add videos to simulator")
                
        finally:
            # Clean up temp files
            for temp_path in temp_paths:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/files/push")
async def push_file(
    session_id: str,
    file: UploadFile = File(...),
    device_path: str = Form(...),
    bundle_id: Optional[str] = Form(None)
):
    """Push a file to the simulator"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Push file using session manager
            success = session_manager.ios_manager.push_file(session_id, temp_path, device_path, bundle_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Successfully pushed file: {file.filename}",
                    "filename": file.filename,
                    "device_path": device_path,
                    "bundle_id": bundle_id,
                    "size": len(content)
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to push file to simulator")
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pushing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/files/pull")
async def pull_file(
    session_id: str,
    device_path: str = Form(...),
    bundle_id: Optional[str] = Form(None),
    filename: Optional[str] = Form(None)
):
    """Pull a file from the simulator"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate filename if not provided
        if not filename:
            filename = os.path.basename(device_path) or "pulled_file"
        
        # Create temp file for pulling
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
            temp_path = temp_file.name
        
        try:
            # Pull file using session manager
            success = session_manager.ios_manager.pull_file(session_id, device_path, temp_path, bundle_id)
            
            if success and os.path.exists(temp_path):
                # Return file as download
                return FileResponse(
                    path=temp_path,
                    filename=filename,
                    media_type='application/octet-stream'
                )
            else:
                # Clean up temp file if pull failed
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise HTTPException(status_code=404, detail="File not found on simulator or pull failed")
                
        except HTTPException:
            raise
        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pulling file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/files/app-container")
async def get_app_container_path(session_id: str, bundle_id: str):
    """Get app container path"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        container_path = session_manager.ios_manager.get_app_container_path(session_id, bundle_id)
        
        if container_path:
            return {
                "success": True,
                "container_path": container_path,
                "bundle_id": bundle_id
            }
        else:
            raise HTTPException(status_code=404, detail="App container not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting app container: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/media/info")
async def get_media_info(session_id: str):
    """Get information about supported media formats"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "success": True,
            "supported_photo_formats": [".jpg", ".jpeg", ".png", ".gif", ".heic", ".heif"],
            "supported_video_formats": [".mp4", ".mov", ".m4v", ".avi", ".mkv"],
            "max_file_size": "100MB",
            "common_paths": {
                "app_documents": "/Documents/",
                "app_library": "/Library/",
                "app_tmp": "/tmp/",
                "simulator_tmp": "/tmp/",
                "simulator_documents": "/Documents/"
            }
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting media info: {e}")
        raise HTTPException(status_code=500, detail=str(e))