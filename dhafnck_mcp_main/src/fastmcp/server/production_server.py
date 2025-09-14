#!/usr/bin/env python
"""
Production Server Entry Point
Uses factory pattern for consistent configuration.
Compatible with gunicorn/uvicorn for production deployment.
"""

import os
import sys
import logging
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

# Configure logging
logging.basicConfig(level=os.getenv("APP_LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Import the app factory
from fastmcp.server.app_factory import app_factory

# Create the application using factory
logger.info("Creating production application using factory pattern...")
app = app_factory.create_app(
    title="DhafnckMCP Production Server",
    description="Unified MCP and API server with factory pattern",
    enable_cors=True,
    enable_auth=os.getenv("AUTH_ENABLED", "true").lower() == "true",
)

logger.info("✅ Production server ready")
logger.info(f"CORS configuration loaded from CORS_ORIGINS: {os.getenv('CORS_ORIGINS', 'not set')}")

if __name__ == "__main__":
    # For direct execution (development)
    import uvicorn
    port = int(os.environ.get("FASTMCP_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)