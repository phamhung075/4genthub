# Python 3.14.0 Installation Guide for Ubuntu 24.04 WSL2

## Overview
This guide documents the process for installing Python 3.14.0 from source on Ubuntu 24.04 WSL2 and configuring it as the default Python 3 version.

## Current System Information
- **OS**: Ubuntu 24.04.1 LTS (Noble Numbat) on WSL2
- **Kernel**: 6.6.87.2-microsoft-standard-WSL2
- **Original Python**: 3.12.3 at /usr/bin/python3
- **Architecture**: x86_64
- **Target Python**: 3.14.0

## Why Build from Source?
Python 3.14.0 is too new for Ubuntu 24.04 repositories (released October 2024). Building from source ensures:
- Latest Python features and performance improvements
- Optimizations enabled during compilation
- Clean installation without conflicts
- Full control over installation location

## Installation Methods

### Method 1: Automated Script (Recommended)
The installation script is located at: `/home/daihungpham/__projects__/4genthub/scripts/install-python-3.14.sh`

**To run:**
```bash
cd /home/daihungpham/__projects__/4genthub
./scripts/install-python-3.14.sh
```

**What the script does:**
1. Installs all required build dependencies
2. Downloads and extracts Python 3.14.0 source
3. Configures build with optimizations enabled
4. Compiles Python using all available CPU cores
5. Installs Python 3.14 using `altinstall` (safe method)
6. Updates system alternatives to make python3.14 the default
7. Upgrades pip, setuptools, and wheel
8. Offers to recreate project virtual environment

**Estimated time:** 15-20 minutes (mostly compilation)

### Method 2: Manual Installation

#### Step 1: Install Build Dependencies
```bash
sudo apt update
sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
    libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget \
    libbz2-dev liblzma-dev tk-dev libgdbm-compat-dev uuid-dev
```

**Required packages explained:**
- `build-essential`: GCC, make, and core build tools
- `zlib1g-dev`: Compression library for gzip support
- `libssl-dev`: SSL/TLS support for HTTPS
- `libffi-dev`: Foreign Function Interface for C extensions
- `libsqlite3-dev`: SQLite database support
- `libreadline-dev`: Interactive shell enhancements
- `libbz2-dev`, `liblzma-dev`: Additional compression support
- `tk-dev`: Tkinter GUI library support

#### Step 2: Download Python 3.14.0 Source
```bash
cd /tmp
wget https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tgz
tar -xf Python-3.14.0.tgz
cd Python-3.14.0
```

**Verify download integrity (optional but recommended):**
```bash
# Download checksum file
wget https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tgz.asc
# Verify signature (requires GPG keys)
gpg --verify Python-3.14.0.tgz.asc Python-3.14.0.tgz
```

#### Step 3: Configure Build with Optimizations
```bash
./configure --enable-optimizations --prefix=/usr/local
```

**Configuration flags explained:**
- `--enable-optimizations`: Enables Profile Guided Optimization (PGO) for ~10-20% performance improvement
  - Note: This makes compilation take longer but results in faster Python
- `--prefix=/usr/local`: Installs to /usr/local instead of /usr (standard for locally compiled software)

**Additional optional flags:**
- `--with-lto`: Enable Link Time Optimization (further performance boost)
- `--enable-shared`: Build shared Python library (needed for some C extensions)

#### Step 4: Build Python
```bash
make -j $(nproc)
```

**Build process:**
- Uses all available CPU cores: `$(nproc)` returns number of cores
- With `--enable-optimizations`, this runs the test suite for profiling
- Typical build time: 10-15 minutes on modern hardware

**Monitor build progress:**
```bash
# Check CPU usage
htop

# Check build logs
tail -f /tmp/Python-3.14.0/build.log
```

#### Step 5: Install Python 3.14
```bash
sudo make altinstall
```

**Important: Why `altinstall` instead of `install`?**
- `make install`: Overwrites `/usr/bin/python3` (can break system tools)
- `make altinstall`: Installs as `/usr/local/bin/python3.14` (safe)
- Preserves system Python while adding new version

**Installation locations:**
- Binary: `/usr/local/bin/python3.14`
- Libraries: `/usr/local/lib/python3.14/`
- Include files: `/usr/local/include/python3.14/`

#### Step 6: Configure Python 3.14 as Default
```bash
# Add python3.14 as an alternative for python3
sudo update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.14 1

# Verify alternatives are registered
sudo update-alternatives --display python3

# Set python3.14 as the selected alternative
sudo update-alternatives --set python3 /usr/local/bin/python3.14
```

**Alternative: Interactive selection**
```bash
sudo update-alternatives --config python3
# Select python3.14 from the menu by number
```

**How alternatives work:**
- Creates symlink: `/usr/bin/python3` → `/etc/alternatives/python3` → `/usr/local/bin/python3.14`
- Allows easy switching between Python versions
- Priority system (higher number = preferred default)

#### Step 7: Verify Installation
```bash
# Check default python3 version
python3 --version
# Expected: Python 3.14.0

# Check python3.14 directly
python3.14 --version
# Expected: Python 3.14.0

# Verify symlink chain
which python3
ls -la /usr/bin/python3
ls -la /etc/alternatives/python3

# Test Python functionality
python3 -c "import sys; print(sys.version)"
python3 -c "import ssl; print(ssl.OPENSSL_VERSION)"
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
```

#### Step 8: Update pip and Core Tools
```bash
# Ensure pip is installed
python3.14 -m ensurepip --upgrade

# Upgrade pip, setuptools, and wheel
python3.14 -m pip install --upgrade pip setuptools wheel

# Verify pip installation
python3 -m pip --version
```

#### Step 9: Recreate Project Virtual Environment
```bash
cd /home/daihungpham/__projects__/4genthub/agenthub_main

# Remove old virtual environment
rm -rf .venv

# Create new virtual environment with Python 3.14
python3.14 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip in virtual environment
pip install --upgrade pip

# Install project in editable mode
pip install -e .

# Verify virtual environment Python version
python --version
which python
```

## Post-Installation Tasks

### Update Docker Configuration
If using Docker, ensure Dockerfile uses Python 3.14:
```dockerfile
FROM python:3.14-slim
```

### Update pyproject.toml
Ensure project specifies Python 3.14 compatibility:
```toml
[project]
requires-python = ">=3.14"
```

### Verify System Integration
```bash
# Check Python can access all modules
python3 -c "import zlib, ssl, sqlite3, bz2, lzma, readline"

# Check pip works
python3 -m pip list

# Test virtual environment creation
python3 -m venv /tmp/test-venv
source /tmp/test-venv/bin/activate
python --version
deactivate
rm -rf /tmp/test-venv
```

## Troubleshooting

### Issue: SSL/TLS Errors
**Symptom:** `pip install` fails with SSL certificate errors
**Solution:**
```bash
# Reinstall with OpenSSL support
cd /tmp/Python-3.14.0
./configure --enable-optimizations --prefix=/usr/local --with-openssl=/usr
make -j $(nproc)
sudo make altinstall
```

### Issue: Missing Modules (zlib, sqlite3, etc.)
**Symptom:** `ImportError: No module named 'zlib'`
**Solution:**
1. Install missing development packages
2. Rebuild Python from source
```bash
# Install missing dependencies
sudo apt install -y zlib1g-dev libsqlite3-dev libbz2-dev

# Rebuild
cd /tmp/Python-3.14.0
make clean
./configure --enable-optimizations --prefix=/usr/local
make -j $(nproc)
sudo make altinstall
```

### Issue: System Python Still Default
**Symptom:** `python3 --version` shows old version
**Solution:**
```bash
# Check alternatives configuration
sudo update-alternatives --display python3

# Manually set python3.14 as default
sudo update-alternatives --set python3 /usr/local/bin/python3.14

# Verify
python3 --version
```

### Issue: Virtual Environment Creation Fails
**Symptom:** `python3 -m venv .venv` fails
**Solution:**
```bash
# Ensure ensurepip is available
python3.14 -m ensurepip --upgrade

# Try creating venv again
python3.14 -m venv .venv

# If still failing, install venv package
sudo apt install python3.14-venv
```

### Issue: Build Takes Too Long
**Symptom:** Compilation running for over 30 minutes
**Solution:**
```bash
# Disable optimizations for faster build
./configure --prefix=/usr/local
make -j $(nproc)
sudo make altinstall

# Note: This produces slower Python but faster compilation
```

## Performance Considerations

### Build Optimizations Impact
- **Without optimizations:** ~5 minutes build, baseline performance
- **With --enable-optimizations:** ~15 minutes build, 10-20% faster execution
- **With --enable-optimizations --with-lto:** ~20 minutes build, 15-25% faster execution

### Recommended for Production
```bash
./configure \
    --enable-optimizations \
    --with-lto \
    --enable-shared \
    --prefix=/usr/local
```

## Cleanup

After successful installation, remove source files:
```bash
rm -rf /tmp/Python-3.14.0
rm /tmp/Python-3.14.0.tgz
```

## Rollback Procedure

To revert to system Python 3.12:
```bash
# Switch python3 alternative back to 3.12
sudo update-alternatives --set python3 /usr/bin/python3.12

# Verify
python3 --version

# Optional: Remove Python 3.14
sudo rm -rf /usr/local/bin/python3.14
sudo rm -rf /usr/local/lib/python3.14
```

## Security Considerations

### Verify Python Source Authenticity
Always verify downloaded Python source:
```bash
# Import Python release signing keys
gpg --recv-keys 0D96DF4D4110E5C43FBFB17F2D347EA6AA65421D

# Verify signature
gpg --verify Python-3.14.0.tgz.asc Python-3.14.0.tgz
```

### Keep Python Updated
Python 3.14 will receive security updates:
```bash
# Check for updates
curl -s https://www.python.org/downloads/ | grep "3.14"

# When 3.14.1 is released, repeat installation process
```

## References
- [Python 3.14 Release Notes](https://docs.python.org/3.14/whatsnew/3.14.html)
- [Python Build Instructions](https://devguide.python.org/getting-started/setup-building/)
- [Ubuntu Python Packaging](https://wiki.ubuntu.com/Python)

## Version History
- **2025-10-15**: Initial documentation for Python 3.14.0 installation on Ubuntu 24.04 WSL2
