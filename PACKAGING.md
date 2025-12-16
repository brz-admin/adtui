# ADTUI Packaging & Distribution Guide

## 📦 Package Structure

```
adtui/
├── adtui.py                 # Main application
├── constants.py             # Constants & enums
├── adtree.py               # Tree widget
├── styles.tcss             # UI styles
├── services/               # Business logic
│   ├── __init__.py
│   ├── ldap_service.py
│   ├── history_service.py
│   └── path_service.py
├── commands/               # Command handling
│   ├── __init__.py
│   └── command_handler.py
├── ui/                     # UI components
│   ├── __init__.py
│   └── dialogs.py
├── widgets/                # Custom widgets
│   ├── __init__.py
│   ├── details_pane.py
│   ├── user_details.py
│   └── group_details.py
├── setup.py               # Setup script
├── pyproject.toml         # Modern Python packaging
├── requirements.txt       # Dependencies
├── MANIFEST.in           # Package data
├── README.md             # Documentation
├── LICENSE               # MIT License
└── config.ini.example    # Config template
```

## 🚀 Distribution Methods

### Method 1: PyPI (Recommended for Public Distribution)

#### 1. Build the Package

```bash
# Install build tools
pip install build twine

# Build distributions
python -m build

# This creates:
# - dist/adtui-2.0.0-py3-none-any.whl
# - dist/adtui-2.0.0.tar.gz
```

#### 2. Test Upload (TestPyPI)

```bash
# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ adtui
```

#### 3. Production Upload

```bash
# Upload to PyPI
twine upload dist/*

# Users can now install with:
pip install adtui
```

### Method 2: GitHub Releases (Recommended for Private/Internal)

#### 1. Create GitHub Repository

```bash
git init
git add .
git commit -m "Initial commit - ADTUI v2.0.0"
git remote add origin https://git.brznet.fr/brz/adtui.git
git push -u origin main
```

#### 2. Create Release

```bash
# Tag the release
git tag -a v2.0.0 -m "Version 2.0.0 - Complete refactoring"
git push origin v2.0.0

# Create release on GitHub and upload:
# - dist/adtui-2.0.0-py3-none-any.whl
# - dist/adtui-2.0.0.tar.gz
```

#### 3. Users Install From GitHub

```bash
# Direct from GitHub
pip install git+https://github.com/yourusername/adtui.git

# Or from specific release
pip install https://github.com/yourusername/adtui/releases/download/v2.0.0/adtui-2.0.0-py3-none-any.whl
```

### Method 3: Standalone Executable (PyInstaller)

#### 1. Install PyInstaller

```bash
pip install pyinstaller
```

#### 2. Create Executable

```bash
# Create single file executable
pyinstaller --onefile \
            --name adtui \
            --add-data "styles.tcss:." \
            --add-data "config.ini.example:." \
            --hidden-import ldap3 \
            --hidden-import textual \
            adtui.py

# Creates: dist/adtui (or adtui.exe on Windows)
```

#### 3. Distribute

```bash
# Zip the executable with config template
cd dist
zip adtui-2.0.0-standalone.zip adtui config.ini.example

# Users can extract and run:
./adtui
```

### Method 4: Docker Container

#### 1. Create Dockerfile

```dockerfile
# Create: Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install -e .

CMD ["adtui"]
```

#### 2. Build and Share

```bash
# Build image
docker build -t adtui:2.0.0 .

# Tag for registry
docker tag adtui:2.0.0 yourregistry/adtui:2.0.0

# Push to registry
docker push yourregistry/adtui:2.0.0

# Users run with:
docker run -it --rm adtui:2.0.0
```

### Method 5: Internal Network Share

#### Simple Distribution

```bash
# Create distribution package
python -m build

# Copy to network share
cp dist/adtui-2.0.0-py3-none-any.whl \\server\share\

# Users install from network
pip install \\server\share\adtui-2.0.0-py3-none-any.whl
```

## 📋 Pre-Distribution Checklist

### Before Building

- [ ] Update version in `setup.py` and `pyproject.toml`
- [ ] Update `README.md` with latest features
- [ ] Update `CHANGELOG.md` with changes
- [ ] Remove hardcoded credentials (already done!)
- [ ] Remove /test code
- [ ] Update config.ini.example
- [ ] Test on clean environment

### Code Quality

```bash
# Run tests
pytest tests/

# Check types
mypy adtui/

# Format code
black adtui/

# Lint
pylint adtui/
```

### Testing Distribution

```bash
# Test in virtual environment
python -m venv test_env
source test_env/bin/activate  # or test_env\Scripts\activate on Windows
pip install dist/adtui-2.0.0-py3-none-any.whl
adtui  # Test it works
deactivate
```

## 📝 Version Management

### Semantic Versioning

```
MAJOR.MINOR.PATCH

2.0.0 - Complete refactoring (breaking changes)
2.1.0 - New features (backwards compatible)
2.1.1 - Bug fixes (backwards compatible)
```

### Update Versions In:

1. `setup.py` - version="2.0.0"
2. `pyproject.toml` - version = "2.0.0"
3. `README.md` - ## Changelog section
4. Git tag - `git tag v2.0.0`

## 🔐 Security Notes

### Before Sharing

- ✅ No hardcoded credentials (fixed!)
- ✅ No sensitive data in config
- ✅ .gitignore includes config.ini and last_user.txt
- ✅ Only config.ini.example is distributed

### For Users

```bash
# After installation, users need to:
1. Copy config.ini.example to config.ini
2. Edit config.ini with their AD details
3. Run adtui
```

## 📊 Distribution Size

Approximate sizes:

- Wheel (.whl): ~50 KB
- Source (.tar.gz): ~70 KB
- PyInstaller executable: ~15 MB (includes Python runtime)
- Docker image: ~150 MB

## 🌐 Publishing to PyPI

### One-Time Setup

```bash
# Create PyPI account at https://pypi.org

# Create ~/.pypirc
[pypi]
username = __token__
password = pypi-your-token-here

[testpypi]
username = __token__
password = pypi-your-test-token-here
```

### Publish Process

```bash
# 1. Clean previous builds
rm -rf dist/ build/ *.egg-info

# 2. Build
python -m build

# 3. Check
twine check dist/*

# 4. Upload to TestPyPI
twine upload --repository testpypi dist/*

# 5. Test install
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ adtui

# 6. If OK, upload to PyPI
twine upload dist/*
```

## 🎯 Distribution Recommendations

### For Public Open Source

✅ **PyPI** + **GitHub Releases**

- Easy installation: `pip install adtui`
- Source code available
- Community can contribute

### For Internal Corporate Use

✅ **GitHub Enterprise** or **GitLab** + **Wheel Files**

- Private repository
- Install from: `pip install adtui-2.0.0-py3-none-any.whl`
- Or: `pip install git+https://your-gitlab.com/company/adtui.git`

### For End Users (Non-Technical)

✅ **PyInstaller Executable**

- Single file, no Python required
- Include config template
- Create simple installer

### For Server Deployment

✅ **Docker Container**

- Consistent environment
- Easy updates
- Isolated dependencies

## 📚 User Installation Instructions

### PyPI Method

```bash
# Install
pip install adtui

# Setup config
adtui --init  # If we add this feature
# Or manually copy config

# Run
adtui
```

### Wheel File Method

```bash
# Install
pip install adtui-2.0.0-py3-none-any.whl

# Setup and run same as above
```

### Executable Method

```bash
# Extract
unzip adtui-2.0.0-standalone.zip
cd adtui

# Setup config
cp config.ini.example config.ini
# Edit config.ini

# Run
./adtui  # or adtui.exe on Windows
```

## 🆘 Common Issues

### Import Errors

- Ensure all dependencies in requirements.txt
- Check `__init__.py` files exist in all packages

### Missing Files

- Check MANIFEST.in includes all needed files
- Use `python -m build --sdist` and inspect contents

### Version Conflicts

- Pin major versions in requirements.txt
- Test in clean environment

## ✅ Ready to Package!

Your project is now ready for distribution with:

- ✅ setup.py and pyproject.toml
- ✅ requirements.txt
- ✅ MANIFEST.in for package data
- ✅ README.md with usage instructions
- ✅ LICENSE file (MIT)
- ✅ .gitignore for safety
- ✅ config.ini.example (no secrets)
- ✅ Entry point configured (adtui command)
- ✅ Clean architecture
- ✅ Type hints
- ✅ Documentation

**Next steps:**

1. Choose your distribution method
2. Follow the appropriate guide above
3. Share with users!

**Quick start for testing:**

```bash
python -m build
pip install dist/adtui-2.0.0-py3-none-any.whl
adtui
```
