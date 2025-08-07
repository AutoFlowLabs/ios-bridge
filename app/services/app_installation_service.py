from dataclasses import dataclass
import os
import shutil
import subprocess
import tempfile
import time
from typing import Callable, Dict, List, Optional
import zipfile

from app.services.ios_app_analyzer_service import AppAnalyzer, AppCompatibility, AppInfo

class InstallationResult:
    def __init__(self):
        self.success = False
        self.message = ""
        self.compatibility = None
        self.app_info = None
        self.suggestions = []
        self.alternatives = []
        self.processing_steps = []

@dataclass
class InstalledApp:
    bundle_id: str
    app_name: str
    app_path: str
    installed_at: float
    app_type: str
    version: str = ""

class NativeBridgeInstaller:
    """Enhanced installer with comprehensive user guidance"""
    
    def __init__(self, active_sessions: Dict):
        self.analyzer = AppAnalyzer()
        self.active_sessions = active_sessions
    

    def install_user_app(self, session_id: str, file_path: str, 
                    progress_callback: Optional[Callable] = None) -> InstallationResult:
        """
        Main installation method with comprehensive handling and better fallback
        """
        result = InstallationResult()
        
        try:
            # Validate session
            if session_id not in self.active_sessions:
                result.message = f"❌ Simulator session not found: {session_id}"
                return result
            
            session = self.active_sessions[session_id]
            
            # Step 1: Analyze the uploaded app
            if progress_callback:
                progress_callback('analyzing', f"🔍 Analyzing uploaded app...")
            
            compatibility, app_info = self.analyzer.analyze_uploaded_app(file_path)
            result.compatibility = compatibility
            result.app_info = app_info
            
            # Print detailed analysis for debugging
            print(f"[DEBUG] Compatibility: {compatibility}")
            print(f"[DEBUG] App Info: {app_info}")
            print(f"[DEBUG] Architecture Info: {app_info.architecture_info}")
            
            # If analysis result is UNKNOWN but we have basic app info, try platform-based guess
            if compatibility == AppCompatibility.UNKNOWN and app_info.bundle_id:
                print(f"[DEBUG] Analysis returned UNKNOWN, attempting platform-based guess...")
                
                # Check platforms to make educated guess
                if 'iPhoneOS' in app_info.supported_platforms and 'iPhoneSimulator' not in app_info.supported_platforms:
                    print(f"[DEBUG] Overriding to DEVICE_ONLY based on platform")
                    compatibility = AppCompatibility.DEVICE_ONLY
                    result.compatibility = compatibility
                elif 'iPhoneSimulator' in app_info.supported_platforms:
                    print(f"[DEBUG] Overriding to SIMULATOR_COMPATIBLE based on platform")
                    compatibility = AppCompatibility.SIMULATOR_COMPATIBLE
                    result.compatibility = compatibility
                else:
                    # Try direct installation as a last resort for unknown compatibility
                    print(f"[DEBUG] Attempting direct installation for unknown compatibility...")
                    return self._attempt_direct_installation(session_id, file_path, app_info, progress_callback)
            
            summary = self.analyzer.get_compatibility_summary(compatibility, app_info)
            
            if progress_callback:
                progress_callback('analysis_complete', summary['message'])
            
            # Step 2: Handle based on compatibility
            if compatibility == AppCompatibility.SIMULATOR_COMPATIBLE:
                return self._install_compatible_app(session_id, file_path, app_info, progress_callback)
                
            elif compatibility == AppCompatibility.UNIVERSAL:
                return self._install_universal_app(session_id, file_path, app_info, progress_callback)
                
            elif compatibility == AppCompatibility.DEVICE_ONLY:
                # Keep the app_info and compatibility in the result
                device_result = self._handle_device_only_app(app_info)
                device_result.compatibility = compatibility  # Ensure compatibility is preserved
                device_result.app_info = app_info  # Ensure app_info is preserved
                return device_result
                
            else:
                # Keep the app_info and compatibility for other cases too
                incompatible_result = self._handle_incompatible_app(compatibility, app_info)
                incompatible_result.compatibility = compatibility
                incompatible_result.app_info = app_info
                return incompatible_result
                
        except Exception as e:
            result.message = f"❌ Installation error: {str(e)}"
            result.suggestions = ["Please try uploading the app again", "Ensure the app file is not corrupted"]
            result.compatibility = AppCompatibility.UNKNOWN
            result.app_info = app_info if 'app_info' in locals() else None
            return result

    def _attempt_direct_installation(self, session_id: str, file_path: str, 
                                app_info: AppInfo, progress_callback: Optional[Callable] = None) -> InstallationResult:
        """
        Attempt direct installation when compatibility analysis fails
        This is a fallback method for when we can't determine compatibility
        """
        result = InstallationResult()
        
        try:
            if progress_callback:
                progress_callback('attempting_direct', "🔄 Attempting direct installation...")
            
            print(f"[DEBUG] Attempting direct installation of {app_info.app_name}")
            
            # Try installing directly and see what happens
            session = self.active_sessions[session_id]
            
            if file_path.endswith('.ipa'):
                success = self._install_from_ipa(session_id, file_path, app_info, progress_callback)
            else:
                success = self._install_app_bundle(session_id, file_path, app_info)
            
            if success:
                result.success = True
                result.message = f"✅ Successfully installed {app_info.display_name or app_info.app_name} (compatibility was uncertain)"
                
                # Add to session's installed apps
                installed_app = InstalledApp(
                    bundle_id=app_info.bundle_id,
                    app_name=app_info.display_name or app_info.app_name,
                    app_path=file_path,
                    installed_at=time.time(),
                    app_type="unknown_compatibility",
                    version=app_info.version
                )
                session.installed_apps[app_info.bundle_id] = installed_app
                
                if progress_callback:
                    progress_callback('success', result.message)
            else:
                result.message = "❌ Direct installation failed - app may not be simulator compatible"
                result.suggestions = [
                    "This app appears to be device-only (ARM64)",
                    "Request a simulator build from your development team",
                    "If you have the source code, build it targeting 'iOS Simulator'"
                ]
            
            return result
            
        except Exception as e:
            result.message = f"❌ Direct installation error: {str(e)}"
            return result
        

    def _install_compatible_app(self, session_id: str, file_path: str, 
                              app_info: AppInfo, progress_callback: Optional[Callable] = None) -> InstallationResult:
        """Install simulator-compatible app"""
        result = InstallationResult()
        
        try:
            if progress_callback:
                progress_callback('installing', "📱 Installing app to simulator...")
            
            session = self.active_sessions[session_id]
            
            # Handle different file types
            if file_path.endswith('.ipa'):
                success = self._install_from_ipa(session_id, file_path, app_info, progress_callback)
            else:
                success = self._install_app_bundle(session_id, file_path, app_info)
            
            if success:
                result.success = True
                result.message = f"✅ Successfully installed {app_info.display_name or app_info.app_name}"
                
                # Add to session's installed apps
                installed_app = InstalledApp(
                    bundle_id=app_info.bundle_id,
                    app_name=app_info.display_name or app_info.app_name,
                    app_path=file_path,
                    installed_at=time.time(),
                    app_type="simulator",
                    version=app_info.version
                )
                session.installed_apps[app_info.bundle_id] = installed_app
                
                if progress_callback:
                    progress_callback('success', result.message)
                    
            else:
                result.message = "❌ Installation failed despite compatibility"
                result.suggestions = [
                    "The app might have simulator-specific dependencies that aren't met",
                    "Try restarting the simulator session",
                    "Contact support if the issue persists"
                ]
                
        except Exception as e:
            result.message = f"❌ Installation error: {str(e)}"
            
        return result
    
    def _install_universal_app(self, session_id: str, file_path: str, 
                             app_info: AppInfo, progress_callback: Optional[Callable] = None) -> InstallationResult:
        """Install universal app by extracting simulator slice"""
        result = InstallationResult()
        
        try:
            if progress_callback:
                progress_callback('processing', "🔄 Processing universal app for simulator...")
            
            # Extract and thin the app for simulator
            processed_path = self._process_universal_app(file_path, app_info, progress_callback)
            
            if processed_path:
                # Install the processed app
                return self._install_compatible_app(session_id, processed_path, app_info, progress_callback)
            else:
                result.message = "❌ Failed to extract simulator-compatible version"
                result.suggestions = self._get_universal_app_suggestions()
                
        except Exception as e:
            result.message = f"❌ Processing error: {str(e)}"
            result.suggestions = self._get_universal_app_suggestions()
            
        return result
    
    def _process_universal_app(self, file_path: str, app_info: AppInfo, 
                              progress_callback: Optional[Callable] = None) -> Optional[str]:
        """Process universal app to extract simulator slice"""
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                if progress_callback:
                    progress_callback('extracting', "📦 Extracting app bundle...")
                
                # Extract the app
                if file_path.endswith('.ipa'):
                    app_bundle_path = self._extract_app_from_ipa(file_path, temp_dir)
                else:
                    app_bundle_path = file_path
                
                if not app_bundle_path:
                    return None
                
                if progress_callback:
                    progress_callback('thinning', "✂️ Extracting simulator architecture...")
                
                # Thin the binary for simulator
                success = self._thin_binary_for_simulator(app_bundle_path, app_info)
                
                if success:
                    # Copy processed app to a permanent location
                    processed_path = os.path.join(
                        tempfile.gettempdir(), 
                        f"processed_{int(time.time())}_{os.path.basename(app_bundle_path)}"
                    )
                    shutil.copytree(app_bundle_path, processed_path)
                    
                    if progress_callback:
                        progress_callback('processing_complete', "✅ Successfully processed universal app")
                    
                    return processed_path
                
        except Exception as e:
            if progress_callback:
                progress_callback('error', f"Processing failed: {str(e)}")
        
        return None
    
    def _extract_app_from_ipa(self, ipa_path: str, temp_dir: str) -> Optional[str]:
        """Extract .app bundle from IPA"""
        try:
            with zipfile.ZipFile(ipa_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            payload_dir = os.path.join(temp_dir, 'Payload')
            if not os.path.exists(payload_dir):
                return None
            
            app_dirs = [d for d in os.listdir(payload_dir) if d.endswith('.app')]
            if not app_dirs:
                return None
            
            return os.path.join(payload_dir, app_dirs[0])
            
        except Exception:
            return None
    
    def _thin_binary_for_simulator(self, app_bundle_path: str, app_info: AppInfo) -> bool:
        """Thin binary to extract simulator architecture"""
        
        if not app_info.executable_name:
            return False
        
        executable_path = os.path.join(app_bundle_path, app_info.executable_name)
        if not os.path.exists(executable_path):
            return False
        
        try:
            # Check available architectures
            result = subprocess.run(['lipo', '-info', executable_path], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                return False
            
            # Determine which simulator architecture to extract
            target_arch = None
            if 'x86_64' in result.stdout:
                target_arch = 'x86_64'
            elif 'i386' in result.stdout:
                target_arch = 'i386'
            
            if not target_arch:
                return False
            
            # Create thinned version
            temp_executable = executable_path + '_temp'
            lipo_cmd = ['lipo', '-thin', target_arch, executable_path, '-output', temp_executable]
            
            result = subprocess.run(lipo_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Replace original with thinned version
                shutil.move(temp_executable, executable_path)
                return True
            
        except Exception as e:
            print(f"Error thinning binary: {e}")
        
        return False
    
    def _install_from_ipa(self, session_id: str, ipa_path: str, 
                         app_info: AppInfo, progress_callback: Optional[Callable] = None) -> bool:
        """Install app from IPA file"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            app_bundle_path = self._extract_app_from_ipa(ipa_path, temp_dir)
            
            if not app_bundle_path:
                return False
            
            return self._install_app_bundle(session_id, app_bundle_path, app_info)
    
    def _install_app_bundle(self, session_id: str, app_bundle_path: str, app_info: AppInfo) -> bool:
        """Install .app bundle using simctl"""
        
        session = self.active_sessions[session_id]
        
        try:
            command = ['xcrun', 'simctl', 'install', session.udid, app_bundle_path]
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
    
    def _handle_device_only_app(self, app_info: AppInfo) -> InstallationResult:
        """Handle device-only apps with comprehensive guidance"""
        result = InstallationResult()
        result.success = False
        result.compatibility = AppCompatibility.DEVICE_ONLY
        result.app_info = app_info
        
        result.message = "🚫 This app is built for physical iOS devices only and cannot run on simulators"
        
        result.suggestions = [
            "📱 The app contains only device-specific architectures (ARM64/ARMv7)",
            "🏗️ Request a simulator build from your development team", 
            "💡 If you have the source code, build it targeting 'iOS Simulator'",
            "📋 Ensure your Xcode project includes simulator architectures"
        ]
        
        app_name = app_info.display_name or app_info.app_name or "Unknown App"
        
        result.alternatives = [
            {
                'title': '👥 Request Simulator Build',
                'description': 'Ask your development team to provide a simulator-compatible version',
                'steps': [
                    'Contact your app development team',
                    f'Request a simulator build for: {app_name}',
                    f'Bundle ID: {app_info.bundle_id}',
                    'Specify need for x86_64 architecture (iOS Simulator)',
                    'Upload the simulator build to NativeBridge'
                ],
                'difficulty': 'Easy',
                'success_rate': 'High'
            },
            {
                'title': '✈️ TestFlight Testing',
                'description': 'Use TestFlight for device testing instead',
                'steps': [
                    'Upload your app to App Store Connect',
                    'Add testers to TestFlight',
                    'Distribute via TestFlight for real device testing'
                ],
                'difficulty': 'Medium',
                'success_rate': 'High'
            }
        ]
        
        return result
    
    def _handle_incompatible_app(self, compatibility: AppCompatibility, app_info: AppInfo) -> InstallationResult:
        """Handle incompatible applications"""
        result = InstallationResult()
        
        if compatibility == AppCompatibility.CORRUPTED:
            result.message = "❌ App file appears to be corrupted or damaged"
            result.suggestions = [
                "📥 Re-download or re-export the app file",
                "🔍 Verify the file wasn't corrupted during transfer",
                "💾 Try exporting the app again from Xcode or App Store Connect"
            ]
            
        elif compatibility == AppCompatibility.INVALID_FORMAT:
            result.message = "❌ Invalid app format or file structure"
            result.suggestions = [
                "📝 Ensure you're uploading a valid .ipa or .app file",
                "🏗️ Verify the app was properly built and exported",
                "📋 Check that the app bundle structure is correct"
            ]
            
        elif compatibility == AppCompatibility.MISSING_COMPONENTS:
            result.message = "❌ App is missing required components"
            result.suggestions = [
                "📄 Info.plist file is missing or corrupted",
                "🔧 Executable file not found",
                "🏗️ Re-build the app with proper configuration"
            ]
            
        else:
            result.message = "❓ Could not determine app compatibility"
            result.suggestions = [
                "🔍 Please verify this is a valid iOS application",
                "📞 Contact support with details about your app"
            ]
        
        if app_info.error_details:
            result.suggestions.append(f"📋 Technical details: {app_info.error_details}")
        
        return result
    
    def _get_universal_app_suggestions(self) -> List[str]:
        """Get suggestions for universal app processing failures"""
        return [
            "🔄 The app contains both device and simulator code but processing failed",
            "🛠️ Request a simulator-specific build from your development team",
            "📋 Ensure the simulator architecture (x86_64) is properly included",
            "🏗️ If rebuilding, target 'iOS Simulator' specifically in Xcode"
        ]
    
    def _get_device_only_alternatives(self, app_info: AppInfo) -> List[Dict]:
        """Get alternative solutions for device-only apps"""
        
        alternatives = []
        
        # Development team solution
        alternatives.append({
            'title': '👥 Request Simulator Build',
            'description': 'Ask your development team to provide a simulator-compatible version',
            'steps': [
                'Contact your app development team',
                f'Request a simulator build for: {app_info.display_name or app_info.app_name}',
                f'Bundle ID: {app_info.bundle_id}',
                'Specify need for x86_64 architecture (iOS Simulator)',
                'Upload the simulator build to NativeBridge'
            ],
            'difficulty': 'Easy',
            'success_rate': 'High'
        })
        
        # Source code solution
        if app_info.bundle_id and 'com.yourcompany' in app_info.bundle_id:  # Heuristic for own app
            alternatives.append({
                'title': '🏗️ Build for Simulator',
                'description': 'Build your app specifically for iOS Simulator',
                'steps': [
                    'Open your project in Xcode',
                    'Select "iOS Simulator" as the destination',
                    'Choose Product → Build',
                    'Locate the .app file in build products',
                    'Upload the .app bundle to NativeBridge'
                ],
                'difficulty': 'Medium',
                'success_rate': 'High'
            })
        
        # TestFlight alternative
        alternatives.append({
            'title': '✈️ TestFlight Testing',
            'description': 'Use TestFlight for device testing instead',
            'steps': [
                'Upload your app to App Store Connect',
                'Add testers to TestFlight',
                'Distribute via TestFlight for real device testing'
            ],
            'difficulty': 'Medium',
            'success_rate': 'High'
        })
        
        return alternatives

    def get_detailed_report(self, session_id: str, file_path: str) -> Dict:
        """Generate a detailed compatibility and installation report"""
        
        compatibility, app_info = self.analyzer.analyze_uploaded_app(file_path)
        summary = self.analyzer.get_compatibility_summary(compatibility, app_info)
        
        report = {
            'timestamp': time.time(),
            'file_info': {
                'path': os.path.basename(file_path),
                'size_mb': round(os.path.getsize(file_path) / (1024 * 1024), 2),
                'type': os.path.splitext(file_path)[1]
            },
            'compatibility_analysis': summary,
            'installation_possible': summary['can_install'],
            'processing_required': summary.get('requires_processing', False),
            'next_steps': []
        }
        
        # Add specific next steps based on compatibility
        if compatibility == AppCompatibility.SIMULATOR_COMPATIBLE:
            report['next_steps'] = [
                "✅ App is ready for installation",
                "Click 'Install' to proceed",
                "App will be available immediately after installation"
            ]
            
        elif compatibility == AppCompatibility.UNIVERSAL:
            report['next_steps'] = [
                "🔄 App will be processed for simulator compatibility",
                "Processing may take a few moments",
                "App will be available after successful processing"
            ]
            
        elif compatibility == AppCompatibility.DEVICE_ONLY:
            result = self._handle_device_only_app(app_info)
            report['next_steps'] = result.suggestions
            report['alternatives'] = result.alternatives
            
        else:
            result = self._handle_incompatible_app(compatibility, app_info)
            report['next_steps'] = result.suggestions
        
        return report