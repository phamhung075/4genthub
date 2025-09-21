#!/usr/bin/env python3
"""
WebSocket Connection Test Script
Tests if the WebSocket endpoint works with proper authentication
"""

import asyncio
import websockets
import json
import sys

async def test_websocket_connection():
    """Test WebSocket connection with valid authentication token"""

    # JWT token from dev-login
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlci0wMDEiLCJlbWFpbCI6ImRldkBleGFtcGxlLmNvbSIsInVzZXJuYW1lIjoiZGV2LXVzZXIiLCJpYXQiOjE3NTg0NDQyNjksImV4cCI6MTc1ODUzMDY2OSwidHlwZSI6ImxvY2FsX2RldiJ9.o17hTv7InXefA2sqq_u0HQEUGrUQ-0xk8TcfU9Qwjg8"

    # WebSocket URL with authentication token
    ws_url = f"ws://localhost:8000/ws/realtime?token={token}"

    print("Testing WebSocket connection...")
    print(f"URL: {ws_url}")

    try:
        # Connect to WebSocket
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connection successful!")

            # Wait for welcome message
            welcome_msg = await websocket.recv()
            print(f"Received welcome message: {welcome_msg}")

            # Send a ping
            ping_msg = {"type": "ping"}
            await websocket.send(json.dumps(ping_msg))
            print("Sent ping message")

            # Wait for pong response
            pong_response = await websocket.recv()
            print(f"Received pong response: {pong_response}")

            print("✅ WebSocket test completed successfully!")

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ WebSocket connection closed: {e}")
        print(f"Close code: {e.code}, reason: {e.reason}")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket connection failed with status code: {e.status_code}")

    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

    return True

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_websocket_connection())
    sys.exit(0 if result else 1)