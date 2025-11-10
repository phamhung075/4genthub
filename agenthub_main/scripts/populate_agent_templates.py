#!/usr/bin/env python3
"""
Populate Agent Templates from agent-library

This script loads all agent templates from the agent-library YAML files
and populates them into the database. It is idempotent - running multiple
times will update existing templates rather than creating duplicates.

Usage:
    python scripts/populate_agent_templates.py
"""

import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(project_root))

from fastmcp.agent_management.application.services import YAMLAgentTemplateLoader
from fastmcp.agent_management.infrastructure.repositories import (
    ORMAgentTemplateRepository,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def populate_templates():
    """Load and populate all agent templates from agent-library"""

    # Paths
    agent_library_path = Path(__file__).parent.parent / "agent-library"

    logger.info("=" * 80)
    logger.info("AGENT TEMPLATE POPULATION SCRIPT")
    logger.info("=" * 80)
    logger.info(f"Agent Library Path: {agent_library_path}")

    # Validate path exists
    if not agent_library_path.exists():
        logger.error(f"❌ Agent library not found at: {agent_library_path}")
        return False

    try:
        # 1. Initialize loader and repository
        logger.info("\n📂 Initializing YAML loader and repository...")
        loader = YAMLAgentTemplateLoader(str(agent_library_path))
        repository = ORMAgentTemplateRepository()

        # 2. Load all agent templates from YAML
        logger.info("\n📖 Loading agent templates from YAML files...")
        templates = loader.load_all_agents()

        if not templates:
            logger.warning("⚠️  No agent templates found in agent-library")
            return False

        logger.info(f"✅ Loaded {len(templates)} agent templates from YAML")

        # 3. Save each template to database (idempotent)
        logger.info("\n💾 Saving agent templates to database...")
        saved_count = 0
        updated_count = 0
        error_count = 0

        for template in templates:
            try:
                # Check if template already exists
                existing = repository.find_by_slug(template.slug)

                if existing:
                    logger.info(f"🔄 Updating existing template: {template.slug}")
                    # Update the existing template ID to maintain relationships
                    template.id = existing.id
                    repository.save(template)
                    updated_count += 1
                else:
                    logger.info(f"➕ Creating new template: {template.slug}")
                    repository.save(template)
                    saved_count += 1

            except Exception as e:
                logger.error(f"❌ Error saving template {template.slug}: {e}")
                error_count += 1
                continue

        # 4. Report results
        logger.info("\n" + "=" * 80)
        logger.info("POPULATION RESULTS")
        logger.info("=" * 80)
        logger.info(f"✅ New templates created: {saved_count}")
        logger.info(f"🔄 Existing templates updated: {updated_count}")
        logger.info(f"❌ Errors encountered: {error_count}")
        logger.info(f"📊 Total templates in database: {saved_count + updated_count}")
        logger.info("=" * 80)

        if error_count > 0:
            logger.warning(f"\n⚠️  {error_count} errors occurred during population")
            return False

        logger.info("\n✅ Agent template population completed successfully!")
        return True

    except Exception as e:
        logger.error(f"\n❌ Fatal error during population: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    logger.info("Starting agent template population...\n")
    success = populate_templates()

    if success:
        logger.info("\n🎉 SUCCESS: All agent templates populated successfully!")
        sys.exit(0)
    else:
        logger.error("\n💥 FAILED: Agent template population encountered errors")
        sys.exit(1)
