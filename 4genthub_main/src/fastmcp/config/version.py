"""Version configuration for 4genthub

This file contains the version information for the 4genthub server.
Update the VERSION constant when releasing new versions.
"""

import os

# Default version - can be overridden by SERVER_VERSION environment variable
DEFAULT_VERSION = "0.0.2c"

# Semantic Versioning: MAJOR.MINOR.PATCH
# MAJOR: Incompatible API changes
# MINOR: New functionality in a backward-compatible manner
# PATCH: Backward-compatible bug fixes
VERSION = os.environ.get("SERVER_VERSION", DEFAULT_VERSION)

# Additional version metadata
VERSION_INFO = {
    "version": VERSION,
    "name": "4genthub - Task Management & Agent Orchestration",
    "codename": "Vision System Enhanced",
    "release_date": "2025-09-10"
}