#!/usr/bin/env python3
"""
Test script to validate the iOS Bridge CLI package structure and functionality
"""

import os
import sys
import importlib
from pathlib import Path


def test_package_structure():
    """Test that all required files exist"""
    print("📂 Testing package structure...")
    
    required_files = [
        "ios_bridge_cli/__init__.py",
        "ios_bridge_cli/cli.py", 
        "ios_bridge_cli/client.py",
        "ios_bridge_cli/exceptions.py",
        "ios_bridge_cli/app_manager.py",
        "ios_bridge_cli/electron_app/package.json",
        "ios_bridge_cli/electron_app/src/main.js",
        "ios_bridge_cli/electron_app/src/renderer.js",
        "ios_bridge_cli/electron_app/src/renderer.html",
        "ios_bridge_cli/electron_app/src/styles.css",
        "ios_bridge_cli/electron_app/src/preload.js",
        "setup.py",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "MANIFEST.in"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path}")
    
    if missing_files:
        print("❌ Missing files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    print("✅ Package structure is complete")
    return True


def test_imports():
    """Test that all modules can be imported"""
    print("\n🐍 Testing Python imports...")
    
    modules = [
        "ios_bridge_cli",
        "ios_bridge_cli.cli",
        "ios_bridge_cli.client", 
        "ios_bridge_cli.exceptions",
        "ios_bridge_cli.app_manager"
    ]
    
    failed_imports = []
    
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            print(f"  ✅ {module_name}")
        except ImportError as e:
            print(f"  ❌ {module_name}: {e}")
            failed_imports.append((module_name, str(e)))
    
    if failed_imports:
        print("❌ Import failures:")
        for module, error in failed_imports:
            print(f"  - {module}: {error}")
        return False
    
    print("✅ All modules import successfully")
    return True


def test_cli_entry_point():
    """Test that the CLI entry point exists"""
    print("\n🖥️  Testing CLI entry point...")
    
    try:
        from ios_bridge_cli.cli import main
        print("  ✅ CLI main function found")
        
        # Try to import click for CLI functionality
        import click
        print("  ✅ Click library available")
        
        return True
    except ImportError as e:
        print(f"  ❌ CLI entry point error: {e}")
        return False


def test_electron_app():
    """Test that Electron app files are valid"""
    print("\n⚡ Testing Electron app...")
    
    electron_path = Path("ios_bridge_cli/electron_app")
    
    # Check package.json
    package_json = electron_path / "package.json"
    if package_json.exists():
        try:
            import json
            with open(package_json) as f:
                package_data = json.load(f)
            
            required_fields = ["name", "version", "main", "scripts"]
            missing_fields = [field for field in required_fields if field not in package_data]
            
            if missing_fields:
                print(f"  ❌ package.json missing fields: {missing_fields}")
                return False
            
            print("  ✅ package.json is valid")
        except json.JSONDecodeError as e:
            print(f"  ❌ package.json is invalid: {e}")
            return False
    else:
        print("  ❌ package.json not found")
        return False
    
    # Check main files
    required_js_files = ["src/main.js", "src/renderer.js", "src/preload.js"]
    for js_file in required_js_files:
        js_path = electron_path / js_file
        if js_path.exists():
            print(f"  ✅ {js_file}")
        else:
            print(f"  ❌ {js_file} not found")
            return False
    
    print("✅ Electron app files are present")
    return True


def test_dependencies():
    """Test that all dependencies can be imported"""
    print("\n📦 Testing dependencies...")
    
    dependencies = [
        ("click", "Click CLI framework"),
        ("requests", "HTTP requests library"),
        ("PIL", "Pillow image library"),
        ("psutil", "Process utilities"),
    ]
    
    missing_deps = []
    
    for dep, description in dependencies:
        try:
            importlib.import_module(dep)
            print(f"  ✅ {dep} ({description})")
        except ImportError:
            print(f"  ❌ {dep} ({description}) - not installed")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies are available")
    return True


def main():
    """Run all tests"""
    print("🧪 iOS Bridge CLI Package Tests")
    print("=" * 40)
    
    tests = [
        ("Package Structure", test_package_structure),
        ("Python Imports", test_imports),
        ("CLI Entry Point", test_cli_entry_point),
        ("Electron App", test_electron_app),
        ("Dependencies", test_dependencies),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}:")
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"💥 {test_name} crashed: {e}")
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Package is ready.")
        return 0
    else:
        print(f"❌ {total - passed} test(s) failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())