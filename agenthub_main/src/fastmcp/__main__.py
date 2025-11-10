#!/usr/bin/env python3
"""
Main entry point for fastmcp module.
Allows running: python -m fastmcp
"""

import os
import sys

# Ensure PDBPP doesn't interfere with imports
os.environ['PDBPP_HIJACK_PDB'] = '0'

try:
    from .server.mcp_entry_point import main
except ImportError as _:
    # If import fails during container startup, try adding paths
    sys.path.insert(0, '/app/src')
    sys.path.insert(0, '/app')
    try:
        from fastmcp.server.mcp_entry_point import main
    except ImportError as e2:
        error_msg = str(e2)
        if 'sqlalchemy' in error_msg.lower():
            print("Fatal error: SQLAlchemy is not installed.", file=sys.stderr)
            print("Please rebuild the Docker image to include SQLAlchemy.", file=sys.stderr)
            print(f"Error details: {e2}", file=sys.stderr)
        else:
            print(f"Fatal error: Cannot import fastmcp server. Error: {e2}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()