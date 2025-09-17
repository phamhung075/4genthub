# Migration Guides

This folder contains migration documentation for upgrading and transitioning between different versions and configurations of the 4genthub platform.

## 📋 Contents

### Agent Library Migrations
- **[Agent Library Cleanup Migration Guide](agent-library-cleanup-migration-guide.md)** - **NEW 2025-09-06** - Step-by-step guide to implement agent library cleanup from 69 to 43 agents

### Authentication & Configuration Migrations
- **[Authentication Configuration Migration](authentication-config-migration-2025-09-05.md)** - **NEW** - Migration from `MCP_AUTH_ENABLED` to `AUTH_ENABLED` and `AUTH_PROVIDER` (2025-09-05)

### Context System Migrations
- **[Hierarchical Context Migration](HIERARCHICAL_CONTEXT_MIGRATION.md)** - Migration from basic to hierarchical context system
- **[Context Auto-Detection Fix](CONTEXT_AUTO_DETECTION_FIX.md)** - Enhanced auto-detection with error handling
- **[Unified Context Migration Guide](unified_context_migration_guide.md)** - Migration to unified context system

### Database Migrations
- **[SQLite Cleanup Summary](sqlite-cleanup-summary.md)** - SQLite to PostgreSQL migration cleanup
- **[Database Migration Complete](database-migration-complete.md)** - Complete database migration status and validation

## 🔄 Migration Process

All migration guides follow a standardized process:

1. **Pre-Migration Assessment** - System readiness and compatibility checks
2. **Backup Procedures** - Data protection and rollback preparation
3. **Step-by-Step Migration** - Detailed implementation instructions
4. **Validation & Testing** - Post-migration verification procedures
5. **Rollback Plans** - Emergency recovery procedures

## ⚠️ Important Notes

- **Always backup your data** before starting any migration
- **Test migrations in staging** before applying to production
- **Follow the migration order** as dependencies exist between components
- **Monitor system health** during and after migration

## 🎯 Migration Types

- **Agent Library Optimization** - Agent consolidation and cleanup for better maintainability
- **Context System Upgrades** - Hierarchical and unified context implementations
- **Database Schema Changes** - PostgreSQL and SQLite migrations  
- **API Version Updates** - MCP tool compatibility updates
- **Feature Enhancements** - New functionality integration

## 👥 Audience

- **System Administrators**: Production migration planning and execution
- **DevOps Engineers**: Deployment and infrastructure updates
- **Senior Developers**: Technical migration implementation
- **Project Managers**: Migration timeline and risk assessment