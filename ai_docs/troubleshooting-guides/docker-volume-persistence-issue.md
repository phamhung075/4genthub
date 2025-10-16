# Docker Volume Persistence Issue - Data Not Cleaned After Rebuild

**Date**: 2025-10-16
**Status**: ✅ RESOLVED
**Impact**: Old database schema persists after Docker rebuild, causing schema mismatch errors

## Problem Summary

When using Docker menu option 9 (Force Complete Rebuild) followed by option B (Database Only), the system still contained old data even though everything was supposedly rebuilt from scratch. This caused the `subtask_count` column to be missing from the tasks table, leading to backend hangs.

## Root Cause

### The Docker Volume Persistence Problem

Docker volumes are **independent of containers** and persist even when containers are removed. The system uses a named volume `agenthub_postgres_data` to store PostgreSQL data:

```yaml
# docker-compose.db-only.yml
volumes:
  - agenthub_postgres_data:/var/lib/postgresql/data
```

### What Happens During Rebuild

1. **User runs Option 9** (Force Complete Rebuild):
   - ✅ Stops all containers
   - ✅ Removes all containers
   - ✅ Removes all images
   - ✅ Clears build cache
   - ❌ **DOES NOT remove Docker volumes** (line 361 has `--volumes` flag BUT containers must be stopped first for it to work properly)

2. **User runs Option B** (Database Only):
   - Creates new PostgreSQL container
   - **Mounts the EXISTING volume** `agenthub_postgres_data`
   - Container sees **old database files** from before code changes
   - Result: Old schema without `subtask_count` column

### Why It's Confusing

From the user's perspective:
- "I rebuilt everything!"
- "I restarted the database!"
- "Why do I still have old data?"

The answer: **The data lives in the volume, not the container.**

## Evidence

```bash
$ docker volume ls | grep agenthub
agenthub_postgres_data  # ← This volume persists between rebuilds

$ docker volume inspect agenthub_postgres_data
"Mountpoint": "/var/lib/docker/volumes/agenthub_postgres_data/_data"
# This directory contains all PostgreSQL data files from previous runs
```

## The Fix

### Manual Solution (What We Did)

```bash
# 1. Stop and remove the PostgreSQL container
docker stop agenthub-postgres
docker rm agenthub-postgres

# 2. Remove the volume containing old data
docker volume rm agenthub_postgres_data

# 3. Restart the database (creates fresh volume)
echo "B" | ./docker-system/docker-menu.sh
```

### Verification After Fix

```sql
-- Check the tasks table schema
\d tasks

-- Look for subtask_count column:
subtask_count | integer | not null  -- ✅ Column exists!
```

### Better Solution (Update docker-menu.sh)

The script's Option 9 should explicitly remove volumes:

```bash
# Current code (line 361):
docker system prune -af --volumes 2>/dev/null || true

# Problem: This only removes UNUSED volumes. If the postgres container
# is still running or was just stopped, the volume is considered "in use"

# Better approach:
force_complete_rebuild() {
    # ... existing code ...

    # NEW: Stop all containers first
    echo -e "${YELLOW}🛑 Stopping all agenthub containers...${RESET}"
    docker stop $(docker ps -aq --filter "name=agenthub") 2>/dev/null || true

    # NEW: Remove all containers
    echo -e "${YELLOW}🗑️  Removing all agenthub containers...${RESET}"
    docker rm $(docker ps -aq --filter "name=agenthub") 2>/dev/null || true

    # NEW: Now remove volumes (they're no longer in use)
    echo -e "${YELLOW}🗑️  Removing all agenthub volumes...${RESET}"
    docker volume rm $(docker volume ls -q --filter "name=agenthub") 2>/dev/null || true

    # THEN run system prune
    docker system prune -af --volumes 2>/dev/null || true

    echo -e "${GREEN}✅ Complete cleanup including volumes!${RESET}"
}
```

## Prevention - Best Practices

### For Users

**When you want a truly fresh start:**

```bash
# Method 1: Use the manual cleanup sequence
docker stop $(docker ps -aq --filter "name=agenthub")
docker rm $(docker ps -aq --filter "name=agenthub")
docker volume rm agenthub_postgres_data
echo "B" | ./docker-menu.sh  # Rebuild

# Method 2: Nuclear option (removes ALL Docker data)
docker system prune -af --volumes
echo "B" | ./docker-menu.sh  # Rebuild
```

**Important**: Always check `docker volume ls` after rebuild to ensure volumes were actually removed!

### For Developers

1. **Named volumes persist by design** - This is usually good for production (data safety)
2. **For development** - Consider using bind mounts or documenting volume cleanup
3. **Update docker-menu.sh** - Option 9 should explicitly handle volumes
4. **Add a new option** - "Clean Database Only" that removes just the postgres volume

## Docker Volume Lifecycle

```
Container Lifecycle:        Volume Lifecycle:
create → start → stop → rm  create → (persists) → rm
     ↓                            ↑
     └── Mounts volume ───────────┘

Key insight: Volumes outlive containers!
```

## When Schema Changes Occur

### Proper Migration Flow

```
1. Code changes add new column (subtask_count)
2. Update ORM model
3. [CRITICAL STEP] Clean database volume OR run migrations
4. Restart backend
5. ORM creates tables with new schema
```

### What Went Wrong

```
1. Code changes add new column ✅
2. Update ORM model ✅
3. [SKIPPED] Clean database volume ❌
4. Restart backend ✅
5. ORM tries to use existing tables ❌
   → Missing column error
   → Backend hangs
```

## Related Issues

This same problem can affect:
- **Redis data** (`agenthub_redis_data` volume)
- **Backend data** (`agenthub_backend_data` volume)
- **Any named volume** used in docker-compose files

## Testing the Fix

```bash
# 1. Clean volumes
docker volume rm agenthub_postgres_data

# 2. Start database
echo "B" | ./docker-menu.sh

# 3. Check schema
PGPASSWORD=agenthub_pass docker exec agenthub-postgres \
  psql -U agenthub_user -d agenthub -c "\d tasks" | grep subtask_count

# Expected output:
# subtask_count | integer | not null
```

## Success Criteria

✅ Volumes are removed during force rebuild
✅ Database has correct schema with subtask_count
✅ Backend starts without errors
✅ Can create tasks and subtasks successfully
✅ No schema mismatch errors in logs

## Lessons Learned

1. **Containers ≠ Data** - Removing containers doesn't remove volumes
2. **Named volumes persist** - This is by design for data safety
3. **Schema changes need migration strategy** - Either clean volumes or run migrations
4. **Document volume cleanup** - Users need to know when/how to clean volumes
5. **Test rebuild scripts** - Ensure they actually remove ALL state

## Recommendation

**Add to docker-menu.sh Option 9:**
```bash
echo -e "${RED}⚠️ WARNING: This will also remove database volumes (data will be lost)${RESET}"
read -p "Continue? Type 'yes' to confirm: " confirm

if [[ "$confirm" == "yes" ]]; then
    # ... existing cleanup ...

    # Add explicit volume removal
    docker volume rm agenthub_postgres_data 2>/dev/null || true
    docker volume rm agenthub_redis_data 2>/dev/null || true
    docker volume rm agenthub_backend_data 2>/dev/null || true

    echo -e "${GREEN}✅ Volumes removed - next build will have fresh database${RESET}"
fi
```

## Additional Resources

- Docker Volumes Documentation: https://docs.docker.com/storage/volumes/
- Managing Docker Data: https://docs.docker.com/storage/
- Docker System Prune: https://docs.docker.com/engine/reference/commandline/system_prune/

---

**Key Takeaway**: When rebuilding Docker services after schema changes, always explicitly remove volumes to ensure a clean slate!
