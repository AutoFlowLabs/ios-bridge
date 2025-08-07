import os
import shutil
import tempfile
import plistlib
import subprocess
from pathlib import Path

def create_simulator_test_app():
    """Create a proper simulator test app"""
    
    print("🏗️ Creating simulator test app...")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    app_bundle = os.path.join(temp_dir, "SimulatorTest.app")
    os.makedirs(app_bundle)
    
    print(f"📁 App bundle: {app_bundle}")
    
    # Create Info.plist with proper simulator platform
    info_plist = {
        'CFBundleIdentifier': 'com.nativebridge.simulatortest',
        'CFBundleName': 'SimulatorTest',
        'CFBundleDisplayName': 'Simulator Test App',
        'CFBundleVersion': '1.0',
        'CFBundleShortVersionString': '1.0',
        'CFBundleExecutable': 'SimulatorTest',
        'CFBundlePackageType': 'APPL',
        'LSRequiresIPhoneOS': True,
        'UIDeviceFamily': [1, 2],  # iPhone and iPad
        'MinimumOSVersion': '12.0',
        'DTPlatformName': 'iphonesimulator',
        'DTSDKName': 'iphonesimulator18.2',
        'DTPlatformVersion': '18.2',
        'DTXcode': '1500',
        'DTXcodeBuild': '15A240d',
        'UISupportedInterfaceOrientations': [
            'UIInterfaceOrientationPortrait',
            'UIInterfaceOrientationLandscapeLeft',
            'UIInterfaceOrientationLandscapeRight'
        ]
    }
    
    info_plist_path = os.path.join(app_bundle, 'Info.plist')
    with open(info_plist_path, 'wb') as f:
        plistlib.dump(info_plist, f)
    
    print("✅ Created Info.plist")
    
    # Create a simple Swift executable (fixed version)
    swift_code = '''import UIKit
import Foundation

class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        
        window = UIWindow(frame: UIScreen.main.bounds)
        
        let viewController = UIViewController()
        viewController.view.backgroundColor = .systemBlue
        
        let label = UILabel()
        label.text = "🧪 Simulator Test App\\n✅ x86_64 Architecture\\n🚀 Ready for Testing!"
        label.numberOfLines = 0
        label.textAlignment = .center
        label.textColor = .white
        label.font = UIFont.systemFont(ofSize: 18, weight: .bold)
        label.translatesAutoresizingMaskIntoConstraints = false
        
        viewController.view.addSubview(label)
        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: viewController.view.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: viewController.view.centerYAnchor),
            label.leadingAnchor.constraint(greaterThanOrEqualTo: viewController.view.leadingAnchor, constant: 20),
            label.trailingAnchor.constraint(lessThanOrEqualTo: viewController.view.trailingAnchor, constant: -20)
        ])
        
        window?.rootViewController = viewController
        window?.makeKeyAndVisible()
        
        print("🎯 Simulator Test App launched successfully!")
        return true
    }
}

// Main entry point
UIApplicationMain(
    CommandLine.argc,
    CommandLine.unsafeArgv,
    nil,
    NSStringFromClass(AppDelegate.self)
)
'''
    
    # Write Swift source
    swift_file = os.path.join(temp_dir, 'main.swift')
    with open(swift_file, 'w') as f:
        f.write(swift_code)
    
    print("✅ Created Swift source")
    
    # Compile Swift for simulator
    executable_path = os.path.join(app_bundle, 'SimulatorTest')
    
    # First, check available SDKs
    sdk_cmd = ['xcrun', '--show-sdk-path', '--sdk', 'iphonesimulator']
    sdk_result = subprocess.run(sdk_cmd, capture_output=True, text=True)
    
    if sdk_result.returncode != 0:
        print("❌ Could not find iOS Simulator SDK")
        return None
    
    sdk_path = sdk_result.stdout.strip()
    print(f"📱 Using SDK: {sdk_path}")
    
    compile_cmd = [
        'xcrun', 'swiftc',
        '-target', 'x86_64-apple-ios12.0-simulator',
        '-sdk', sdk_path,
        '-framework', 'UIKit',
        '-framework', 'Foundation',
        '-o', executable_path,
        swift_file
    ]
    
    print("🔨 Compiling Swift code for x86_64 simulator...")
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Compilation successful!")
        
        # Verify architecture
        lipo_cmd = ['lipo', '-info', executable_path]
        lipo_result = subprocess.run(lipo_cmd, capture_output=True, text=True)
        print(f"🔍 Architecture info: {lipo_result.stdout.strip()}")
        
        return app_bundle
    else:
        print(f"❌ Compilation failed: {result.stderr}")
        print(f"Stdout: {result.stdout}")
        
        # Try alternative approach - create a simple C program instead
        print("🔄 Trying alternative C approach...")
        return create_simple_c_app(temp_dir, app_bundle)

def create_simple_c_app(temp_dir, app_bundle):
    """Create a simple C-based iOS app as fallback"""
    
    print("🔨 Creating simple C-based app...")
    
    # Create a minimal C program
    c_code = '''#include <stdio.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    printf("🧪 Simulator Test App (C version)\\n");
    printf("✅ x86_64 Architecture\\n");
    printf("🚀 Ready for Testing!\\n");
    
    // Keep the app running
    while(1) {
        sleep(1);
    }
    
    return 0;
}
'''
    
    # Write C source
    c_file = os.path.join(temp_dir, 'main.c')
    with open(c_file, 'w') as f:
        f.write(c_code)
    
    # Compile C for simulator
    executable_path = os.path.join(app_bundle, 'SimulatorTest')
    
    compile_cmd = [
        'xcrun', 'clang',
        '-target', 'x86_64-apple-ios12.0-simulator',
        '-isysroot', '/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk',
        '-o', executable_path,
        c_file
    ]
    
    print("🔨 Compiling C code for x86_64 simulator...")
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ C compilation successful!")
        
        # Verify architecture
        lipo_cmd = ['lipo', '-info', executable_path]
        lipo_result = subprocess.run(lipo_cmd, capture_output=True, text=True)
        print(f"🔍 Architecture info: {lipo_result.stdout.strip()}")
        
        return app_bundle
    else:
        print(f"❌ C compilation also failed: {result.stderr}")
        return None

def create_simple_shell_app(temp_dir, app_bundle):
    """Create a shell script based app as final fallback"""
    
    print("🔨 Creating shell script app (final fallback)...")
    
    # Create a shell script executable
    shell_script = '''#!/bin/bash
echo "🧪 Simulator Test App (Shell version)"
echo "✅ Architecture: $(uname -m)"
echo "🚀 Ready for Testing!"

# Keep running
while true; do
    sleep 1
done
'''
    
    executable_path = os.path.join(app_bundle, 'SimulatorTest')
    with open(executable_path, 'w') as f:
        f.write(shell_script)
    
    # Make executable
    os.chmod(executable_path, 0o755)
    
    print("✅ Shell script app created")
    
    # Check what architecture the shell reports
    arch_cmd = ['file', executable_path]
    arch_result = subprocess.run(arch_cmd, capture_output=True, text=True)
    print(f"🔍 File info: {arch_result.stdout.strip()}")
    
    return app_bundle

def test_with_session_manager(app_bundle_path):
    """Test the app with your session manager"""
    print("\n🧪 Testing with session manager...")
    
    try:
        # Import your session manager
        import sys
        sys.path.append('/Users/himanshukukreja/autoflow/ios-bridge')
        from app.services.session_manager import session_manager
        
        # List sessions
        sessions = session_manager.list_sessions()
        print(f"📱 Found {len(sessions)} active sessions")
        
        if not sessions:
            print("🏗️ Creating new simulator session...")
            session_id = session_manager.create_session('iPhone 14', '18.2')
        else:
            session_id = sessions[0]['session_id']
            print(f"📱 Using existing session: {session_id}")
        
        # Install the app
        print(f"📦 Installing app: {app_bundle_path}")
        result = session_manager.install_app(session_id, app_bundle_path)
        
        print("\n🎯 Installation result:")
        print(f"   Success: {result['success']}")
        print(f"   Message: {result['message']}")
        print(f"   Compatibility: {result['compatibility']}")
        
        if result.get('app_info'):
            architectures = result['app_info'].get('architectures', [])
            print(f"   Architectures: {architectures}")
            
            if 'x86_64' in architectures:
                print("   ✅ x86_64 architecture detected!")
            elif 'arm64' in architectures:
                print("   ⚠️  ARM64 detected (device architecture)")
            else:
                print(f"   ❓ Unknown architectures: {architectures}")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    app_bundle = create_simulator_test_app()
    
    if app_bundle:
        print(f"\n🎯 Test app created successfully!")
        print(f"📁 Location: {app_bundle}")
        
        # Check if the executable exists and its size
        executable_path = os.path.join(app_bundle, 'SimulatorTest')
        if os.path.exists(executable_path):
            print(f"📊 Executable size: {os.path.getsize(executable_path)} bytes")
        else:
            print("❌ Executable not found")
            app_bundle = None
    
    if app_bundle:
        # Test with your session manager
        success = test_with_session_manager(app_bundle)
        
        if success:
            print("\n🎉 SUCCESS! Your system can install simulator apps!")
        else:
            print("\n❌ Installation failed - check the logs above")
    else:
        print("❌ Failed to create test app")