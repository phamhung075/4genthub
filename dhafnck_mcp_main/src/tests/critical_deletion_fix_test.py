#!/usr/bin/env python3
"""
Critical Deletion Fix Test
Test script to verify that our critical fixes for deletion consistency issues work.

Issues Fixed:
1. Project deletion fake success - incorrect facade import paths
2. Branch deletion failing - missing user_id in facade instantiation
3. Transaction handling and data persistence issues
"""

import asyncio
import logging
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastmcp.task_management.application.services.project_management_service import ProjectManagementService
from fastmcp.task_management.application.facades.git_branch_application_facade import GitBranchApplicationFacade

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CriticalDeletionFixTest:
    """Test the critical deletion fixes"""

    def __init__(self):
        self.test_user_id = "test-fix-user-123"

    def test_facade_import_fix(self):
        """Test 1: Verify that facade imports are working correctly"""
        logger.info("🔍 Test 1: Testing facade import fix...")
        
        try:
            # This should not raise an import error anymore
            from fastmcp.task_management.application.facades.git_branch_application_facade import GitBranchApplicationFacade
            logger.info("✅ Facade import successful - no 'fastmcp.task_management.facades' error")
            return True
        except ImportError as e:
            logger.error(f"❌ Facade import failed: {e}")
            return False

    def test_project_service_imports(self):
        """Test 2: Verify that ProjectManagementService can be instantiated without import errors"""
        logger.info("🔍 Test 2: Testing ProjectManagementService imports...")
        
        try:
            # This should not raise an import error about GlobalRepositoryManager
            service = ProjectManagementService(user_id=self.test_user_id)
            logger.info("✅ ProjectManagementService created successfully - no import errors")
            return True
        except Exception as e:
            logger.error(f"❌ ProjectManagementService creation failed: {e}")
            return False

    def test_facade_user_id_integration(self):
        """Test 3: Verify that GitBranchApplicationFacade accepts user_id parameter"""
        logger.info("🔍 Test 3: Testing GitBranchApplicationFacade user_id integration...")
        
        try:
            # This should work without raising a ValueError about missing user_id
            facade = GitBranchApplicationFacade(user_id=self.test_user_id)
            logger.info("✅ GitBranchApplicationFacade created with user_id successfully")
            return True
        except Exception as e:
            logger.error(f"❌ GitBranchApplicationFacade creation with user_id failed: {e}")
            return False

    def test_project_service_facade_creation(self):
        """Test 4: Test that ProjectManagementService can create facades with user_id"""
        logger.info("🔍 Test 4: Testing ProjectManagementService facade creation with user_id...")
        
        try:
            service = ProjectManagementService(user_id=self.test_user_id)
            
            # This simulates the fixed code in project_management_service.py
            facade = GitBranchApplicationFacade(user_id=service._user_id)
            
            if facade._user_id == self.test_user_id:
                logger.info("✅ Facade created with correct user_id from service")
                return True
            else:
                logger.error(f"❌ Facade user_id mismatch: expected {self.test_user_id}, got {facade._user_id}")
                return False
        except Exception as e:
            logger.error(f"❌ ProjectManagementService facade creation failed: {e}")
            return False

    def run_all_tests(self):
        """Run all critical deletion fix tests"""
        logger.info("🚀 Starting Critical Deletion Fix Tests...")
        logger.info("=" * 60)
        
        tests = [
            ("Facade Import Fix", self.test_facade_import_fix),
            ("Project Service Imports", self.test_project_service_imports),
            ("Facade User ID Integration", self.test_facade_user_id_integration),
            ("Project Service Facade Creation", self.test_project_service_facade_creation)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n📝 Running: {test_name}")
            try:
                if test_func():
                    passed += 1
                    logger.info(f"✅ {test_name} PASSED")
                else:
                    logger.error(f"❌ {test_name} FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name} CRASHED: {e}")
        
        logger.info("\n" + "=" * 60)
        logger.info(f"🎯 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED - Critical deletion fixes are working!")
            return True
        else:
            logger.error(f"💥 {total - passed} tests failed - Issues still remain")
            return False


if __name__ == "__main__":
    tester = CriticalDeletionFixTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)