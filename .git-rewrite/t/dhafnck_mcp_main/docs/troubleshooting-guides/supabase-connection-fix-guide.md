# Supabase Connection Fix Guide

## Problem Solved
After making code changes, your Supabase data wasn't showing because:
1. ORM models didn't match actual database schema
2. Docker was caching old code with incorrect models
3. Rebuild wasn't picking up the fixes

## What Was Fixed

### 1. Database Schema Models (✅ COMPLETED)
Fixed all context table models to match Supabase exactly:
- BranchContext: Added `id` primary key, removed non-existent columns
- ProjectContext: Changed primary key to `id` 
- TaskContext: Added `id` primary key, fixed all columns
- All models now match your Supabase database structure

### 2. Docker Menu Script (✅ ENHANCED)
Updated `./docker-system/docker-menu.sh` with:
- Automatic cleanup before rebuild
- Python cache clearing
- Option 10: Force Complete Rebuild
- Better Supabase verification
- Health checks after startup

## How to Use

### Quick Rebuild (Recommended)
```bash
./docker-system/docker-menu.sh
# Select option 2 (Supabase Cloud)
```

### Force Complete Rebuild (If Issues Persist)
```bash
./docker-system/docker-menu.sh
# Select option 10 (Force Complete Rebuild)
# Then select option 2 (Supabase Cloud)
```

## What Happens Now

1. **Clean Build**: Removes old containers and images
2. **Cache Clear**: Deletes Python cache files
3. **Fresh Build**: Builds with `--no-cache` using latest code
4. **Supabase Connect**: Uses your .env credentials
5. **Data Access**: Your Supabase data is now accessible!

## Verification

After rebuild, verify connection:
```bash
# Check if backend is connected to Supabase
docker exec dhafnck-backend env | grep SUPABASE

# Check logs for errors
docker logs dhafnck-backend --tail 50

# Test API
curl http://localhost:8000/health
```

## Important Notes

- Your data is safe in Supabase Cloud
- The fix ensures ORM models match your database
- Use docker-menu.sh for all rebuilds (it handles everything)
- Option 10 is nuclear option - removes everything and rebuilds

## If Still Having Issues

1. Check .env file has all SUPABASE_* variables
2. Ensure DATABASE_TYPE=supabase in .env
3. Use option 10 for complete cleanup and rebuild
4. Check Supabase dashboard to verify data exists

Your Supabase data should now be accessible after using the updated docker-menu.sh!
