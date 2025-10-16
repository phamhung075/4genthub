#!/bin/bash
# Python 3.14.0 Installation Script for Ubuntu 24.04 WSL2
# This script installs Python 3.14.0 from source and configures it as the default Python 3

set -e  # Exit on error

echo "=========================================="
echo "Python 3.14.0 Installation Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root. Use your normal user account."
    exit 1
fi

# Check current Python version
print_step "Checking current Python version..."
python3 --version || true
echo ""

# Step 1: Install build dependencies
print_step "Installing build dependencies..."
sudo apt update
sudo apt install -y \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    wget \
    libbz2-dev \
    liblzma-dev \
    tk-dev \
    libgdbm-compat-dev \
    uuid-dev

print_success "Build dependencies installed"
echo ""

# Step 2: Download Python 3.14.0
print_step "Downloading Python 3.14.0 source..."
cd /tmp
if [ -f "Python-3.14.0.tgz" ]; then
    print_info "Python-3.14.0.tgz already exists, skipping download"
else
    wget https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tgz
fi

print_step "Extracting Python 3.14.0..."
if [ -d "Python-3.14.0" ]; then
    print_info "Removing existing Python-3.14.0 directory"
    rm -rf Python-3.14.0
fi
tar -xf Python-3.14.0.tgz
cd Python-3.14.0

print_success "Python 3.14.0 source prepared"
echo ""

# Step 3: Configure and build
print_step "Configuring Python 3.14.0 with optimizations..."
print_info "This may take several minutes..."
./configure --enable-optimizations --prefix=/usr/local

print_step "Building Python 3.14.0..."
print_info "This will use all available CPU cores and may take 10-15 minutes..."
make -j $(nproc)

print_success "Python 3.14.0 built successfully"
echo ""

# Step 4: Install Python 3.14
print_step "Installing Python 3.14.0..."
print_info "Using 'altinstall' to avoid overwriting system python3"
sudo make altinstall

print_success "Python 3.14.0 installed to /usr/local/bin/python3.14"
echo ""

# Step 5: Update alternatives
print_step "Configuring Python 3.14 as default python3..."
sudo update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.14 1

print_info "Current Python alternatives:"
sudo update-alternatives --display python3 || true
echo ""

print_step "Setting python3.14 as the selected alternative..."
# Auto-select python3.14
sudo update-alternatives --set python3 /usr/local/bin/python3.14

print_success "Python 3.14.0 set as default python3"
echo ""

# Step 6: Verify installation
print_step "Verifying installation..."
echo "Python version:"
python3 --version
echo ""
echo "Python 3.14 version:"
python3.14 --version
echo ""
echo "Python location:"
which python3
echo ""

# Step 7: Update pip
print_step "Updating pip for Python 3.14..."
python3.14 -m ensurepip --upgrade
python3.14 -m pip install --upgrade pip setuptools wheel

print_success "pip updated successfully"
echo ""

# Step 8: Offer to recreate project virtual environment
print_step "Virtual environment setup..."
PROJECT_DIR="/home/daihungpham/__projects__/4genthub/agenthub_main"

if [ -d "$PROJECT_DIR" ]; then
    print_info "Project directory found: $PROJECT_DIR"
    echo ""
    read -p "Do you want to recreate the project virtual environment? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Recreating virtual environment..."
        cd "$PROJECT_DIR"

        if [ -d ".venv" ]; then
            print_info "Removing old virtual environment..."
            rm -rf .venv
        fi

        print_info "Creating new virtual environment with Python 3.14..."
        python3.14 -m venv .venv

        print_info "Activating virtual environment and installing project..."
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -e .

        print_success "Virtual environment recreated successfully"
        echo ""
        print_info "To activate the virtual environment in the future, run:"
        print_info "  cd $PROJECT_DIR"
        print_info "  source .venv/bin/activate"
    else
        print_info "Skipping virtual environment recreation"
        print_info "You can recreate it manually later with:"
        print_info "  cd $PROJECT_DIR"
        print_info "  rm -rf .venv"
        print_info "  python3.14 -m venv .venv"
        print_info "  source .venv/bin/activate"
        print_info "  pip install -e ."
    fi
else
    print_info "Project directory not found: $PROJECT_DIR"
    print_info "Virtual environment must be created manually"
fi

echo ""
print_success "=========================================="
print_success "Python 3.14.0 installation completed!"
print_success "=========================================="
echo ""
print_info "Summary:"
print_info "  - Python 3.14.0 installed to: /usr/local/bin/python3.14"
print_info "  - Default python3 points to: $(which python3)"
print_info "  - Python version: $(python3 --version)"
print_info "  - pip version: $(python3 -m pip --version)"
echo ""
print_info "Cleanup:"
print_info "You can safely delete the source files with:"
print_info "  rm -rf /tmp/Python-3.14.0 /tmp/Python-3.14.0.tgz"
echo ""
