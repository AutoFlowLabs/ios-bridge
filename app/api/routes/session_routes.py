from fastapi import APIRouter, HTTPException, UploadFile, File, Form
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

# App Management Routes
@router.post("/{session_id}/apps/install")
async def install_app(session_id: str, ipa_file: UploadFile = File(...)):
    """Install an IPA file to a session"""
    try:
        # Validate session exists
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ipa') as tmp_file:
            content = await ipa_file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Install the app
            success = session_manager.install_ipa(session_id, tmp_file_path)
            
            if success:
                return {
                    "success": True,
                    "message": f"App installed successfully to session {session_id}"
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to install app")
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing app: {e}")
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

@router.delete("/{session_id}/apps/{bundle_id}")
async def uninstall_app(session_id: str, bundle_id: str):
    """Uninstall an app from a session"""
    try:
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        success = session_manager.uninstall_app(session_id, bundle_id)
        return {
            "success": success,
            "message": f"App {bundle_id} uninstalled" if success else "Failed to uninstall app"
        }
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