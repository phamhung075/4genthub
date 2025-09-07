#!/usr/bin/env python3
"""
Direct MCP Tools Testing Script
This script bypasses the MCP connection and tests the tools directly
"""

import requests
import json
import uuid
import sys
from datetime import datetime

class DirectMCPTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
        }
        # We'll test without authentication first to see what endpoints work
        
    def test_health_check(self):
        """Test basic health check"""
        print("🔍 Testing Health Check...")
        try:
            response = requests.get(f"{self.base_url}/health")
            print(f"✅ Status: {response.status_code}")
            print(f"📋 Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def test_project_management(self):
        """Test project management endpoints"""
        print("\n🚀 Testing Project Management...")
        
        # Try to create a project
        project_data = {
            "name": f"Test Project {uuid.uuid4().hex[:8]}",
            "description": "Direct API test project",
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v2/projects/",
                json=project_data,
                headers=self.headers
            )
            print(f"Create Project Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 201:
                project = response.json()
                project_id = project.get('id') or project.get('project_id')
                print(f"✅ Created project ID: {project_id}")
                return project_id
            else:
                print(f"❌ Failed to create project: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating project: {e}")
            return None
    
    def test_list_projects(self):
        """Test listing projects"""
        print("\n📋 Testing List Projects...")
        try:
            response = requests.get(f"{self.base_url}/api/v2/projects/", headers=self.headers)
            print(f"List Projects Status: {response.status_code}")
            print(f"Response: {response.text}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error listing projects: {e}")
            return False

if __name__ == "__main__":
    print("🧪 Direct MCP Tools Testing")
    print("=" * 50)
    
    tester = DirectMCPTester()
    
    # Test basic connectivity
    if not tester.test_health_check():
        print("❌ Health check failed - server may not be running")
        sys.exit(1)
    
    # Test project management
    tester.test_list_projects()
    project_id = tester.test_project_management()
    
    print("\n" + "=" * 50)
    print("🏁 Direct API Testing Complete")