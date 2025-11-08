#!/usr/bin/env python3
"""
Agent Template Verification Script

Quickly check how many agent templates are in the database.
Usage: python scripts/verify_agents.py
"""

import logging
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_agents():
    """Check agent template count in database"""
    try:
        from fastmcp.agent_management.infrastructure.repositories import (
            ORMAgentTemplateRepository,
        )

        logger.info("=" * 60)
        logger.info("Agent Template Verification")
        logger.info("=" * 60)

        repository = ORMAgentTemplateRepository()
        templates = repository.find_all()

        if templates and len(templates) > 0:
            logger.info(f"✅ Found {len(templates)} agent templates")
            logger.info("\nAgent List:")
            for i, template in enumerate(templates, 1):
                logger.info(f"  {i}. {template.name} ({template.slug})")
        else:
            logger.warning("⚠️  No agent templates found!")
            logger.warning("Run: python scripts/init_database.py to populate agents")

        logger.info("=" * 60)
        return 0

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(verify_agents())
