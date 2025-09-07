#!/usr/bin/env python3
"""
Test script for database schema validator

This script tests the schema validation functionality.
"""

import asyncio
import logging
import sys
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_schema_validation():
    """Test the schema validation functionality"""
    
    try:
        # Import required modules
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from fastmcp.task_management.infrastructure.database.schema_validator import SchemaValidator
        
        logger.info("=" * 60)
        logger.info("TESTING DATABASE SCHEMA VALIDATOR")
        logger.info("=" * 60)
        
        # Get database configuration
        db_config = get_db_config()
        if not db_config or not db_config.engine:
            logger.error("Could not get database configuration")
            return False
        
        logger.info(f"Database type: {db_config.database_type}")
        logger.info("Creating schema validator...")
        
        # Create validator
        validator = SchemaValidator(db_config.engine)
        
        # Run validation
        logger.info("Running validation...")
        results = await validator.validate_all()
        
        # Display results
        logger.info("=" * 60)
        logger.info("VALIDATION RESULTS")
        logger.info("=" * 60)
        logger.info(f"Status: {results['status']}")
        logger.info(f"Models validated: {results['validated_models']}/{results['total_models']}")
        logger.info(f"Issues found: {results['issues_count']}")
        logger.info(f"Warnings found: {results['warnings_count']}")
        
        if results['issues']:
            logger.error("\nISSUES:")
            for issue in results['issues']:
                logger.error(f"  - {issue['model']}: {issue['message']}")
        
        if results['warnings']:
            logger.warning("\nWARNINGS:")
            for warning in results['warnings']:
                logger.warning(f"  - {warning['model']}: {warning['message']}")
        
        if results['validated_models']:
            logger.info("\nVALIDATED MODELS:")
            for model in results['validated_models']:
                logger.info(f"  ✓ {model}")
        
        logger.info("=" * 60)
        
        return results['status'] == 'PASS'
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        return False


def main():
    """Main entry point"""
    success = asyncio.run(test_schema_validation())
    
    if success:
        logger.info("✅ Schema validation test PASSED")
        sys.exit(0)
    else:
        logger.error("❌ Schema validation test FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()