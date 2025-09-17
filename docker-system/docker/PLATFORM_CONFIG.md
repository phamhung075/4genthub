# Docker Platform Configuration Guide

## Overview
This Dockerfile supports multi-platform builds for both ARM64 (M1/M2 Macs) and AMD64 (Intel/AMD) architectures.

## Current Configuration
- **Default Platform**: `linux/arm64` (optimized for M1/M2 Macs)
- **Version**: 2.2.0
- **BuildKit**: Enabled for optimal multi-platform support

## Platform Options

### For M1/M2 Mac Development (ARM64)
```bash
# This is the current default
DOCKER_DEFAULT_PLATFORM=linux/arm64
```

### For Intel/AMD Systems (x86_64)
```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64
```

## How to Change Platform

### Method 1: Environment Variable (Recommended)
```bash
# For ARM64 (M1/M2 Macs)
export DOCKER_DEFAULT_PLATFORM=linux/arm64
docker build -f docker-system/docker/Dockerfile.frontend.production .

# For AMD64 (Intel/AMD)
export DOCKER_DEFAULT_PLATFORM=linux/amd64
docker build -f docker-system/docker/Dockerfile.frontend.production .
```

### Method 2: Build Argument
```bash
# For ARM64
docker build --build-arg DOCKER_DEFAULT_PLATFORM=linux/arm64 -f docker-system/docker/Dockerfile.frontend.production .

# For AMD64
docker build --build-arg DOCKER_DEFAULT_PLATFORM=linux/amd64 -f docker-system/docker/Dockerfile.frontend.production .
```

### Method 3: Use Build Script
```bash
# Automatically detects your platform
./docker-system/docker/build-frontend.sh
```

### Method 4: Edit .dockerbuildrc
Edit `docker-system/docker/.dockerbuildrc` and uncomment the appropriate line for your platform.

## CapRover Deployment

For CapRover deployments, you have two options:

1. **Deploy with current platform setting** (linux/arm64):
   - Works on ARM64 CapRover servers
   - Best for development on M1/M2 Macs

2. **Change to AMD64 for production**:
   - Edit the Dockerfile before deployment
   - Change both FROM statements to use `linux/amd64`
   - Or set environment variable: `export DOCKER_DEFAULT_PLATFORM=linux/amd64`

## Troubleshooting

### "exec format error" during build
This means the wrong platform image is being used. Solutions:
1. Clear Docker cache: `docker system prune -a`
2. Pull correct platform: `docker pull --platform=linux/arm64 node:20-alpine`
3. Use the build script which auto-detects platform

### Platform warnings during build
These warnings can be ignored if the build completes successfully. They indicate cross-platform compilation is happening.

### Build fails on CapRover
Ensure CapRover server architecture matches the platform setting in the Dockerfile.

## Platform Detection
The build script automatically detects your system architecture:
- `arm64` or `aarch64` → Uses `linux/arm64`
- `x86_64` → Uses `linux/amd64`
- Other → Defaults to `linux/arm64`

## Performance Notes
- Native platform builds are fastest (ARM64 on M1/M2, AMD64 on Intel)
- Cross-platform builds work but are slower due to emulation
- Production deployments should use native platform for best performance