# Version Management Scripts

Scripts to automatically bump version numbers across all iOS Bridge CLI files.

## Quick Usage

### Python Script (Recommended)
```bash
# Show current version
python3 bump_version.py --current

# Dry run (see what would change)
python3 bump_version.py --dry-run 1.0.2

# Bump to specific version
python3 bump_version.py 1.0.2
```

### Shell Script (Simple)
```bash
# Bump to specific version
./bump_version.sh 1.0.2
```

## What Gets Updated

Both scripts update version numbers in:

1. **`ios-bridge-cli/pyproject.toml`** - Python package version
2. **`ios-bridge-cli/ios_bridge_cli/electron_app/package.json`** - Electron app version  
3. **`.github/workflows/build-and-release.yml`** - GitHub workflow default version
4. **`ios-bridge-cli/ios_bridge_cli/__init__.py`** - Python package `__version__`

## Complete Release Workflow

```bash
# 1. Bump version
python3 bump_version.py 1.0.2

# 2. Commit changes
git add .
git commit -m "Bump version to 1.0.2"
git push origin main

# 3. Create and push release tag
git tag -a v1.0.2 -m "Release v1.0.2"
git push origin v1.0.2

# 4. GitHub Actions will automatically:
#    - Build Python package
#    - Build Electron apps for all platforms
#    - Create GitHub release with assets
#    - Publish to PyPI
```

## Supported Version Formats

- **Standard**: `1.0.2`, `2.1.0`, `0.1.0`
- **Pre-release**: `1.0.0-alpha.1`, `2.0.0-beta.2`, `1.5.0-rc.1`

## Script Features

### Python Script (`bump_version.py`)
- ✅ Validates version format
- ✅ Shows current version
- ✅ Dry run mode
- ✅ Detailed progress output
- ✅ Error handling and validation
- ✅ Cross-platform compatibility

### Shell Script (`bump_version.sh`)  
- ✅ Fast and simple
- ✅ Basic version validation
- ✅ macOS compatible (uses `sed -i ''`)

## Examples

### Patch Release (Bug Fixes)
```bash
python3 bump_version.py 1.0.1  # 1.0.0 → 1.0.1
```

### Minor Release (New Features)
```bash
python3 bump_version.py 1.1.0  # 1.0.x → 1.1.0
```

### Major Release (Breaking Changes)
```bash
python3 bump_version.py 2.0.0  # 1.x.x → 2.0.0
```

### Pre-release
```bash
python3 bump_version.py 1.1.0-beta.1  # Testing version
```

## Troubleshooting

**Permission denied:**
```bash
chmod +x bump_version.py
chmod +x bump_version.sh
```

**Invalid version format:**
- Use semantic versioning: `MAJOR.MINOR.PATCH`
- Optional suffix: `-alpha.1`, `-beta.2`, `-rc.1`

**File not found errors:**
- Run from the root directory of the ios-bridge repository
- Ensure all files exist in expected locations

## Integration with CI/CD

The scripts automatically update the GitHub Actions workflow default version, ensuring:
- Manual workflow triggers use the correct version
- All releases are properly tagged and versioned
- PyPI and GitHub releases stay synchronized

## Version Strategy

**Recommended versioning:**
- **Patch** (1.0.1): Bug fixes, documentation updates
- **Minor** (1.1.0): New features, UI improvements, non-breaking changes
- **Major** (2.0.0): Breaking changes, major architecture updates

**Pre-release suffixes:**
- **alpha**: Early development, API may change
- **beta**: Feature complete, testing phase
- **rc**: Release candidate, final testing