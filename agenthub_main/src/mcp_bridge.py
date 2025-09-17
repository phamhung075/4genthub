#!/usr/bin/env python3
"""
MCP Bridge Script
Bridges Claude Desktop (stdio) to agenthub HTTP Server

DEBUGGING GUIDE:
================
1. Log Files:
   - Main log: /tmp/mcp_bridge.log
   - Contains detailed request/response data, connection info, and errors
   
2. Testing the Bridge:
   - Simple test: echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | python3 mcp_bridge.py
   - Check server is running: curl http://localhost:8000/health
   - View logs: tail -f /tmp/mcp_bridge.log
   
3. Common Issues:
   - "Invalid request parameters": Check that clientInfo is included in initialize requests
   - "Not Found": Server uses redirects, ensure requests go to /mcp/ (with trailing slash)
   - No response: Check if server is running with docker ps
   - EOF immediately: Normal when no input provided (e.g., running directly)
   
4. Log Levels:
   - INFO: High-level flow (connections, requests received)
   - DEBUG: Detailed data (full requests, responses, raw input)
   - ERROR: Problems (connection failures, invalid JSON)
   
5. Key Debug Points:
   - Line 139-146: Logs each incoming request with size and number
   - Line 157-159: Logs parsed request details
   - Line 176-178: Logs forwarding to server and response receipt
   - Line 182-185: Logs response sent back to client
"""
import sys
import json
import requests
import asyncio
import logging
import time
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mcp_bridge.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('mcp_bridge')

MCP_SERVER_URL = "http://localhost:8000"
MCP_ENDPOINT = f"{MCP_SERVER_URL}/mcp/"  # Note the trailing slash
MAX_RETRIES = 3
RETRY_DELAY = 1.0

class MCPBridge:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 30
        # Allow redirects
        self.session.max_redirects = 10
        # Debug verbosity flag
        self.debug_verbose = logger.level <= logging.DEBUG
        
    def test_connection(self) -> bool:
        """Test if the MCP server is available"""
        try:
            response = self.session.get(f"{MCP_SERVER_URL}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def send_request(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        """Send JSON-RPC request to MCP server"""
        try:
            # All requests go to the same MCP endpoint with trailing slash
            url = MCP_ENDPOINT  # http://localhost:8000/mcp/
            method = data.get("method", "")
            
            logger.debug(f"Sending {method} request to: {url}")
            
            # Add clientInfo if it's an initialize request and missing
            # This is required by the MCP protocol for initialization
            if method == "initialize" and data.get("params"):
                if "clientInfo" not in data["params"]:
                    data["params"]["clientInfo"] = {
                        "name": "mcp-bridge",
                        "version": "1.0.0"
                    }
                    logger.debug("Added missing clientInfo to initialize request")
            
            # Headers required by MCP protocol for HTTP transport
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"  # Required for streamable HTTP transport
            }
            
            response = self.session.post(
                url,
                json=data,
                headers=headers
            )
            
            logger.debug(f"Response status: {response.status_code} | Request: {json.dumps(data, indent=2) if self.debug_verbose else f'{method} request'}")
            
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    logger.debug(f"Server response: {json.dumps(json_response, indent=2)}")
                    
                    # The MCP server should return proper JSON-RPC responses
                    # Just pass them through
                    return json_response
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse server response as JSON: {e}")
                    logger.error(f"Raw response: {response.text}")
                    return {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "error": {
                            "code": -32603,
                            "message": f"Server returned invalid JSON: {str(e)}"
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": data.get("id"),
                    "error": {
                        "code": response.status_code,
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
                }
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return {
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def run(self):
        """Main bridge loop"""
        logger.info("Starting MCP Bridge...")
        
        # Test connection
        if not self.test_connection():
            logger.error("Cannot connect to MCP server. Make sure Docker container is running.")
            logger.error("Run: docker ps | grep agenthub-server")
            logger.error("If not running: cd /path/to/agenthub_main && docker-compose up -d")
            sys.exit(1)
        
        logger.info("Connected to MCP server successfully")
        logger.info(f"Waiting for input from stdin...")
        logger.info("Bridge ready to process MCP requests")
        
        request_count = 0
        while True:
            try:
                # Read from stdin (Claude Desktop)
                logger.debug("Reading from stdin...")
                line = sys.stdin.readline()
                if not line:
                    logger.info("EOF received, shutting down")
                    break
                
                request_count += 1
                logger.info(f"Received request #{request_count}: {len(line)} bytes")
                
                line = line.strip()
                if not line:
                    logger.debug("Empty line received, skipping")
                    continue
                
                logger.debug(f"Raw input: {line[:200]}..." if len(line) > 200 else f"Raw input: {line}")
                
                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                    logger.info(f"Parsed request: method={request.get('method')}, id={request.get('id')}")
                    logger.debug(f"Full request: {json.dumps(request, indent=2)}")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    logger.error(f"Failed to parse: {line}")
                    # Continue to send error response below
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response))
                    sys.stdout.flush()
                    continue
                
                # Forward to HTTP MCP server
                logger.info(f"Forwarding request to MCP server...")
                response = self.send_request(request)
                logger.info(f"Got response from MCP server, sending back to Claude Desktop")
                
                # Send response back to stdout (Claude Desktop)
                response_json = json.dumps(response)
                logger.debug(f"Response sent to stdout: {response_json[:200]}..." if len(response_json) > 200 else f"Response sent to stdout: {response_json}")
                print(response_json)
                sys.stdout.flush()
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()

async def main():
    logger.info("=" * 80)
    logger.info("MCP Bridge Starting Up")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Process ID: {sys.platform}")
    logger.info(f"Log file: /tmp/mcp_bridge.log")
    logger.info("=" * 80)
    
    bridge = MCPBridge()
    await bridge.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)