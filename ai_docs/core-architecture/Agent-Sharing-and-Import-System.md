---
description: Agent Sharing and Import System - Social features for collaborative agent marketplace
date: 2025-11-01
status: design-proposal-extension
parent: User-Specific-Agent-System-Architecture.md
---

# Agent Sharing and Import System

## Executive Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Extends User-Specific Agent System with social features enabling collaborative agent marketplace |
| **Key Features** | Public sharing \| Shareable links \| Agent importing \| Creator attribution \| Name collision handling \| Import lineage tracking |
| **Database** | 2 schema extensions (user_agent_instances + agent_import_history table) |
| **Security** | Share token validation \| Import validation \| Rate limiting \| Content moderation |
| **User Workflows** | Share agent → Import agent → Browse marketplace |

---

## Core Features

| Feature | Capabilities | User Value |
|---------|--------------|------------|
| **Agent Sharing** | Make agents public \| Generate shareable link \| View public agents \| Track share stats | Share customizations with community |
| **Agent Importing** | Import via shareable link \| Name collision handling \| Track lineage | Discover and use community agents |
| **Attribution** | Display creator info (Default/user email/imported creator) \| Track original customizer | Proper credit and provenance |
| **Marketplace** | Browse public agents \| Filter by category \| Sort by popularity \| Search agents | Easy discovery |

---

## Extended Database Schema

### Table Modifications: user_agent_instances

```sql
-- Sharing fields
ALTER TABLE user_agent_instances ADD COLUMN IF NOT EXISTS
    visibility VARCHAR(20) DEFAULT 'private' CHECK (visibility IN ('private', 'public')),
    share_token VARCHAR(64) UNIQUE,
    share_count INTEGER DEFAULT 0,

    -- Attribution
    original_creator_id UUID,  -- NULL = system default, UUID = customizer
    imported_from_instance_id UUID,

    -- Tracking
    is_imported BOOLEAN DEFAULT FALSE,
    import_count INTEGER DEFAULT 0;

-- Foreign keys & Indexes
ADD CONSTRAINT fk_original_creator FOREIGN KEY (original_creator_id) REFERENCES users(id) ON DELETE SET NULL;
ADD CONSTRAINT fk_imported_from FOREIGN KEY (imported_from_instance_id) REFERENCES user_agent_instances(id) ON DELETE SET NULL;
CREATE INDEX idx_share_token ON user_agent_instances(share_token) WHERE share_token IS NOT NULL;
CREATE INDEX idx_public ON user_agent_instances(user_id, visibility) WHERE visibility = 'public';
CREATE INDEX idx_creator ON user_agent_instances(original_creator_id) WHERE original_creator_id IS NOT NULL;
```

### New Table: agent_import_history

```sql
CREATE TABLE agent_import_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    importer_user_id UUID NOT NULL,
    source_instance_id UUID NOT NULL,
    imported_instance_id UUID NOT NULL,
    imported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    share_token VARCHAR(64),
    FOREIGN KEY (importer_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (source_instance_id) REFERENCES user_agent_instances(id) ON DELETE CASCADE,
    FOREIGN KEY (imported_instance_id) REFERENCES user_agent_instances(id) ON DELETE CASCADE
);
CREATE INDEX idx_import_history_importer ON agent_import_history(importer_user_id);
CREATE INDEX idx_import_history_source ON agent_import_history(source_instance_id);
CREATE INDEX idx_import_history_date ON agent_import_history(imported_at);
```

---

## Domain Layer Extensions

### Extended Entity: UserAgentInstance

| New Fields | Type | Purpose |
|------------|------|---------|
| **visibility** | AgentVisibility enum (private/public) | Controls public access |
| **share_token** | Optional[str] (64 chars) | Unique shareable identifier |
| **share_count** | int | Tracks sharing events |
| **original_creator_id** | Optional[UserId] | None = system, UUID = customizer |
| **imported_from_instance_id** | Optional[AgentInstanceId] | Import lineage tracking |
| **is_imported** | bool | Flags imported agents |
| **import_count** | int | Popularity metric |

**Key Methods**:

| Method | Returns | Purpose |
|--------|---------|---------|
| `make_public()` | str (share_token) | Generate shareable link |
| `make_private()` | void | Revoke sharing |
| `get_shareable_link(base_url)` | str (full URL) | Construct share URL |
| `is_public()` | bool | Check visibility |
| `is_system_default()` | bool | Check if uncustomized template |
| `is_user_created()` | bool | Check if user-customized |
| `get_creator_display_name(repo)` | str | Display creator (Default/email/Unknown) |
| `_generate_share_token()` | str | secrets.token_urlsafe(48) → 64 chars |

### Domain Services

| Service | Purpose | Key Methods |
|---------|---------|-------------|
| **AgentSharingService** | Sharing logic | `share_agent()`, `revoke_sharing()`, `get_shared_agent_details()` |
| **AgentImportService** | Import logic | `import_agent()`, `_resolve_agent_name()` (collision handling), `_log_import_history()` |

**Sharing Logic**: Validate customized → make_public() → save → generate link → return ShareResult

**Import Logic**: Validate public → Check collision → Resolve name (append creator if exists) → Deep copy config → Mark imported → Log history → Increment source import_count

**Name Collision**: If template exists → Append " - created by [creator_name]" | Else → Use original name

---

## Application Layer Extensions

### Use Cases (8 total)

| Use Case | Action | Parameters | Returns |
|----------|--------|------------|---------|
| **ShareAgentUseCase** | Make public | user_id, instance_id, base_url | ShareResult (token, link) |
| **RevokeAgentSharingUseCase** | Make private | user_id, instance_id | void |
| **GetSharedAgentDetailsUseCase** | Preview before import | share_token | SharedAgentDetails (no auth) |
| **ImportAgentUseCase** | Import agent | share_token, importer_user_id | ImportResult (instance, renamed) |
| **ListSharedAgentsUseCase** | Marketplace listing | filters, page, page_size | PagedResult[SharedAgentSummary] |
| **GetMySharedAgentsUseCase** | User's shared agents | user_id | list[SharedAgentSummary] with stats |

### DTOs (4 total)

| DTO | Fields | Purpose |
|-----|--------|---------|
| **ShareResult** | share_token, shareable_link, agent_name | Share operation response |
| **SharedAgentDetails** | instance_id, agent_name, template_slug, description (500 char preview), creator_name, share_count, configuration_preview | Import preview |
| **ImportResult** | imported_instance, source_agent_name, creator_name, was_renamed (bool collision flag) | Import operation response |
| **SharedAgentSummary** | instance_id, agent_name, template_slug, category, description_preview (200 chars), creator_name, import_count, timestamps | Marketplace card |

---

## API Endpoints

### Sharing

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/agents/instances/{id}/share` | POST | Required | Share agent (body: {base_url}) → {share_token, shareable_link} |
| `/api/agents/instances/{id}/share` | DELETE | Required | Revoke sharing → {success, message} |
| `/api/agents/instances/{id}/share` | GET | Required | Share status → {is_shared, share_token, share_count, import_count} |
| `/api/agents/shared/my` | GET | Required | User's shared agents → {shared_agents: [{instance_id, agent_name, import_count}]} |

### Importing

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/agents/shared/{share_token}` | GET | None | Preview shared agent → {agent_name, template, creator, config_preview} |
| `/api/agents/import/{share_token}` | POST | Required | Import agent → {imported_instance, was_renamed, message} |
| `/api/agents/imports/history` | GET | Required | Import history → {imports: [{agent_name, source_creator, imported_at}]} |

### Marketplace

| Endpoint | Query Params | Purpose |
|----------|--------------|---------|
| `/api/agents/marketplace` | category, page, page_size, sort | Browse public agents → {agents[], pagination} |
| `/api/agents/marketplace/search` | q (search query) | Search shared agents → search results |
| `/api/agents/marketplace/trending` | - | Top imported agents this week |

---

## Frontend Components

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **ShareAgentModal** | Generate shareable link | Share/revoke toggle \| Copy link button \| Import/share count display \| Revoke button |
| **ImportAgentModal** | Import confirmation | Agent preview (name, template, creator, description) \| Capabilities preview \| Import count \| Collision warning (renamed alert) \| Import/cancel buttons |
| **AgentMarketplace** | Browse public agents | Category/sort filters \| Grid layout \| SharedAgentCard for each agent \| Pagination |
| **SharedAgentCard** | Display agent summary | Agent name \| Creator \| Description preview \| Import count \| Updated timestamp \| Import button |
| **MySharedAgents** | User's shared agents | Share link with copy button \| Import/share stats \| Revoke button per agent |

**Example Flow**: User clicks "Share" → ShareAgentModal opens → Confirm → POST /share → Display link → User copies → Share on social/email

---

## User Workflows

### Workflow 1: Sharing an Agent

| Step | Actor | Action | Result |
|------|-------|--------|--------|
| 1 | User | Click "Share" on agent | ShareAgentModal opens |
| 2 | User | Confirm share | POST /api/agents/instances/{id}/share |
| 3 | API | Update visibility='public' → Generate share_token | Updated instance |
| 4 | Frontend | Display shareable link | User copies link |

### Workflow 2: Importing an Agent

| Step | Actor | Action | Result |
|------|-------|--------|--------|
| 1 | User | Click shareable link | GET /api/agents/shared/{token} |
| 2 | API | Find public agent by token | Agent preview returned |
| 3 | Frontend | Show ImportAgentModal with preview | User reviews details |
| 4 | User | Click "Import" | POST /api/agents/import/{token} |
| 5 | API | Check collision → Append creator name if exists → Copy config → Log history | Imported instance |
| 6 | Frontend | Success notification | Agent available in My Agents |

### Workflow 3: Browse Marketplace

| Step | Actor | Action | Result |
|------|-------|--------|--------|
| 1 | User | Navigate to Marketplace | GET /api/agents/marketplace |
| 2 | API | Query public agents | Agent summaries |
| 3 | Frontend | Display agent cards | User browses |
| 4 | User | Filter by category | GET /marketplace?category=development |
| 5 | Frontend | Display filtered agents | User finds agent |
| 6 | User | Click "Import" | ImportAgentModal opens |

---

## Security Considerations

| Concern | Implementation | Enforcement |
|---------|----------------|-------------|
| **1. Share Token Security** | 64-char URL-safe tokens (secrets.token_urlsafe(48)) \| Validate format + existence + public status | Check token length = 64, verify agent is_public() |
| **2. Import Validation** | Agent exists \| Agent is_public \| Not importing own agent \| Check instance limits | ValidationResult with specific errors |
| **3. Rate Limiting** | share_agent: 10/hour \| import_agent: 20/hour \| revoke_sharing: 20/hour | Per-user rate limits enforced at API layer |
| **4. Content Moderation** | Inappropriate content check \| Malicious capabilities check \| Spam pattern detection | Validate before allowing public sharing |

**Validation Example**:
```python
# Import validation checks
if source.user_id == user_id: return error("Cannot import your own agent")
if instance_count >= MAX_INSTANCES: return error("Maximum instances reached")
if not source.is_public(): return error("Agent no longer public")
```

---

## Analytics and Metrics

### Tracking Events

| Event | Properties | Purpose |
|-------|------------|---------|
| **agent_shared** | instance_id, template_slug, timestamp | Track sharing activity |
| **agent_imported** | importer_id, source_instance_id, was_renamed, timestamp | Track import activity |
| **sharing_revoked** | instance_id, timestamp | Track revocation |

### Dashboard Metrics

- **Most imported agents** (popularity)
- **Most active sharers** (contributors)
- **Category breakdown** of shared agents
- **Import trends** over time
- **Average time** from share to first import

---

## Implementation Roadmap

| Phase | Timeline | Deliverables |
|-------|----------|-------------|
| **1. Database & Domain** | Week 1 | Extend schema \| Migration scripts \| Update UserAgentInstance entity \| Implement services \| Unit tests |
| **2. Application Layer** | Week 2 | Sharing/import use cases \| Validation logic \| Extended DTOs \| Integration tests |
| **3. API Endpoints** | Week 3 | Sharing/import/marketplace endpoints \| Rate limiting \| Auth/authz \| API tests |
| **4. Frontend Components** | Weeks 4-5 | ShareAgentModal \| ImportAgentModal \| AgentMarketplace \| SharedAgentCard \| MySharedAgents \| Share/import flows |
| **5. Testing & Polish** | Week 6 | E2E testing \| Security testing \| Performance testing \| UI/UX refinement \| Documentation \| Beta launch |

---

## Success Metrics

| Category | Metrics |
|----------|---------|
| **Technical** | Share link generation <100ms \| Import operation <500ms \| Zero unauthorized access \| 100% collision handling accuracy |
| **Business** | % users sharing ≥1 agent \| % users importing ≥1 agent \| Avg imports per shared agent \| Marketplace engagement rate \| Contributor retention |
| **User Experience** | Time to share <30s \| Time to import <1min \| User satisfaction ≥4.5/5 \| Import success rate ≥99% |

---

## Conclusion

Agent Sharing and Import System transforms user-specific agents into **collaborative marketplace** enabling:

1. **Share** customizations with community via shareable links
2. **Import** agents created by others with automatic collision handling
3. **Browse** marketplace of public agents with filtering/sorting
4. **Attribute** proper creator credit and lineage tracking
5. **Track** popularity and usage statistics for analytics

**Virtuous Cycle**: Users customize → Share → Others benefit → More customization → Better agents

**Security**: Share token validation \| Import validation \| Rate limiting \| Content moderation \| User isolation

**Next Steps**: Review with team → Gather feedback → Integrate with User-Specific Agent System Architecture implementation
