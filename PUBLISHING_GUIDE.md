# iOS Bridge CLI Publishing Guide

Complete guide for publishing and distributing the iOS Bridge CLI package.

## Table of Contents

1. [Pre-Publishing Checklist](#pre-publishing-checklist)
2. [PyPI Publishing](#pypi-publishing)
3. [Electron Desktop App Distribution](#electron-desktop-app-distribution)
4. [GitHub Releases](#github-releases)
5. [Distribution Platforms](#distribution-platforms)
6. [Marketing and Promotion](#marketing-and-promotion)
7. [Post-Release Tasks](#post-release-tasks)

---

## Pre-Publishing Checklist

### ✅ Code Quality and Testing

```bash
# Run all tests
cd ios-bridge-cli
python -m pytest tests/ -v

# Check code formatting
black --check .
flake8 .

# Type checking
mypy ios_bridge_cli/

# Security scan
safety check
bandit -r ios_bridge_cli/

# Test package installation
pip install -e .
ios-bridge --help
```

### ✅ Documentation Review

- [ ] README.md is complete and up-to-date
- [ ] Installation instructions are tested on all platforms
- [ ] API documentation is generated and accurate
- [ ] Usage examples work correctly
- [ ] Screenshots/GIFs are current
- [ ] License file is included
- [ ] Changelog is updated

### ✅ Version Management

```bash
# Update version in pyproject.toml
# Update version in package.json
# Update version in __init__.py
# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### ✅ Platform Testing

**Test on each platform:**
- [ ] macOS (Intel + Apple Silicon)
- [ ] Windows (10/11, x64/x86)
- [ ] Linux (Ubuntu/Debian/CentOS)

**Test installation methods:**
- [ ] PyPI package installation
- [ ] GitHub release packages
- [ ] Source installation
- [ ] Development installation

### ✅ Dependencies and Security

```bash
# Check for vulnerabilities
pip-audit

# Update dependencies
pip-tools compile --upgrade requirements.in

# Check license compatibility
pip-licenses --format=table
```

---

## PyPI Publishing

### 1. Setup PyPI Account

1. **Create accounts:**
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

2. **Generate API tokens:**
   - Go to Account Settings > API tokens
   - Create token for the project
   - Store securely (use for CI/CD)

3. **Configure credentials:**
   ```bash
   # Create ~/.pypirc
   cat > ~/.pypirc << EOF
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-your-api-token

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-your-test-api-token
   EOF
   chmod 600 ~/.pypirc
   ```

### 2. Build and Test Package

```bash
cd ios-bridge-cli

# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build package
python -m build

# Check package
twine check dist/*

# Test upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ ios-bridge-cli

# Test the installed package
ios-bridge --help
```

### 3. Publish to PyPI

```bash
# Upload to PyPI (production)
twine upload dist/*

# Verify on PyPI
# Visit: https://pypi.org/project/ios-bridge-cli/

# Test installation from PyPI
pip install ios-bridge-cli
```

### 4. Automated PyPI Publishing

The GitHub Actions workflow will automatically publish to PyPI when you create a release tag:

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

---

## Electron Desktop App Distribution

The iOS Bridge CLI includes an integrated Electron desktop app that provides a native streaming experience. The distribution strategy uses auto-download functionality to provide users with platform-specific binaries.

### Architecture Overview

**Development Mode (Current Setup):**
- CLI bundles Electron source code
- Requires Node.js and npm for `electron` dependency
- Auto-detected when running from source directory

**Production Mode (Auto-Download):**
- CLI downloads pre-built platform-specific binaries
- No Node.js requirement for end users
- Cached locally for subsequent use

### Building Electron Apps for Distribution

#### 1. Build Cross-Platform Binaries

```bash
cd ios_bridge_cli/electron_app

# Install dependencies
npm install

# Build for all platforms
npm run build-mac     # macOS (DMG + ZIP) 
npm run build-win     # Windows (NSIS + Portable)
npm run build-linux   # Linux (AppImage + DEB + RPM)

# Or build for current platform only
npm run build
```

#### 2. Package Built Apps for GitHub Releases

The built apps need to be packaged as ZIP files with specific naming convention:

```bash
# After building, package the distributables
cd dist

# macOS
zip -r ios-bridge-desktop-mac-arm64.zip "mac-arm64/iOS Bridge.app"
zip -r ios-bridge-desktop-mac-x64.zip "mac-x64/iOS Bridge.app"

# Windows  
zip -r ios-bridge-desktop-windows-x64.zip "win-unpacked/iOS Bridge.exe"

# Linux
zip -r ios-bridge-desktop-linux-x64.zip "linux-unpacked/ios-bridge-desktop"
```

**Required File Names:**
- `ios-bridge-desktop-mac-arm64.zip`
- `ios-bridge-desktop-mac-x64.zip` 
- `ios-bridge-desktop-windows-x64.zip`
- `ios-bridge-desktop-linux-x64.zip`

### Auto-Download Configuration

The CLI automatically detects the user's platform and downloads the appropriate binary:

**Cache Locations:**
- **macOS**: `~/Library/Caches/ios-bridge/desktop-apps/`
- **Windows**: `%LOCALAPPDATA%/ios-bridge/cache/desktop-apps/`
- **Linux**: `~/.cache/ios-bridge/desktop-apps/`

**Version Management:**
- Apps are cached per CLI version (`v1.0.0`, `v1.0.1`, etc.)
- Automatic updates when CLI version changes
- Fallback to bundled app if download fails

### User Experience Flow

1. **User installs CLI:**
   ```bash
   pip install ios-bridge-cli  # ~5MB package, fast install
   ```

2. **First desktop usage:**
   ```bash
   ios-bridge desktop
   # 🏗️ Downloading iOS Bridge Desktop for macOS...
   # ████████████████████████████████████████ 25.4MB / 25.4MB
   # ✅ iOS Bridge Desktop installed successfully
   # 🚀 Starting iOS Bridge Desktop
   ```

3. **Subsequent usage:**
   ```bash
   ios-bridge desktop  # Instant launch from cache
   ```

### Development vs Production Behavior

The CLI automatically detects the environment:

**Development Mode (Source Directory):**
- Uses bundled Electron source (`ios_bridge_cli/electron_app/`)
- Requires `npm install` and `electron` dependency
- Enables live reloading for development

**Production Mode (Installed via pip):**
- Downloads platform-specific binary from GitHub releases
- No Node.js dependency required
- Cached for performance

### Testing the Auto-Download

Before releasing, test the auto-download functionality:

```bash
# Build test release assets
cd ios_bridge_cli/electron_app
npm run build-mac

# Package for testing
zip -r ios-bridge-desktop-mac-arm64.zip "dist/mac-arm64/iOS Bridge.app"

# Upload to GitHub release (draft)
# Test CLI download functionality
pip install ios-bridge-cli
ios-bridge desktop  # Should download and launch
```

### Troubleshooting

**Download Fails:**
- CLI automatically falls back to bundled app (requires Node.js)
- Check GitHub release assets exist and are properly named
- Verify internet connection and GitHub access

**App Won't Launch:**
- On macOS: Check Gatekeeper settings and app signing
- On Linux: Verify executable permissions
- Check cache directory permissions

**Cache Issues:**
```bash
# Clear cache and force re-download
python -c "from ios_bridge_cli.app_manager import ElectronAppManager; ElectronAppManager().clear_cache()"
```

---

## GitHub Releases

### 1. Prepare Release Assets

#### A. Build CLI Packages
```bash
# Build Python CLI packages
cd ios-bridge-cli
python -m build

# This creates:
# - dist/ios_bridge_cli-1.0.0-py3-none-any.whl
# - dist/ios_bridge_cli-1.0.0.tar.gz
```

#### B. Build Electron Desktop Apps
```bash
# Build Electron apps for all platforms
cd ios_bridge_cli/electron_app
npm install
npm run build-mac
npm run build-win  
npm run build-linux

# Package for GitHub release
cd dist

# macOS
zip -r ios-bridge-desktop-mac-arm64.zip "mac-arm64/iOS Bridge.app"
zip -r ios-bridge-desktop-mac-x64.zip "mac-x64/iOS Bridge.app"

# Windows
zip -r ios-bridge-desktop-windows-x64.zip "win-unpacked/iOS Bridge.exe"

# Linux  
zip -r ios-bridge-desktop-linux-x64.zip "linux-unpacked/ios-bridge-desktop"

# Move to release directory
mkdir -p ../../dist/release/
mv *.zip ../../dist/release/
```

#### C. Generate Checksums
```bash
cd dist/release
sha256sum * > checksums.txt
```

### 2. Create GitHub Release

**Option 1: GitHub UI**
1. Go to your repository on GitHub
2. Click "Releases" → "Create a new release"
3. Tag version: `v1.0.0`
4. Release title: `iOS Bridge CLI v1.0.0`
5. Upload release assets
6. Write release notes

**Option 2: GitHub CLI**
```bash
# Create release with CLI and Electron assets
gh release create v1.0.0 \
  --title "iOS Bridge CLI v1.0.0" \
  --notes-file RELEASE_NOTES.md \
  dist/ios_bridge_cli-1.0.0-py3-none-any.whl \
  dist/ios_bridge_cli-1.0.0.tar.gz \
  dist/release/ios-bridge-desktop-mac-arm64.zip \
  dist/release/ios-bridge-desktop-mac-x64.zip \
  dist/release/ios-bridge-desktop-windows-x64.zip \
  dist/release/ios-bridge-desktop-linux-x64.zip \
  dist/release/checksums.txt
```

**Option 3: Automated (GitHub Actions)**
The workflow automatically creates releases when you push tags.

### 3. Release Notes Template

```markdown
## iOS Bridge CLI v1.0.0

### 🎉 New Features
- Cross-platform desktop client with Electron integration
- WebSocket and WebRTC streaming support
- Real-time iOS simulator interaction
- Session management and recording

### 🐛 Bug Fixes
- Fixed coordinate mapping issues in WebRTC mode
- Improved connection stability
- Better error handling and recovery

### 🔧 Improvements  
- Enhanced performance for concurrent users
- Better resource management
- Improved documentation

### 📦 Downloads
- **macOS**: `ios-bridge-cli-v1.0.0-macos.tar.gz`
- **Windows**: `ios-bridge-cli-v1.0.0-windows.zip`
- **Linux**: `ios-bridge-cli-v1.0.0-linux.tar.gz`
- **Python Package**: Available on [PyPI](https://pypi.org/project/ios-bridge-cli/)

### 📋 Installation
See the [Installation Guide](INSTALLATION_GUIDE.md) for detailed instructions.

### 🔐 Checksums
Verify downloads with `checksums.txt`.

### 🙏 Contributors
Thanks to all contributors who made this release possible!
```

---

## Release Methods

There are two ways to create and publish a release: **Automated CI/CD** (recommended) and **Manual Release**.

### 🤖 Method 1: Automated CI/CD Release (Recommended)

The GitHub Actions workflow automatically builds, packages, and publishes everything when you push a git tag.

#### Prerequisites Setup (One-Time)

1. **Configure PyPI API Token:**
   ```bash
   # Go to: https://pypi.org/manage/account/token/
   # Create new token with scope: "Entire account"
   # Copy the token (starts with pypi-)
   ```

2. **Add GitHub Secrets:**
   - Go to: `https://github.com/YOUR_USERNAME/ios-bridge/settings/secrets/actions`
   - Add secret: `PYPI_API_TOKEN` = your PyPI token
   - `GITHUB_TOKEN` is automatically provided

3. **Update Repository URL** (if needed):
   ```bash
   # In ios_bridge_cli/app_manager.py, verify line 28:
   GITHUB_REPO = "YOUR_USERNAME/ios-bridge"  # Should match your repo
   ```

#### Release Process

1. **Bump Version:**
   ```bash
   cd ios-bridge-cli
   
   # Update version in pyproject.toml
   sed -i '' 's/version = "1.0.0"/version = "1.0.1"/' pyproject.toml
   
   # Or manually edit:
   # version = "1.0.1"
   ```

2. **Commit Changes:**
   ```bash
   git checkout main
   git pull origin main
   git add .
   git commit -m "Release v1.0.1: Auto-download functionality and enhanced documentation"
   ```

3. **Create and Push Release Tag:**
   ```bash
   # Create annotated tag with release notes
   git tag -a v1.0.1 -m "Release v1.0.1

   - Implemented auto-download functionality for Electron desktop app
   - Updated documentation and installation guides  
   - Enhanced user experience with automatic app management
   - Cross-platform support with smart caching
   - Fallback to bundled app for development mode"

   # Push everything
   git push origin main
   git push origin v1.0.1
   ```

4. **Monitor the Build:**
   - Go to: `https://github.com/YOUR_USERNAME/ios-bridge/actions`
   - Watch the "Build and Release iOS Bridge CLI" workflow
   - Should complete in ~15-20 minutes

#### What Gets Created Automatically

**GitHub Release Assets:**
- `ios-bridge-desktop-mac-arm64.zip` (for auto-download)
- `ios-bridge-desktop-mac-x64.zip` (for auto-download)
- `ios-bridge-desktop-windows-x64.zip` (for auto-download)
- `ios-bridge-desktop-linux-x64.zip` (for auto-download)
- `ios_bridge_cli-1.0.1-py3-none-any.whl` (Python package)
- `ios_bridge_cli-1.0.1.tar.gz` (Python source)
- `checksums.txt` (verification)

**PyPI Publication:**
- Package automatically published to https://pypi.org/project/ios-bridge-cli/

#### Alternative: Manual Trigger

If you need to trigger without creating a tag:

1. Go to: `https://github.com/YOUR_USERNAME/ios-bridge/actions`
2. Select: "Build and Release iOS Bridge CLI"
3. Click: "Run workflow"
4. Enter version: `v1.0.1`
5. Click: "Run workflow"

#### Troubleshooting CI/CD

**Build fails:**
```bash
# Check the Actions logs on GitHub
# Common issues:
# - Missing PYPI_API_TOKEN secret
# - Node.js build errors (check electron_app/package.json)
# - Python build errors (check pyproject.toml)
```

**PyPI upload fails:**
```bash
# Check if version already exists on PyPI
# Increment version and try again
sed -i '' 's/version = "1.0.1"/version = "1.0.2"/' pyproject.toml
```

---

### 🔧 Method 2: Manual Release

For developers who prefer manual control or need to debug the build process.

#### Step 1: Prepare Environment

```bash
# Ensure you have all build tools
pip install build twine
npm install -g electron-builder

# Verify tools
python -m build --help
twine --help
electron-builder --help
```

#### Step 2: Build Python Package

```bash
cd ios-bridge-cli

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build Python packages
python -m build

# Verify packages
twine check dist/*

# Test install locally
pip install dist/*.whl --force-reinstall
ios-bridge --version
```

#### Step 3: Build Electron Apps

```bash
cd ios_bridge_cli/electron_app

# Install dependencies
npm install

# Build for all platforms
npm run build-mac     # macOS (creates DMG + ZIP)
npm run build-win     # Windows (creates NSIS + Portable)  
npm run build-linux   # Linux (creates AppImage + DEB + RPM)

# Verify builds
ls -la dist/
```

#### Step 4: Package for Auto-Download

```bash
cd dist

# Create ZIP files with exact names expected by CLI
zip -r ios-bridge-desktop-mac-arm64.zip "mac-arm64/iOS Bridge.app"
zip -r ios-bridge-desktop-mac-x64.zip "mac-x64/iOS Bridge.app"
zip -r ios-bridge-desktop-windows-x64.zip "win-unpacked"
zip -r ios-bridge-desktop-linux-x64.zip "linux-unpacked"

# Move to release directory
mkdir -p ../../../dist/release/
mv ios-bridge-desktop-*.zip ../../../dist/release/

# Generate checksums
cd ../../../dist/release/
sha256sum *.zip > desktop-apps-checksums.txt
```

#### Step 5: Test Packages Locally

```bash
# Test Python package
pip install dist/ios_bridge_cli-1.0.1-py3-none-any.whl --force-reinstall
ios-bridge --help

# Test desktop apps (extract and run one)
cd dist/release/
unzip ios-bridge-desktop-mac-arm64.zip
open "mac-arm64/iOS Bridge.app"  # macOS
# Or double-click the .exe/.AppImage on other platforms
```

#### Step 6: Publish to PyPI

```bash
# Upload to TestPyPI first (optional)
twine upload --repository testpypi dist/ios_bridge_cli-1.0.1*

# Test install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ios-bridge-cli

# If everything works, upload to production PyPI
twine upload dist/ios_bridge_cli-1.0.1*
```

#### Step 7: Create GitHub Release

**Option A: Using GitHub CLI**
```bash
# Create release with all assets
gh release create v1.0.1 \
  --title "iOS Bridge CLI v1.0.1" \
  --notes "Release notes here..." \
  dist/ios_bridge_cli-1.0.1-py3-none-any.whl \
  dist/ios_bridge_cli-1.0.1.tar.gz \
  dist/release/ios-bridge-desktop-mac-arm64.zip \
  dist/release/ios-bridge-desktop-mac-x64.zip \
  dist/release/ios-bridge-desktop-windows-x64.zip \
  dist/release/ios-bridge-desktop-linux-x64.zip \
  dist/release/desktop-apps-checksums.txt
```

**Option B: Using GitHub Web UI**
1. Go to: `https://github.com/YOUR_USERNAME/ios-bridge/releases`
2. Click: "Create a new release"
3. Tag version: `v1.0.1`
4. Release title: `iOS Bridge CLI v1.0.1`
5. Upload all files from `dist/` and `dist/release/`
6. Write release notes
7. Click: "Publish release"

#### Step 8: Verify Release

```bash
# Test auto-download functionality
cd /tmp
mkdir test-release
cd test-release

# Create fresh environment
python -m venv test-env
source test-env/bin/activate

# Install from PyPI
pip install ios-bridge-cli

# Test auto-download (should download from GitHub releases)
ios-bridge desktop --help

# Should show:
# 🔍 iOS Bridge Desktop not found or outdated
# 🏗️ Downloading iOS Bridge Desktop for macOS...
# ✅ iOS Bridge Desktop installed successfully
```

#### Manual Release Checklist

- [ ] Version bumped in `pyproject.toml`
- [ ] Python package builds successfully
- [ ] Electron apps build for all platforms
- [ ] Auto-download ZIP files created with correct names
- [ ] All packages tested locally
- [ ] PyPI upload successful
- [ ] GitHub release created with all assets
- [ ] Auto-download functionality verified
- [ ] Documentation updated

---

## Release Comparison

| Feature | Automated CI/CD | Manual Release |
|---------|----------------|----------------|
| **Time Required** | 2 minutes setup | 30-60 minutes |
| **Complexity** | Very Low | High |
| **Error-Prone** | Low | High |
| **Cross-Platform** | All platforms | Depends on your OS |
| **Consistency** | Perfect | Manual variations |
| **Best For** | Production releases | Debugging, learning |

**Recommendation:** Use **Automated CI/CD** for all production releases. Use **Manual Release** only for:
- Learning the build process
- Debugging build issues  
- One-off custom builds
- When CI/CD is unavailable

---

## Distribution Platforms

### 1. Package Managers

**Homebrew (macOS/Linux)**
```bash
# Create homebrew formula
# Submit PR to homebrew-core or create tap
brew tap AutoFlowLabs/ios-bridge
brew install ios-bridge-cli
```

**Chocolatey (Windows)**
```powershell
# Create chocolatey package
# Submit to community repository
choco install ios-bridge-cli
```

**Snap (Linux)**
```bash
# Create snapcraft.yaml
# Publish to Snap Store
snap install ios-bridge-cli
```

**winget (Windows)**
```yaml
# Create winget manifest
# Submit to winget-pkgs repository
winget install ios-bridge-cli
```

### 2. Container Images

**Docker Hub**
```dockerfile
# Dockerfile for server
FROM python:3.11-slim
RUN pip install ios-bridge-cli
EXPOSE 8000
CMD ["ios-bridge", "start-server"]
```

**GitHub Container Registry**
```bash
# Build and push
docker build -t ghcr.io/AutoFlowLabs/ios-bridge:latest .
docker push ghcr.io/AutoFlowLabs/ios-bridge:latest
```

### 3. Cloud Marketplaces

- **AWS Marketplace**: Container or AMI
- **Google Cloud Marketplace**: Container or VM image  
- **Azure Marketplace**: Container or VM image
- **DigitalOcean Marketplace**: Droplet image

---

## Marketing and Promotion

### 1. Developer Communities

**Reddit**
- r/iOSProgramming
- r/MachineLearning (if applicable)
- r/Python
- r/javascript
- r/SideProject

**Hacker News**
- Submit with compelling title
- Best times: Tuesday-Thursday, 8-10 AM EST
- Include "Show HN:" prefix

**Product Hunt**
- Schedule launch day
- Prepare assets (logo, screenshots, GIF)
- Rally early supporters

### 2. Technical Blogs

**Platform Blogs**
- Dev.to
- Medium
- Hashnode
- Personal blog

**Guest Posts**
- iOS development blogs
- Testing/automation blogs
- Developer tool roundups

**Content Ideas**
- "Building a Cross-Platform iOS Simulator Client"
- "WebRTC vs WebSocket for Real-Time Streaming"
- "Packaging Python CLI Tools with Electron Integration"

### 3. Social Media

**Twitter/X**
- Developer community hashtags: #iOSDev #Python #Electron
- Tag relevant accounts and tools
- Share screenshots/demos

**LinkedIn**
- Professional developer content
- Company pages and groups

**YouTube**
- Demo videos
- Tutorial content
- Feature walkthroughs

### 4. Documentation Sites

**Awesome Lists**
- awesome-ios
- awesome-python
- awesome-electron

**Tool Directories**
- awesome-selfhosted
- iOS development tool lists
- Testing tool directories

---

## Post-Release Tasks

### 1. Monitor and Support

```bash
# Monitor PyPI downloads
pip install pypistats
pypistats recent ios-bridge-cli

# Monitor GitHub
# - Stars, forks, issues
# - Download statistics
# - User feedback
```

### 2. Community Building

- **Discord/Slack**: Create community server
- **GitHub Discussions**: Enable and moderate
- **Documentation Wiki**: Keep updated
- **Issue Triage**: Respond promptly to issues

### 3. Continuous Improvement

**Collect Feedback**
- User surveys
- GitHub issues
- Community discussions
- Usage analytics

**Plan Updates**
- Bug fixes (patch releases)
- New features (minor releases)
- Breaking changes (major releases)

**Release Schedule**
- Regular release cycle (monthly/quarterly)
- Security updates (as needed)
- LTS versions (yearly)

### 4. Legal and Compliance

- **License compliance**: Review dependencies
- **Export compliance**: If applicable
- **Privacy policy**: If collecting data
- **Terms of service**: For hosted services

---

## Automation Scripts

### 1. Release Preparation Script

```bash
#!/bin/bash
# prepare_release.sh

set -e

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "🚀 Preparing release $VERSION"

# Update version in files
sed -i "" "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
sed -i "" "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" ios_bridge_cli/electron_app/package.json

# Run tests
python -m pytest tests/ -v

# Build and test
python -m build
twine check dist/*

# Create git tag
git add .
git commit -m "Bump version to $VERSION"
git tag -a "v$VERSION" -m "Release v$VERSION"

echo "✅ Release $VERSION prepared"
echo "Next steps:"
echo "1. git push origin main"
echo "2. git push origin v$VERSION"
echo "3. Monitor GitHub Actions"
```

### 2. Post-Release Verification Script

```bash
#!/bin/bash
# verify_release.sh

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "🔍 Verifying release $VERSION"

# Check PyPI
echo "Checking PyPI..."
pip index versions ios-bridge-cli | grep $VERSION

# Check GitHub release
echo "Checking GitHub release..."
gh release view v$VERSION

# Test installation
echo "Testing installation..."
pip install --upgrade ios-bridge-cli==$VERSION
ios-bridge --version

echo "✅ Release $VERSION verified"
```

---

## Troubleshooting Common Issues

### PyPI Upload Issues

```bash
# Invalid package
twine check dist/*

# Authentication issues
twine upload --verbose dist/*

# File already exists
# Delete from PyPI or increment version
```

### GitHub Actions Issues

```bash
# Check workflow logs
gh run list
gh run view <run-id>

# Re-run failed jobs
gh run rerun <run-id>
```

### Build Issues

```bash
# Clean environment
rm -rf build/ dist/ *.egg-info/
pip install --upgrade build wheel twine

# Check dependencies
pip-tools compile --upgrade requirements.in
```

---

## Success Metrics

Track these metrics to measure success:

- **Downloads**: PyPI downloads, GitHub release downloads
- **Stars/Forks**: GitHub repository metrics
- **Issues**: Quality and response time
- **Community**: Discord/discussions activity
- **Adoption**: Integration in other projects
- **Press**: Blog mentions, tool lists inclusion

---

## Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [Electron Builder Documentation](https://www.electron.build/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyPI Help](https://pypi.org/help/)
- [Semantic Versioning](https://semver.org/)

Happy publishing! 🚀