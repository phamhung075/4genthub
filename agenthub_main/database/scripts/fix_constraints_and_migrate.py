#!/usr/bin/env python3
import psycopg2
import os
import sys

def main():
    db_url = os.environ.get('SUPABASE_DB_URL')
    if not db_url:
        print("❌ SUPABASE_DB_URL not set")
        return 1
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        print("🔧 Dropping all constraints first...")
        
        # Drop all foreign key constraints
        cur.execute("""
            DO $$ 
            DECLARE 
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT conname, conrelid::regclass AS table_name
                    FROM pg_constraint
                    WHERE contype = 'f'
                    AND connamespace = 'public'::regnamespace
                )
                LOOP
                    EXECUTE 'ALTER TABLE ' || r.table_name || ' DROP CONSTRAINT IF EXISTS ' || r.conname || ' CASCADE';
                END LOOP;
            END $$;
        """)
        
        # Drop all unique constraints
        cur.execute("""
            DO $$ 
            DECLARE 
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT conname, conrelid::regclass AS table_name
                    FROM pg_constraint
                    WHERE contype = 'u'
                    AND connamespace = 'public'::regnamespace
                )
                LOOP
                    EXECUTE 'ALTER TABLE ' || r.table_name || ' DROP CONSTRAINT IF EXISTS ' || r.conname || ' CASCADE';
                END LOOP;
            END $$;
        """)
        
        print("🗑️ Dropping all tables...")
        
        # Drop all tables
        cur.execute("""
            DO $$ 
            DECLARE 
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                )
                LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        
        conn.commit()
        print("✅ All constraints and tables dropped successfully")
        
        # Now run the fresh migration
        print("🚀 Running fresh migration...")
        with open('../migrations/000_complete_database_wipe_and_fresh_init.sql', 'r') as f:
            migration_sql = f.read()
        
        cur.execute(migration_sql)
        conn.commit()
        
        print("✅ Fresh migration completed successfully!")
        
        cur.close()
        conn.close()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
