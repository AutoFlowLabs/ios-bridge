# iOS Bridge CLI Publishing Checklist - Step by Step

This is your exact roadmap to publish both the CLI and Electron app from your current state.

## 🔍 Current Status Check

First, let's verify what we have:

```bash
# Verify your project structure
cd /Users/himanshukukreja/autoflow/ios-bridge
ls -la

# Check if CLI works locally
cd ios-bridge-cli
python -m ios_bridge_cli.cli --help

# Check if Electron app builds
cd ios_bridge_cli/electron_app
npm run start  # Test locally first
```

---

## 📋 Step-by-Step Publishing Process

### **Phase 1: Pre-Publishing Setup (5-10 minutes)**

#### ✅ Step 1: Update Project Metadata

1. **Edit repository URLs in configuration files:**

```bash
# Update pyproject.toml
cd /Users/himanshukukreja/autoflow/ios-bridge/ios-bridge-cli
```

Replace these in `pyproject.toml`:
- `"Homepage" = "https://github.com/AutoFlowLabs/ios-bridge-cli"`
- `"Bug Tracker" = "https://github.com/AutoFlowLabs/ios-bridge-cli/issues"`

With your actual GitHub repository URL.

2. **Set your version number:**
```bash
# Check current version
grep 'version = ' pyproject.toml

# Set to 1.0.0 if not already
sed -i '' 's/version = ".*"/version = "1.0.0"/' pyproject.toml
```

#### ✅ Step 2: Create GitHub Repository (if not exists)

```bash
# If you haven't pushed to GitHub yet:
cd /Users/himanshukukreja/autoflow/ios-bridge
git init
git add .
git commit -m "Initial iOS Bridge CLI release"

# Create repository on GitHub (use gh CLI or web interface)
gh repo create ios-bridge --public --source=. --push
# OR manually create on github.com and push
```

#### ✅ Step 3: Set Up PyPI Account

1. **Create PyPI account:** Go to https://pypi.org/account/register/
2. **Create TestPyPI account:** Go to https://test.pypi.org/account/register/
3. **Generate API tokens:**
   - PyPI: Account Settings → API tokens → "Add API token"
   - TestPyPI: Same process on test.pypi.org
   - Store tokens securely (you'll need them)

#### ✅ Step 4: Configure GitHub Secrets

Add these secrets to your GitHub repository:
1. Go to your repo → Settings → Secrets and variables → Actions
2. Add these secrets:
   - `PYPI_API_TOKEN`: Your PyPI API token
   - `TEST_PYPI_API_TOKEN`: Your TestPyPI API token (optional)

---

### **Phase 2: First Test Build (10-15 minutes)**

#### ✅ Step 5: Test Python Package Build

```bash
cd /Users/himanshukukreja/autoflow/ios-bridge/ios-bridge-cli

# Install build dependencies
pip install build twine

# Clean any previous builds
rm -rf build/ dist/ *.egg-info/

# Build the package
python -m build

# Check the built package
twine check dist/*

# Test install locally
pip install dist/*.whl
ios-bridge --help
```

#### ✅ Step 6: Test Electron App Build

```bash
cd ios_bridge_cli/electron_app

# Install dependencies (if not done)
npm install

# Test development mode
npm run start

# Test build for your platform
npm run build-mac  # or build-win/build-linux
```

#### ✅ Step 7: Test Upload to TestPyPI

```bash
# Configure credentials (one-time setup)
cat > ~/.pypirc << EOF
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = YOUR_PYPI_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = YOUR_TESTPYPI_TOKEN_HERE
EOF

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ ios-bridge-cli
```

---

### **Phase 3: Production Publishing (5-10 minutes)**

#### ✅ Step 8: Create Release Tag

```bash
cd /Users/himanshukukreja/autoflow/ios-bridge

# Commit any final changes
git add .
git commit -m "Prepare for v1.0.0 release"

# Create and push release tag
git tag -a v1.0.0 -m "iOS Bridge CLI v1.0.0 - Initial Release"
git push origin main
git push origin v1.0.0
```

#### ✅ Step 9: Monitor GitHub Actions

1. **Go to your GitHub repository**
2. **Click "Actions" tab**
3. **Watch the build process** (triggered by the tag push)
4. **Verify all platforms build successfully**

The workflow will automatically:
- Build Python package
- Build Electron apps for macOS, Windows, Linux
- Create GitHub release
- Upload to PyPI

#### ✅ Step 10: Verify Publication

```bash
# Check PyPI publication
pip install ios-bridge-cli
ios-bridge --version

# Check GitHub release
gh release view v1.0.0
# OR visit: https://github.com/your-username/ios-bridge/releases
```

---

### **Phase 4: Electron Desktop App Release (15-20 minutes)**

Now that the CLI is published, let's build and release the Electron desktop apps for auto-download functionality.

#### ✅ Step 11: Build Cross-Platform Electron Apps

```bash
cd /Users/himanshukukreja/autoflow/ios-bridge/ios-bridge-cli/ios_bridge_cli/electron_app

# Install dependencies (if not already done)
npm install

# Build for all platforms
npm run build-mac     # Creates macOS DMG + ZIP
npm run build-win     # Creates Windows NSIS + Portable
npm run build-linux   # Creates Linux AppImage + DEB + RPM

# Check what was built
ls -la dist/
```

#### ✅ Step 12: Package Electron Apps for GitHub Release

```bash
cd dist

# Package each platform as ZIP with exact names expected by CLI
zip -r ios-bridge-desktop-mac-arm64.zip "mac-arm64/iOS Bridge.app"
zip -r ios-bridge-desktop-mac-x64.zip "mac-x64/iOS Bridge.app"
zip -r ios-bridge-desktop-windows-x64.zip "win-unpacked/iOS Bridge.exe" 
zip -r ios-bridge-desktop-linux-x64.zip "linux-unpacked/ios-bridge-desktop"

# Move to a release directory
mkdir -p ../../../dist/release/
mv ios-bridge-desktop-*.zip ../../../dist/release/

# Generate checksums
cd ../../../dist/release/
sha256sum *.zip > desktop-apps-checksums.txt

# Verify files
ls -la
```

#### ✅ Step 13: Update GitHub Release with Desktop Apps

```bash
# Option 1: GitHub CLI (recommended)
gh release upload v1.0.0 \
  dist/release/ios-bridge-desktop-mac-arm64.zip \
  dist/release/ios-bridge-desktop-mac-x64.zip \
  dist/release/ios-bridge-desktop-windows-x64.zip \
  dist/release/ios-bridge-desktop-linux-x64.zip \
  dist/release/desktop-apps-checksums.txt

# Option 2: Manual upload via GitHub UI
# Visit: https://github.com/your-username/ios-bridge/releases/tag/v1.0.0
# Click "Edit release" and drag the ZIP files to upload
```

#### ✅ Step 14: Update app_manager.py GitHub Repository URL

**IMPORTANT:** Update the repository URL in the auto-download code:

```bash
# Edit the file
cd /Users/himanshukukreja/autoflow/ios-bridge/ios-bridge-cli/ios_bridge_cli
```

In `app_manager.py`, update line 28:
```python
GITHUB_REPO = "your-username/ios-bridge"  # Replace with your actual repo
```

Then republish the CLI with the correct repository URL:
```bash
# Increment version number
cd /Users/himanshukukreja/autoflow/ios-bridge/ios-bridge-cli
sed -i '' 's/version = "1.0.0"/version = "1.0.1"/' pyproject.toml

# Rebuild and upload
python -m build
twine upload dist/ios_bridge_cli-1.0.1*

# Update GitHub release tag
git tag v1.0.1
git push origin v1.0.1
```

#### ✅ Step 15: Test Auto-Download Functionality

```bash
# Test in a fresh environment
cd /tmp
mkdir test-ios-bridge
cd test-ios-bridge

# Create virtual environment
python -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install from PyPI
pip install ios-bridge-cli

# Test auto-download (first time should download desktop app)
ios-bridge desktop --help

# This should show:
# 🔍 iOS Bridge Desktop not found or outdated
# 🏗️ Downloading iOS Bridge Desktop for macOS...
# ████████████████████████████████████████ 25.4MB / 25.4MB
# ✅ iOS Bridge Desktop installed successfully
```

---

### **Phase 5: Post-Publication Tasks (10-15 minutes)**

#### ✅ Step 16: Test Installation on Each Platform

**macOS:**
```bash
# Download from GitHub releases
curl -L https://github.com/your-username/ios-bridge/releases/download/v1.0.0/ios-bridge-cli-macos.tar.gz -o ios-bridge-cli-macos.tar.gz
tar -xzf ios-bridge-cli-macos.tar.gz
cd ios-bridge-cli-macos
chmod +x install.sh
./install.sh
```

**Test the same for Windows and Linux** (or have others test)

#### ✅ Step 17: Update Documentation

```bash
# Update README with actual installation instructions
cd /Users/himanshukukreja/autoflow/ios-bridge

# Edit README.md to include:
# - Actual GitHub repository URL
# - Actual PyPI installation command
# - Links to releases
# - Updated screenshots if needed
```

#### ✅ Step 18: Create Documentation

```bash
# Create a simple website or update README with:
# - Installation instructions
# - Usage examples
# - Screenshots/GIFs of the Electron app
# - API documentation
```

---

## 🚨 **If Something Goes Wrong**

### **GitHub Actions Fails:**
```bash
# Check logs in GitHub Actions tab
# Common fixes:
git commit -m "Fix build issue"
git tag -d v1.0.0  # Delete local tag
git push origin :refs/tags/v1.0.0  # Delete remote tag
git tag -a v1.0.0 -m "iOS Bridge CLI v1.0.0 - Fixed"
git push origin v1.0.0
```

### **PyPI Upload Fails:**
```bash
# Manual upload
cd ios-bridge-cli
python -m build
twine upload dist/*
```

### **Electron Build Fails:**
```bash
cd ios_bridge_cli/electron_app
rm -rf node_modules dist
npm install
npm run build-mac
```

---

## 📊 **Quick Status Check Commands**

Run these anytime to check your publication status:

```bash
# Check if published on PyPI
pip search ios-bridge-cli  # or visit pypi.org/project/ios-bridge-cli

# Check GitHub release
gh release list

# Check downloads
gh release view v1.0.0

# Test installation works
pip install ios-bridge-cli
ios-bridge --version
```

---

## 🎯 **Success Criteria**

You'll know you're successful when:

- ✅ `pip install ios-bridge-cli` works from anywhere
- ✅ `ios-bridge --help` shows your CLI
- ✅ GitHub releases has downloadable installers for all platforms
- ✅ Desktop apps launch and connect to your server
- ✅ Other people can install and use your tool

---

## 🚀 **Next Actions After Publishing**

1. **Announce on social media** (Twitter, Reddit, etc.)
2. **Submit to tool directories** (awesome-ios, etc.)
3. **Write blog post** about the tool
4. **Create demo video** showing the desktop app
5. **Monitor GitHub issues** for user feedback
6. **Plan next release** with user-requested features

---

## 📞 **Need Help?**

If you get stuck at any step:

1. **Check the logs** in GitHub Actions
2. **Run the commands locally** to debug
3. **Check PyPI status** at pypi.org
4. **Verify GitHub releases** are created correctly

Ready to start? Begin with **Phase 1, Step 1** above! 🚀