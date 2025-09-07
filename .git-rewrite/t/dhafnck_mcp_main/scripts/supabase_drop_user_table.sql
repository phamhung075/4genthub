-- ============================================================
-- DROP USER TABLE FROM PUBLIC SCHEMA
-- ============================================================
-- Purpose: Remove user table from public schema if it exists
-- Date: 2025-08-19
-- Note: Supabase uses auth.users for authentication, not public.users

-- Drop the table if it exists in public schema
DROP TABLE IF EXISTS public.users CASCADE;
DROP TABLE IF EXISTS public.user CASCADE;

-- Also check for any related user tables that might exist
DROP TABLE IF EXISTS public.user_profiles CASCADE;
DROP TABLE IF EXISTS public.profiles CASCADE;

-- Verify deletion
SELECT 
    schemaname,
    tablename
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('users', 'user', 'user_profiles', 'profiles');

-- This should return no rows if successful

-- Note: The auth.users table is managed by Supabase Auth
-- and should NOT be deleted. It's in the 'auth' schema, not 'public'