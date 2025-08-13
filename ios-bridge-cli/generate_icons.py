#!/usr/bin/env python3
"""
Icon generation script for iOS Bridge
Converts the SVG icon to all required formats for cross-platform Electron distribution
"""

import os
import subprocess
import sys
from pathlib import Path

def check_dependencies():
    """Check if required tools are installed"""
    tools = ['inkscape', 'convert']  # inkscape for SVG conversion, imagemagick for ICO
    missing = []
    
    for tool in tools:
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
            print(f"✅ {tool} is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(tool)
            print(f"❌ {tool} is not available")
    
    if missing:
        print("\n🔧 Install missing dependencies:")
        if 'inkscape' in missing:
            print("  macOS: brew install inkscape")
            print("  Linux: sudo apt-get install inkscape")
            print("  Windows: Download from https://inkscape.org/")
        
        if 'convert' in missing:
            print("  macOS: brew install imagemagick")
            print("  Linux: sudo apt-get install imagemagick")
            print("  Windows: Download from https://imagemagick.org/")
        
        return False
    
    return True

def generate_png_from_svg(svg_path, output_path, size):
    """Generate PNG from SVG using inkscape"""
    try:
        cmd = [
            'inkscape',
            '--export-type=png',
            f'--export-width={size}',
            f'--export-height={size}',
            f'--export-filename={output_path}',
            str(svg_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Generated {output_path} ({size}x{size})")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate {output_path}: {e}")
        return False

def generate_ico_from_png(png_files, ico_path):
    """Generate ICO file from multiple PNG files using ImageMagick"""
    try:
        cmd = ['convert'] + png_files + [str(ico_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Generated {ico_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate {ico_path}: {e}")
        return False

def generate_icns_from_png(png_files, icns_path):
    """Generate ICNS file for macOS"""
    try:
        # Create iconset directory
        iconset_dir = icns_path.parent / f"{icns_path.stem}.iconset"
        iconset_dir.mkdir(exist_ok=True)
        
        # Copy and rename PNG files to iconset format
        size_map = {
            16: ['icon_16x16.png'],
            32: ['icon_16x16@2x.png', 'icon_32x32.png'],
            64: ['icon_32x32@2x.png'],
            128: ['icon_128x128.png'],
            256: ['icon_128x128@2x.png', 'icon_256x256.png'],
            512: ['icon_256x256@2x.png', 'icon_512x512.png'],
            1024: ['icon_512x512@2x.png']
        }
        
        png_by_size = {int(png.stem.split('_')[1]): png for png in png_files}
        
        for size, names in size_map.items():
            if size in png_by_size:
                for name in names:
                    target = iconset_dir / name
                    subprocess.run(['cp', str(png_by_size[size]), str(target)], check=True)
        
        # Generate ICNS
        cmd = ['iconutil', '-c', 'icns', str(iconset_dir)]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Clean up iconset directory
        subprocess.run(['rm', '-rf', str(iconset_dir)], check=True)
        
        print(f"✅ Generated {icns_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate {icns_path}: {e}")
        return False

def main():
    # Paths
    base_dir = Path(__file__).parent
    assets_dir = base_dir / "ios_bridge_cli" / "electron_app" / "assets" / "icons"
    svg_path = assets_dir / "icon.svg"
    
    # Check if SVG exists
    if not svg_path.exists():
        print(f"❌ SVG icon not found at {svg_path}")
        return 1
    
    print("🎨 iOS Bridge Icon Generator")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Missing required dependencies. Please install them and try again.")
        return 1
    
    # Icon sizes needed for different platforms
    sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
    
    print(f"\n📁 Creating icons in {assets_dir}")
    
    # Generate PNG files
    png_files = []
    for size in sizes:
        png_path = assets_dir / f"icon_{size}.png"
        if generate_png_from_svg(svg_path, png_path, size):
            png_files.append(png_path)
    
    # Generate platform-specific formats
    print("\n🖼️ Generating platform-specific formats...")
    
    # Windows ICO (16, 32, 48, 256)
    ico_pngs = [assets_dir / f"icon_{size}.png" for size in [16, 32, 48, 256] 
                if (assets_dir / f"icon_{size}.png").exists()]
    if ico_pngs:
        generate_ico_from_png([str(p) for p in ico_pngs], assets_dir / "icon.ico")
    
    # macOS ICNS (if on macOS)
    if sys.platform == "darwin":
        icns_pngs = [assets_dir / f"icon_{size}.png" for size in [16, 32, 128, 256, 512, 1024] 
                     if (assets_dir / f"icon_{size}.png").exists()]
        if icns_pngs:
            generate_icns_from_png(icns_pngs, assets_dir / "icon.icns")
    
    # Copy main icon for Electron
    main_icon = assets_dir / "icon_512.png"
    if main_icon.exists():
        subprocess.run(['cp', str(main_icon), str(assets_dir / "icon.png")], check=True)
        print(f"✅ Generated main icon.png")
    
    print(f"\n🎉 Icon generation complete!")
    print(f"📁 All icons saved to: {assets_dir}")
    
    # List generated files
    print("\n📋 Generated files:")
    for file in sorted(assets_dir.glob("icon*")):
        print(f"  - {file.name}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())