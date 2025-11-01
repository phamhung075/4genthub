# Database Migration Guide

Complete guide for managing database schema changes in the agenthub project.

## Quick Reference

| Task | Command |
|------|---------|
| **Create migration** | `python scripts/migrate.py create "description"` |
| **Auto-generate** | `python scripts/migrate.py auto "detected changes"` |
| **Apply all pending** | `python scripts/migrate.py upgrade head` |
| **Rollback one** | `python scripts/migrate.py downgrade -1` |
| **View history** | `python scripts/migrate.py history` |
| **Fresh start** | `python scripts/reset_database.py` |

---

## Migration Strategies

### 1. Alembic Migrations (Production-Ready) ⭐ Recommended

**When to use:**
- Production and staging environments
- Need rollback capability
- Team collaboration (tracked in git)
- Complex schema changes

**Advantages:**
- ✅ Version controlled
- ✅ Rollback support
- ✅ Auto-detection of changes
- ✅ Database-agnostic
- ✅ Industry standard

### 2. Raw SQL Migrations (Development)

**When to use:**
- Quick local fixes
- Testing schema changes
- One-off database modifications
- Development environment only

**Advantages:**
- ✅ Simple and fast
- ✅ Direct SQL control
- ✅ No dependencies
- ✅ Easy to understand

### 3. Database Reset (Development Only)

**When to use:**
- Fresh local development
- Complete schema redesign
- Data loss is acceptable
- Faster than migrations

**Advantages:**
- ✅ Guaranteed clean state
- ✅ ORM = Database truth
- ✅ No migration complexity
- ✅ Fastest approach

---

## Alembic Workflow (Detailed)

### Setup (Already Done)

The project is configured with:
- `alembic.ini` - Configuration
- `alembic/env.py` - Environment setup
- `alembic/versions/` - Migration files
- `scripts/migrate.py` - Helper script

### Creating Migrations

#### Method 1: Manual Migration

```bash
# Create empty migration
python scripts/migrate.py create "remove subtask_count column"

# This creates: alembic/versions/YYYYMMDD_HHMM_<rev>_remove_subtask_count_column.py
```

Edit the generated file:

```python
def upgrade() -> None:
    # Add your changes
    op.drop_column('tasks', 'subtask_count')


def downgrade() -> None:
    # Add rollback logic
    op.add_column('tasks',
        sa.Column('subtask_count', sa.Integer(), nullable=False, server_default='0')
    )
```

Apply it:

```bash
python scripts/migrate.py upgrade head
```

#### Method 2: Auto-Generate (Recommended)

```bash
# 1. Update your ORM models first (e.g., remove subtask_count from models.py)

# 2. Auto-generate migration
python scripts/migrate.py auto "remove subtask_count column"

# 3. Review generated file in alembic/versions/

# 4. Apply migration
python scripts/migrate.py upgrade head
```

**⚠️ Important:** Always review auto-generated migrations before applying!

### Managing Migrations

```bash
# View current version
python scripts/migrate.py current

# View migration history
python scripts/migrate.py history

# Show specific migration
python scripts/migrate.py show <revision>

# Apply next migration
python scripts/migrate.py upgrade +1

# Apply specific migration
python scripts/migrate.py upgrade <revision>

# Rollback last migration
python scripts/migrate.py downgrade -1

# Rollback all migrations
python scripts/migrate.py downgrade base
```

---

## Raw SQL Migration Workflow

### 1. Create SQL File

```bash
# Create migration in migrations directory
nano migrations/remove_subtask_count_column.sql
```

```sql
-- Migration: Remove subtask_count column
-- Date: 2025-11-01

ALTER TABLE tasks DROP COLUMN IF EXISTS subtask_count;
```

### 2. Apply Migration

```bash
python scripts/apply_migration.py migrations/remove_subtask_count_column.sql
```

Features:
- Tracks applied migrations in `schema_migrations` table
- Prevents duplicate applications
- Shows SQL preview before applying
- Requires confirmation

### 3. List Migrations

```bash
python scripts/apply_migration.py --list
```

---

## Database Reset Workflow

### Complete Reset

```bash
python scripts/reset_database.py
```

This will:
1. Drop all existing tables
2. Recreate from ORM models
3. Give you a fresh database

**⚠️ Warning:** All data will be lost!

### When to Reset vs Migrate

| Situation | Use Reset | Use Migration |
|-----------|-----------|---------------|
| Local development | ✅ | Optional |
| Shared development | ❌ | ✅ |
| Staging environment | ❌ | ✅ |
| Production | ❌ | ✅ Required |
| Need to preserve data | ❌ | ✅ |
| Quick schema fixes | ✅ | Optional |

---

## Solving the subtask_count Issue

### Option A: Migration (Preserve Data)

```bash
# Auto-generate migration
python scripts/migrate.py auto "remove subtask_count column from tasks table"

# Review the migration file
cat alembic/versions/*_remove_subtask_count*.py

# Apply migration
python scripts/migrate.py upgrade head
```

### Option B: Quick SQL (Development)

```bash
# Use existing SQL file
python scripts/apply_migration.py migrations/remove_subtask_count_column.sql
```

### Option C: Reset (Fastest, Data Loss)

```bash
# Complete fresh start
python scripts/reset_database.py

# Type RESET to confirm
```

---

## Best Practices

### ✅ DO

1. **Review Auto-Generated Migrations**
   ```bash
   python scripts/migrate.py auto "changes"
   # Review file before applying
   python scripts/migrate.py upgrade head
   ```

2. **Test Migrations Locally First**
   ```bash
   # Test upgrade
   python scripts/migrate.py upgrade head

   # Test downgrade
   python scripts/migrate.py downgrade -1

   # Re-upgrade
   python scripts/migrate.py upgrade head
   ```

3. **Write Descriptive Messages**
   ```bash
   # Good
   python scripts/migrate.py create "add user_preferences table with jsonb column"

   # Bad
   python scripts/migrate.py create "changes"
   ```

4. **Always Include Downgrade**
   ```python
   def upgrade():
       op.add_column('tasks', sa.Column('new_field', sa.String()))

   def downgrade():
       op.drop_column('tasks', 'new_field')  # Always provide rollback
   ```

5. **Commit Migrations to Git**
   ```bash
   git add alembic/versions/
   git commit -m "Add migration: remove subtask_count column"
   ```

### ❌ DON'T

1. **Don't Edit Applied Migrations**
   - Create a new migration instead

2. **Don't Skip Migration Testing**
   - Always test upgrade and downgrade

3. **Don't Trust Auto-Generate Blindly**
   - Review and edit as needed

4. **Don't Forget Backups (Production)**
   ```bash
   # Before production migrations
   pg_dump agenthub > backup_before_migration.sql
   ```

---

## Common Scenarios

### Scenario 1: Add New Column

```bash
python scripts/migrate.py create "add status_notes to tasks"
```

```python
def upgrade():
    op.add_column('tasks',
        sa.Column('status_notes', sa.Text(), nullable=True)
    )

def downgrade():
    op.drop_column('tasks', 'status_notes')
```

### Scenario 2: Rename Column

```bash
python scripts/migrate.py create "rename description to details in tasks"
```

```python
def upgrade():
    op.alter_column('tasks', 'description',
        new_column_name='details'
    )

def downgrade():
    op.alter_column('tasks', 'details',
        new_column_name='description'
    )
```

### Scenario 3: Add Index

```bash
python scripts/migrate.py create "add index on tasks.status"
```

```python
def upgrade():
    op.create_index('idx_tasks_status', 'tasks', ['status'])

def downgrade():
    op.drop_index('idx_tasks_status', table_name='tasks')
```

### Scenario 4: Data Migration

```bash
python scripts/migrate.py create "populate default task priorities"
```

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add new column
    op.add_column('tasks',
        sa.Column('priority_level', sa.Integer(), nullable=True)
    )

    # Migrate data
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            UPDATE tasks
            SET priority_level = CASE priority
                WHEN 'low' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'high' THEN 3
                WHEN 'urgent' THEN 4
                WHEN 'critical' THEN 5
                ELSE 2
            END
        """)
    )

    # Make non-nullable after data migration
    op.alter_column('tasks', 'priority_level',
        nullable=False
    )

def downgrade():
    op.drop_column('tasks', 'priority_level')
```

---

## Troubleshooting

### Issue: "Target database is not up to date"

```bash
# Check current version
python scripts/migrate.py current

# Apply pending migrations
python scripts/migrate.py upgrade head
```

### Issue: "Can't locate revision"

```bash
# View migration history
python scripts/migrate.py history

# Check alembic_version table
python scripts/reset_database.py  # If corrupted
python scripts/migrate.py upgrade head
```

### Issue: Migration Failed Mid-Way

```bash
# Check current state
python scripts/migrate.py current

# Try to downgrade
python scripts/migrate.py downgrade -1

# Fix the migration file
# Re-apply
python scripts/migrate.py upgrade head
```

### Issue: Want Clean Start

```bash
# Reset everything
python scripts/reset_database.py

# Optional: Apply all migrations
python scripts/migrate.py upgrade head
```

---

## Migration Files Reference

### Project Structure

```
agenthub_main/
├── alembic/                         # Alembic migrations
│   ├── versions/                    # Migration files
│   │   └── YYYYMMDD_HHMM_<rev>_description.py
│   ├── env.py                       # Environment config
│   └── script.py.mako              # Template
├── alembic.ini                      # Alembic configuration
├── migrations/                      # Raw SQL migrations
│   ├── remove_subtask_count_column.sql
│   └── update_context_models.sql
└── scripts/                         # Helper scripts
    ├── migrate.py                   # Main migration tool
    ├── apply_migration.py           # SQL migration runner
    └── reset_database.py            # Database reset
```

### Environment Variables

The migration system uses database config from `.env` or `.env.dev`:

```bash
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=agenthub
DATABASE_USER=agenthub_user
DATABASE_PASSWORD=your_password
```

---

## Summary

### For Your Current Issue (subtask_count)

**Quick Fix (Development):**
```bash
python scripts/reset_database.py
```

**Proper Migration (Shared/Production):**
```bash
python scripts/migrate.py auto "remove subtask_count computed column"
python scripts/migrate.py upgrade head
```

### Remember

- **Development**: Reset is fine
- **Shared/Production**: Always use migrations
- **Review**: Auto-generated migrations before applying
- **Test**: Migrations locally first
- **Commit**: Migration files to version control
- **Backup**: Production data before migrations

---

**Need Help?**
```bash
python scripts/migrate.py --help
```
