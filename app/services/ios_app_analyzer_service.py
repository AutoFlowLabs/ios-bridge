import subprocess
import plistlib
import os
import tempfile
import zipfile
import time
import json
from enum import Enum
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass

class AppCompatibility(Enum):
    SIMULATOR_COMPATIBLE = "simulator_compatible"
    DEVICE_ONLY = "device_only"
    UNIVERSAL = "universal"
    CORRUPTED = "corrupted"
    INVALID_FORMAT = "invalid_format"
    MISSING_COMPONENTS = "missing_components"
    UNSUPPORTED_ARCHITECTURE = "unsupported_architecture"
    UNKNOWN = "unknown"

@dataclass
class ArchitectureInfo:
    has_x86_64: bool = False
    has_arm64: bool = False
    has_i386: bool = False
    has_armv7: bool = False
    architectures: List[str] = None
    
    def __post_init__(self):
        if self.architectures is None:
            self.architectures = []

@dataclass
class AppInfo:
    bundle_id: str = ""
    app_name: str = ""
    display_name: str = ""
    version: str = ""
    build_version: str = ""
    min_os_version: str = ""
    supported_platforms: List[str] = None
    architecture_info: ArchitectureInfo = None
    executable_name: str = ""
    file_size: int = 0
    has_info_plist: bool = False
    error_details: str = ""
    
    def __post_init__(self):
        if self.supported_platforms is None:
            self.supported_platforms = []
        if self.architecture_info is None:
            self.architecture_info = ArchitectureInfo()

class AppAnalyzer:
    """Comprehensive iOS app analyzer for NativeBridge compatibility"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._log("AppAnalyzer initialized")
    
    def _log(self, message: str):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[AppAnalyzer] {message}")
    
    def analyze_uploaded_app(self, file_path: str) -> Tuple[AppCompatibility, AppInfo]:
        """
        Main analysis method - analyzes any uploaded iOS app file
        
        Args:
            file_path: Path to the uploaded file (.ipa or .app)
            
        Returns:
            Tuple of (AppCompatibility, AppInfo)
        """
        app_info = AppInfo()
        
        try:
            # Basic file validation
            if not os.path.exists(file_path):
                app_info.error_details = f"File not found: {file_path}"
                return AppCompatibility.INVALID_FORMAT, app_info
            
            app_info.file_size = os.path.getsize(file_path)
            self._log(f"Analyzing file: {os.path.basename(file_path)} ({app_info.file_size} bytes)")
            
            # Determine file type and analyze
            if file_path.lower().endswith('.ipa'):
                return self._analyze_ipa(file_path, app_info)
            elif file_path.lower().endswith('.app') or os.path.isdir(file_path):
                return self._analyze_app_bundle(file_path, app_info)
            else:
                app_info.error_details = f"Unsupported file format: {os.path.splitext(file_path)[1]}"
                return AppCompatibility.INVALID_FORMAT, app_info
                
        except Exception as e:
            self._log(f"Analysis error: {str(e)}")
            app_info.error_details = str(e)
            return AppCompatibility.UNKNOWN, app_info
    
    def _analyze_ipa(self, ipa_path: str, app_info: AppInfo) -> Tuple[AppCompatibility, AppInfo]:
        """Analyze IPA file"""
        self._log("Analyzing IPA file...")
        
        try:
            # Validate ZIP structure
            if not zipfile.is_zipfile(ipa_path):
                app_info.error_details = "File is not a valid ZIP/IPA archive"
                return AppCompatibility.CORRUPTED, app_info
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract IPA
                try:
                    with zipfile.ZipFile(ipa_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                except zipfile.BadZipFile:
                    app_info.error_details = "Corrupted IPA file - cannot extract"
                    return AppCompatibility.CORRUPTED, app_info
                
                # Look for Payload directory
                payload_dir = os.path.join(temp_dir, 'Payload')
                if not os.path.exists(payload_dir):
                    app_info.error_details = "Invalid IPA structure - no Payload directory"
                    return AppCompatibility.INVALID_FORMAT, app_info
                
                # Find .app bundle
                app_bundles = []
                for item in os.listdir(payload_dir):
                    if item.endswith('.app') and os.path.isdir(os.path.join(payload_dir, item)):
                        app_bundles.append(item)
                
                if not app_bundles:
                    app_info.error_details = "No .app bundle found in IPA"
                    return AppCompatibility.INVALID_FORMAT, app_info
                
                if len(app_bundles) > 1:
                    self._log(f"Warning: Multiple app bundles found, analyzing first: {app_bundles[0]}")
                
                app_bundle_path = os.path.join(payload_dir, app_bundles[0])
                return self._analyze_app_bundle(app_bundle_path, app_info)
                
        except Exception as e:
            app_info.error_details = f"IPA analysis error: {str(e)}"
            return AppCompatibility.UNKNOWN, app_info
    
    def _analyze_app_bundle(self, app_path: str, app_info: AppInfo) -> Tuple[AppCompatibility, AppInfo]:
        """Analyze .app bundle"""
        self._log(f"Analyzing app bundle: {os.path.basename(app_path)}")
        
        try:
            # Check if it's a valid app bundle
            if not os.path.isdir(app_path):
                app_info.error_details = "Not a valid app bundle directory"
                return AppCompatibility.INVALID_FORMAT, app_info
            
            # Analyze Info.plist
            self._log("Starting Info.plist analysis...")
            compatibility = self._analyze_info_plist(app_path, app_info)
            self._log(f"Info.plist analysis result: {compatibility}")
            
            if compatibility != AppCompatibility.UNKNOWN:
                self._log("Info.plist analysis failed, returning early")
                return compatibility, app_info
            
            # Analyze executable if plist analysis was successful
            self._log("Starting executable analysis...")
            self._analyze_executable(app_path, app_info)
            self._log(f"Executable analysis completed. Architecture info: {app_info.architecture_info}")
            
            # Determine final compatibility
            final_compatibility = self._determine_final_compatibility(app_info)
            self._log(f"Final compatibility determination: {final_compatibility}")
            
            return final_compatibility, app_info
            
        except Exception as e:
            self._log(f"App bundle analysis error: {str(e)}")
            app_info.error_details = f"App bundle analysis error: {str(e)}"
            return AppCompatibility.UNKNOWN, app_info
        

    def _analyze_info_plist(self, app_path: str, app_info: AppInfo) -> AppCompatibility:
        """Analyze Info.plist file"""
        info_plist_path = os.path.join(app_path, 'Info.plist')
        
        if not os.path.exists(info_plist_path):
            app_info.error_details = "Info.plist not found in app bundle"
            app_info.has_info_plist = False
            return AppCompatibility.MISSING_COMPONENTS
        
        try:
            app_info.has_info_plist = True
            
            with open(info_plist_path, 'rb') as f:
                plist_data = plistlib.load(f)
            
            # Extract basic app information
            app_info.bundle_id = plist_data.get('CFBundleIdentifier', '')
            app_info.app_name = plist_data.get('CFBundleName', '')
            app_info.display_name = plist_data.get('CFBundleDisplayName', app_info.app_name)
            app_info.version = plist_data.get('CFBundleShortVersionString', '')
            app_info.build_version = plist_data.get('CFBundleVersion', '')
            app_info.min_os_version = plist_data.get('MinimumOSVersion', '')
            app_info.executable_name = plist_data.get('CFBundleExecutable', '')
            
            # Get supported platforms
            platforms = plist_data.get('CFBundleSupportedPlatforms', [])
            app_info.supported_platforms = platforms if isinstance(platforms, list) else [platforms]
            
            self._log(f"App: {app_info.display_name or app_info.app_name} ({app_info.bundle_id})")
            self._log(f"Version: {app_info.version} ({app_info.build_version})")
            self._log(f"Min OS: {app_info.min_os_version}")
            self._log(f"Platforms: {app_info.supported_platforms}")
            
            # Basic validation
            if not app_info.bundle_id:
                app_info.error_details = "Missing bundle identifier"
                return AppCompatibility.INVALID_FORMAT
            
            if not app_info.executable_name:
                app_info.error_details = "Missing executable name in Info.plist"
                return AppCompatibility.MISSING_COMPONENTS
            
            return AppCompatibility.UNKNOWN  # Continue with executable analysis
            
        except Exception as e:
            app_info.error_details = f"Error reading Info.plist: {str(e)}"
            return AppCompatibility.CORRUPTED
    
    
    def _analyze_executable(self, app_path: str, app_info: AppInfo):
        """Analyze the main executable for architecture information with enhanced debugging"""
        self._log("=== STARTING EXECUTABLE ANALYSIS ===")
        
        if not app_info.executable_name:
            self._log("No executable name found in Info.plist")
            self._set_educated_guess_architecture(app_info)
            return
        
        executable_path = os.path.join(app_path, app_info.executable_name)
        self._log(f"Looking for executable: {executable_path}")
        
        if not os.path.exists(executable_path):
            self._log(f"❌ Executable not found: {app_info.executable_name}")
            app_info.error_details = f"Executable not found: {app_info.executable_name}"
            self._set_educated_guess_architecture(app_info)
            return
        
        # Check if file is executable
        import stat
        file_stat = os.stat(executable_path)
        self._log(f"File permissions: {oct(file_stat.st_mode)}")
        self._log(f"File size: {file_stat.st_size} bytes")
        
        # Initialize architecture info if not already done
        if not app_info.architecture_info:
            app_info.architecture_info = ArchitectureInfo()
        
        try:
            # Try lipo first (most reliable for iOS binaries)
            self._log("Attempting architecture analysis with 'lipo'...")
            result = subprocess.run(
                ['lipo', '-info', executable_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            self._log(f"lipo return code: {result.returncode}")
            self._log(f"lipo stdout: '{result.stdout}'")
            self._log(f"lipo stderr: '{result.stderr}'")
            
            if result.returncode == 0 and result.stdout.strip():
                arch_info = self._parse_lipo_output(result.stdout)
                if arch_info.architectures:  # Only use if we found architectures
                    app_info.architecture_info = arch_info
                    self._log(f"✅ Architectures detected via lipo: {arch_info.architectures}")
                    return
                else:
                    self._log("lipo succeeded but no architectures found in output")
            
            # Try file command as fallback
            self._log("lipo failed or found no architectures, trying 'file' command...")
            result = subprocess.run(
                ['file', executable_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            self._log(f"file return code: {result.returncode}")
            self._log(f"file stdout: '{result.stdout}'")
            self._log(f"file stderr: '{result.stderr}'")
            
            if result.returncode == 0 and result.stdout.strip():
                arch_info = self._parse_file_output(result.stdout)
                if arch_info.architectures:  # Only use if we found architectures
                    app_info.architecture_info = arch_info
                    self._log(f"✅ Architectures detected via file: {arch_info.architectures}")
                    return
                else:
                    self._log("file succeeded but no architectures found in output")
            
            # Try otool as another fallback
            self._log("file failed or found no architectures, trying 'otool'...")
            result = subprocess.run(
                ['otool', '-h', executable_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            self._log(f"otool return code: {result.returncode}")
            self._log(f"otool stdout length: {len(result.stdout) if result.stdout else 0}")
            
            if result.returncode == 0 and result.stdout.strip():
                arch_info = self._parse_otool_output(result.stdout)
                if arch_info.architectures:  # Only use if we found architectures
                    app_info.architecture_info = arch_info
                    self._log(f"✅ Architectures detected via otool: {arch_info.architectures}")
                    return
                else:
                    self._log("otool succeeded but no architectures found in output")
            
            # If all tools fail, make educated guess based on platform
            self._log("⚠️ All architecture detection tools failed, making educated guess...")
            self._set_educated_guess_architecture(app_info)
            
        except subprocess.TimeoutExpired:
            self._log("❌ Timeout while analyzing executable")
            app_info.error_details = "Timeout during architecture analysis"
            self._set_educated_guess_architecture(app_info)
        except FileNotFoundError as e:
            self._log(f"❌ Required tool not found: {e}")
            app_info.error_details = f"Architecture analysis tool not available: {e}"
            self._set_educated_guess_architecture(app_info)
        except Exception as e:
            self._log(f"❌ Error analyzing executable: {str(e)}")
            app_info.error_details = f"Architecture analysis error: {str(e)}"
            self._set_educated_guess_architecture(app_info)
        
        self._log(f"=== EXECUTABLE ANALYSIS COMPLETE. Final arch info: {app_info.architecture_info} ===")

    def _set_educated_guess_architecture(self, app_info: AppInfo):
        """Set educated guess for architecture when tools fail"""
        self._log("=== SETTING EDUCATED GUESS ARCHITECTURE ===")
        
        if not app_info.architecture_info:
            app_info.architecture_info = ArchitectureInfo()
        
        if 'iPhoneOS' in app_info.supported_platforms:
            app_info.architecture_info.has_arm64 = True
            app_info.architecture_info.architectures = ['arm64']
            self._log("📱 Set educated guess: ARM64 based on iPhoneOS platform")
        elif 'iPhoneSimulator' in app_info.supported_platforms:
            app_info.architecture_info.has_x86_64 = True
            app_info.architecture_info.architectures = ['x86_64']
            self._log("🖥️ Set educated guess: x86_64 based on iPhoneSimulator platform")
        else:
            self._log("⚠️ No platform information available for educated guess")
        
        self._log(f"Educated guess result: {app_info.architecture_info}")


    def _parse_otool_output(self, otool_output: str) -> ArchitectureInfo:
        """Parse otool -h output to extract architecture information"""
        arch_info = ArchitectureInfo()
        
        lines = otool_output.strip().split('\n')
        for line in lines:
            line = line.strip().lower()
            
            # Look for architecture indicators in otool output
            if 'arm64' in line:
                arch_info.has_arm64 = True
                if 'arm64' not in arch_info.architectures:
                    arch_info.architectures.append('arm64')
            elif 'x86_64' in line:
                arch_info.has_x86_64 = True
                if 'x86_64' not in arch_info.architectures:
                    arch_info.architectures.append('x86_64')
            elif 'i386' in line:
                arch_info.has_i386 = True
                if 'i386' not in arch_info.architectures:
                    arch_info.architectures.append('i386')
            elif 'armv7' in line:
                arch_info.has_armv7 = True
                if 'armv7' not in arch_info.architectures:
                    arch_info.architectures.append('armv7')
        
        return arch_info
    
    
    def _parse_lipo_output(self, lipo_output: str) -> ArchitectureInfo:
        """Parse lipo command output to extract architecture information"""
        arch_info = ArchitectureInfo()
        
        # Clean up the output
        output = lipo_output.strip().lower()
        self._log(f"Parsing lipo output: '{output}'")
        
        # Common lipo output patterns:
        # "Architectures in the fat file: /path are: armv7 arm64"
        # "Non-fat file: /path is architecture: arm64"
        # "/path is architecture: x86_64"
        
        # Look for architecture keywords (case insensitive)
        if 'x86_64' in output or 'x86-64' in output:
            arch_info.has_x86_64 = True
            if 'x86_64' not in arch_info.architectures:
                arch_info.architectures.append('x86_64')
            self._log("Found x86_64 architecture")
        
        if 'arm64' in output:
            arch_info.has_arm64 = True
            if 'arm64' not in arch_info.architectures:
                arch_info.architectures.append('arm64')
            self._log("Found arm64 architecture")
        
        if 'i386' in output:
            arch_info.has_i386 = True
            if 'i386' not in arch_info.architectures:
                arch_info.architectures.append('i386')
            self._log("Found i386 architecture")
        
        if 'armv7' in output:
            arch_info.has_armv7 = True
            if 'armv7' not in arch_info.architectures:
                arch_info.architectures.append('armv7')
            self._log("Found armv7 architecture")
        
        # If no specific architectures found but output contains "architecture:", try to extract it
        if not arch_info.architectures and 'architecture:' in output:
            import re
            match = re.search(r'architecture:\s*(\w+)', output)
            if match:
                found_arch = match.group(1).lower()
                self._log(f"Extracted architecture from text: {found_arch}")
                
                if found_arch == 'arm64':
                    arch_info.has_arm64 = True
                    arch_info.architectures.append('arm64')
                elif found_arch == 'x86_64':
                    arch_info.has_x86_64 = True
                    arch_info.architectures.append('x86_64')
                elif found_arch == 'armv7':
                    arch_info.has_armv7 = True
                    arch_info.architectures.append('armv7')
                elif found_arch == 'i386':
                    arch_info.has_i386 = True
                    arch_info.architectures.append('i386')
        
        # Try to extract from "are: arch1 arch2" pattern
        if not arch_info.architectures and 'are:' in output:
            import re
            match = re.search(r'are:\s*(.+)', output)
            if match:
                arch_list_str = match.group(1).strip()
                self._log(f"Found architecture list: '{arch_list_str}'")
                
                # Split by whitespace and process each architecture
                for arch in arch_list_str.split():
                    arch = arch.strip().lower()
                    if arch == 'arm64':
                        arch_info.has_arm64 = True
                        arch_info.architectures.append('arm64')
                    elif arch == 'x86_64':
                        arch_info.has_x86_64 = True
                        arch_info.architectures.append('x86_64')
                    elif arch == 'armv7':
                        arch_info.has_armv7 = True
                        arch_info.architectures.append('armv7')
                    elif arch == 'i386':
                        arch_info.has_i386 = True
                        arch_info.architectures.append('i386')
        
        self._log(f"Parsed architectures: {arch_info.architectures}")
        return arch_info


    def _parse_file_output(self, file_output: str) -> ArchitectureInfo:
        """Parse file command output as fallback for architecture detection"""
        arch_info = ArchitectureInfo()
        
        output = file_output.strip().lower()
        
        if 'x86_64' in output or 'x86-64' in output:
            arch_info.has_x86_64 = True
            arch_info.architectures.append('x86_64')
        
        if 'arm64' in output:
            arch_info.has_arm64 = True
            arch_info.architectures.append('arm64')
        
        if 'i386' in output:
            arch_info.has_i386 = True
            arch_info.architectures.append('i386')
        
        if 'arm' in output and 'arm64' not in output:
            arch_info.has_armv7 = True
            arch_info.architectures.append('armv7')
        
        return arch_info

    def _determine_final_compatibility(self, app_info: AppInfo) -> AppCompatibility:
        """Determine final compatibility based on all analyzed information with better fallback logic"""
        
        self._log("Determining final compatibility...")
        self._log(f"Architecture info available: {app_info.architecture_info is not None}")
        self._log(f"Supported platforms: {app_info.supported_platforms}")
        
        # If we have architecture info, use it
        if app_info.architecture_info and app_info.architecture_info.architectures:
            arch_info = app_info.architecture_info
            self._log(f"Using detected architectures: {arch_info.architectures}")
            
            # Determine compatibility based on architectures
            has_simulator_arch = arch_info.has_x86_64 or arch_info.has_i386
            has_device_arch = arch_info.has_arm64 or arch_info.has_armv7
            
            self._log(f"Has simulator arch: {has_simulator_arch}")
            self._log(f"Has device arch: {has_device_arch}")
            
            if has_simulator_arch and has_device_arch:
                self._log("Universal app detected")
                return AppCompatibility.UNIVERSAL
            elif has_simulator_arch and not has_device_arch:
                self._log("Simulator-only app detected")
                return AppCompatibility.SIMULATOR_COMPATIBLE
            elif has_device_arch and not has_simulator_arch:
                self._log("Device-only app detected")
                return AppCompatibility.DEVICE_ONLY
            else:
                self._log("Unsupported architecture combination")
                return AppCompatibility.UNSUPPORTED_ARCHITECTURE
        
        # Fallback to platform-based detection when architecture detection fails
        self._log("No architecture information available, using platform-based detection")
        
        if 'iPhoneSimulator' in app_info.supported_platforms:
            self._log("Platform indicates simulator compatibility")
            return AppCompatibility.SIMULATOR_COMPATIBLE
        elif 'iPhoneOS' in app_info.supported_platforms and 'iPhoneSimulator' not in app_info.supported_platforms:
            self._log("Platform indicates device-only compatibility")
            return AppCompatibility.DEVICE_ONLY
        else:
            self._log("Unknown platform compatibility")
            return AppCompatibility.UNKNOWN
            

    def get_compatibility_summary(self, compatibility: AppCompatibility, app_info: AppInfo) -> Dict:
        """Get a human-readable summary of the compatibility analysis"""
        
        summary = {
            'status': compatibility.value,
            'can_install': False,
            'can_run_immediately': False,
            'requires_processing': False,
            'app_details': {
                'name': app_info.display_name or app_info.app_name or 'Unknown',
                'bundle_id': app_info.bundle_id,
                'version': app_info.version,
                'build': app_info.build_version,
                'min_os': app_info.min_os_version,
                'platforms': app_info.supported_platforms,
                'architectures': app_info.architecture_info.architectures if app_info.architecture_info else [],
                'file_size_mb': round(app_info.file_size / (1024 * 1024), 2) if app_info.file_size else 0
            }
        }
        
        # Set flags based on compatibility
        if compatibility == AppCompatibility.SIMULATOR_COMPATIBLE:
            summary['can_install'] = True
            summary['can_run_immediately'] = True
            summary['message'] = "✅ App is compatible with iOS Simulator"
            
        elif compatibility == AppCompatibility.UNIVERSAL:
            summary['can_install'] = True
            summary['can_run_immediately'] = False
            summary['requires_processing'] = True
            summary['message'] = "🔄 App contains both device and simulator code - processing required"
            
        elif compatibility == AppCompatibility.DEVICE_ONLY:
            summary['can_install'] = False
            summary['message'] = "📱 App is built for physical devices only"
            
        elif compatibility == AppCompatibility.CORRUPTED:
            summary['message'] = "❌ App file appears to be corrupted"
            
        elif compatibility == AppCompatibility.INVALID_FORMAT:
            summary['message'] = "❌ Invalid app format or structure"
            
        elif compatibility == AppCompatibility.MISSING_COMPONENTS:
            summary['message'] = "❌ App is missing required components"
            
        else:
            summary['message'] = "❓ Could not determine app compatibility"
        
        if app_info.error_details:
            summary['error'] = app_info.error_details
        
        return summary