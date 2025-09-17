# Core Architecture Documentation

This folder contains the **core architectural design documents** for the agenthub AI Agent Orchestration Platform.

**🧹 Reorganized (2025-09-11)**: This folder has been cleaned from 48 files to 6 core files. Specialized documentation has been moved to appropriate folders for better organization.

## 📋 Core Contents

- **[PRD.md](PRD.md)** - Product Requirements Document with complete vision and technical requirements
- **[Architecture_Technique.md](Architecture_Technique.md)** - Detailed technical architecture with DDD principles  
- **[architecture.md](architecture.md)** - Overall system architecture and component relationships
- **[database-architecture.md](database-architecture.md)** - Database design patterns and schemas
- **[index.md](index.md)** - This folder's documentation index with cross-references

## 📁 Relocated Documentation

**Specialized documentation has been moved to:**
- **Authentication**: [ai_docs/authentication/](../authentication/) - Auth system, token security, Keycloak
- **Context System**: [ai_docs/context-system/](../context-system/) - Hierarchical context, inheritance  
- **Agent Architecture**: [ai_docs/development-guides/](../development-guides/) - Agent patterns, optimization
- **DDD Patterns**: [ai_docs/development-guides/](../development-guides/) - Domain-driven design implementation
- **MCP Integration**: [ai_docs/api-integration/](../api-integration/) - MCP server, controllers, parameters
- **Controller Architecture**: [ai_docs/development-guides/](../development-guides/) - Modular controllers, refactoring
- **Repository Patterns**: [ai_docs/development-guides/](../development-guides/) - Repository architecture, switching guides

## 🎯 Purpose

These documents provide the foundational design principles, architectural patterns, and technical decisions that guide the development of the agenthub platform. They focus on core system architecture rather than implementation details.

## 👥 Audience

- **System Architects**: Complete architectural overview and design decisions
- **Senior Developers**: Technical implementation guidance and patterns
- **Project Managers**: High-level system understanding and component relationships
- **New Team Members**: Architectural onboarding and system comprehension