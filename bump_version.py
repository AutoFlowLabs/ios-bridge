#!/usr/bin/env python3
"""
Version bumping script for iOS Bridge CLI release
Automatically updates version numbers in all required files
"""

import sys
import json
import re
import argparse
from pathlib import Path

def update_pyproject_toml(file_path: Path, new_version: str) -> bool:
    """Update version in pyproject.toml"""
    try:
        content = file_path.read_text()
        updated_content = re.sub(
            r'version\s*=\s*"[^"]*"',
            f'version = "{new_version}"',
            content
        )
        file_path.write_text(updated_content)
        print(f"✅ Updated {file_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to update {file_path}: {e}")
        return False

def update_package_json(file_path: Path, new_version: str) -> bool:
    """Update version in package.json"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        data['version'] = new_version
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')  # Add trailing newline
        
        print(f"✅ Updated {file_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to update {file_path}: {e}")
        return False

def update_github_workflow(file_path: Path, new_version: str) -> bool:
    """Update default version in GitHub workflow"""
    try:
        content = file_path.read_text()
        updated_content = re.sub(
            r"default:\s*['\"]v[^'\"]*['\"]",
            f"default: 'v{new_version}'",
            content
        )
        file_path.write_text(updated_content)
        print(f"✅ Updated {file_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to update {file_path}: {e}")
        return False

def update_version_file(file_path: Path, new_version: str) -> bool:
    """Update version in __init__.py if it exists"""
    try:
        if not file_path.exists():
            # Create __init__.py with version if it doesn't exist
            file_path.write_text(f'__version__ = "{new_version}"\n')
            print(f"✅ Created {file_path}")
            return True
        
        content = file_path.read_text()
        updated_content = re.sub(
            r'__version__\s*=\s*["\'][^"\']*["\']',
            f'__version__ = "{new_version}"',
            content
        )
        
        # If __version__ wasn't found, add it
        if '__version__' not in content:
            updated_content = f'__version__ = "{new_version}"\n' + content
        
        file_path.write_text(updated_content)
        print(f"✅ Updated {file_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to update {file_path}: {e}")
        return False

def validate_version(version: str) -> bool:
    """Validate semantic version format"""
    pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$'
    return bool(re.match(pattern, version))

def get_current_version() -> str:
    """Get current version from pyproject.toml"""
    pyproject_path = Path("ios-bridge-cli/pyproject.toml")
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        match = re.search(r'version\s*=\s*"([^"]*)"', content)
        if match:
            return match.group(1)
    return "unknown"

def main():
    parser = argparse.ArgumentParser(
        description="Bump version in all iOS Bridge CLI files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bump_version.py 1.0.2           # Bump to version 1.0.2
  python bump_version.py 1.1.0           # Bump to version 1.1.0
  python bump_version.py 2.0.0-beta.1    # Bump to pre-release version
  python bump_version.py --current       # Show current version
        """
    )
    
    parser.add_argument(
        'version',
        nargs='?',
        help='New version number (e.g., 1.0.2)'
    )
    
    parser.add_argument(
        '--current',
        action='store_true',
        help='Show current version and exit'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    
    args = parser.parse_args()
    
    # Show current version
    current_version = get_current_version()
    print(f"📦 Current version: {current_version}")
    
    if args.current:
        return
    
    if not args.version:
        print("❌ Please provide a version number")
        parser.print_help()
        sys.exit(1)
    
    new_version = args.version
    
    # Validate version format
    if not validate_version(new_version):
        print(f"❌ Invalid version format: {new_version}")
        print("   Expected format: X.Y.Z or X.Y.Z-suffix (e.g., 1.0.2, 2.0.0-beta.1)")
        sys.exit(1)
    
    print(f"🚀 Bumping version from {current_version} to {new_version}")
    
    if args.dry_run:
        print("🔍 DRY RUN - No files will be modified")
    
    # Define files to update
    files_to_update = [
        {
            'path': Path("ios-bridge-cli/pyproject.toml"),
            'update_func': update_pyproject_toml,
            'description': 'Python package version'
        },
        {
            'path': Path("ios-bridge-cli/ios_bridge_cli/electron_app/package.json"),
            'update_func': update_package_json,
            'description': 'Electron app version'
        },
        {
            'path': Path(".github/workflows/build-and-release.yml"),
            'update_func': update_github_workflow,
            'description': 'GitHub workflow default version'
        },
        {
            'path': Path("ios-bridge-cli/ios_bridge_cli/__init__.py"),
            'update_func': update_version_file,
            'description': 'Python package __version__'
        }
    ]
    
    success_count = 0
    total_count = len(files_to_update)
    
    print(f"\n📝 Updating {total_count} files:")
    
    for file_info in files_to_update:
        file_path = file_info['path']
        update_func = file_info['update_func']
        description = file_info['description']
        
        print(f"\n🔧 {description}")
        print(f"   File: {file_path}")
        
        if not file_path.exists():
            print(f"   ⚠️  File not found")
            if 'optional' not in str(file_path):
                continue
        
        if args.dry_run:
            print(f"   📋 Would update to version {new_version}")
            success_count += 1
        else:
            if update_func(file_path, new_version):
                success_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   ✅ Successfully updated: {success_count}/{total_count} files")
    
    if success_count == total_count:
        if not args.dry_run:
            print(f"\n🎉 All files updated to version {new_version}!")
            print(f"\n🚀 Next steps:")
            print(f"   git add .")
            print(f"   git commit -m \"Bump version to {new_version}\"")
            print(f"   git push origin main")
            print(f"   git tag -a v{new_version} -m \"Release v{new_version}\"")
            print(f"   git push origin v{new_version}")
        else:
            print(f"\n✅ Dry run completed - all files would be updated successfully")
    else:
        print(f"\n❌ Some files failed to update. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()