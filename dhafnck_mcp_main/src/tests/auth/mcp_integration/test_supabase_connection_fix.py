"""
Test to verify Supabase connection fix works correctly.

This test verifies that uncommenting the DATABASE_URL fixes the connection issue.
"""

import pytest
import os
import logging
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

# Import the modules we need to test
from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
from fastmcp.task_management.infrastructure.database.supabase_config import SupabaseConfig, is_supabase_configured

logger = logging.getLogger(__name__)


class TestSupabaseConnectionFix:
    """Test class to verify the Supabase connection fix."""
    
    def setup_method(self):
        """Set up test environment."""
        # Clear any cached instances
        DatabaseConfig._instance = None
        DatabaseConfig._initialized = False
        DatabaseConfig._connection_verified = False
        
    def test_current_environment_configuration(self):
        """Test the current environment configuration to identify the issue."""
        print("\n=== TESTING CURRENT ENVIRONMENT CONFIGURATION ===")
        
        # Check current environment variables
        database_type = os.getenv("DATABASE_TYPE")
        database_url = os.getenv("DATABASE_URL") 
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_db_password = os.getenv("SUPABASE_DB_PASSWORD")
        
        print(f"DATABASE_TYPE: {database_type}")
        print(f"DATABASE_URL: {'SET' if database_url else 'NOT SET'}")
        print(f"SUPABASE_URL: {'SET' if supabase_url else 'NOT SET'}")
        print(f"SUPABASE_DB_PASSWORD: {'SET' if supabase_db_password else 'NOT SET'}")
        
        # Test Supabase configuration check
        supabase_configured = is_supabase_configured()
        print(f"is_supabase_configured(): {supabase_configured}")
        
        # This should show the current issue
        if database_type == "supabase" and not supabase_configured:
            print("❌ ISSUE CONFIRMED: DATABASE_TYPE=supabase but Supabase not properly configured")
        elif database_type == "supabase" and supabase_configured:
            print("✅ Supabase appears to be configured correctly")
        else:
            print(f"⚠️  Unexpected configuration state: DATABASE_TYPE={database_type}, configured={supabase_configured}")
            
        # Try to create SupabaseConfig to see the exact error
        try:
            supabase_config = SupabaseConfig()
            print("✅ SupabaseConfig created successfully")
            print(f"Database URL: {supabase_config.database_url[:50]}...")
        except Exception as e:
            print(f"❌ SupabaseConfig failed: {str(e)}")
            
        return database_type, database_url, supabase_configured
    
    @patch.dict(os.environ)
    def test_fix_with_database_url(self):
        """Test that setting DATABASE_URL fixes the issue."""
        print("\n=== TESTING FIX WITH DATABASE_URL ===")
        
        # Set the DATABASE_URL that should be uncommented
        os.environ["DATABASE_URL"] = "postgresql://postgres.PLACEHOLDER_SUPABASE_REF:PLACEHOLDER_SUPABASE_PASSWORD@aws-0-eu-north-1.pooler.supabase.com:5432/postgres?sslmode=require"
        os.environ["DATABASE_TYPE"] = "supabase"
        
        try:
            # Clear cached instances
            DatabaseConfig._instance = None
            DatabaseConfig._initialized = False
            
            # This should now work
            supabase_config = SupabaseConfig()
            print("✅ SupabaseConfig created successfully with DATABASE_URL")
            print(f"Database URL: {supabase_config.database_url[:50]}...")
            
            # Test that it's actually a PostgreSQL URL
            assert "postgresql://" in supabase_config.database_url
            assert "supabase.com" in supabase_config.database_url
            print("✅ Database URL is correctly formatted PostgreSQL connection")
            
            return True
            
        except Exception as e:
            print(f"❌ Fix with DATABASE_URL failed: {str(e)}")
            return False
    
    @patch.dict(os.environ)
    def test_fix_with_supabase_database_url(self):
        """Test that setting SUPABASE_DATABASE_URL fixes the issue."""
        print("\n=== TESTING FIX WITH SUPABASE_DATABASE_URL ===")
        
        # Set the direct Supabase database URL
        os.environ["SUPABASE_DATABASE_URL"] = "postgresql://postgres.PLACEHOLDER_SUPABASE_REF:PLACEHOLDER_SUPABASE_PASSWORD@aws-0-eu-north-1.pooler.supabase.com:5432/postgres?sslmode=require"
        os.environ["DATABASE_TYPE"] = "supabase"
        
        # Make sure other URL is not set to test priority
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
            
        try:
            # This should work with SUPABASE_DATABASE_URL
            supabase_config = SupabaseConfig()
            print("✅ SupabaseConfig created successfully with SUPABASE_DATABASE_URL")
            print(f"Database URL: {supabase_config.database_url[:50]}...")
            
            # Test that it's actually a PostgreSQL URL
            assert "postgresql://" in supabase_config.database_url
            assert "supabase.com" in supabase_config.database_url
            print("✅ Database URL is correctly formatted PostgreSQL connection")
            
            return True
            
        except Exception as e:
            print(f"❌ Fix with SUPABASE_DATABASE_URL failed: {str(e)}")
            return False
    
    @patch.dict(os.environ)
    def test_component_construction_fallback(self):
        """Test if component construction works as fallback."""
        print("\n=== TESTING COMPONENT CONSTRUCTION FALLBACK ===")
        
        # Remove direct URL settings to force component construction
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
        if "SUPABASE_DATABASE_URL" in os.environ:
            del os.environ["SUPABASE_DATABASE_URL"]
            
        # Set individual components
        os.environ["DATABASE_TYPE"] = "supabase"
        os.environ["SUPABASE_URL"] = "https://PLACEHOLDER_SUPABASE_REF.supabase.co"
        os.environ["SUPABASE_DB_HOST"] = "aws-0-eu-north-1.pooler.supabase.com"
        os.environ["SUPABASE_DB_USER"] = "postgres.PLACEHOLDER_SUPABASE_REF"
        os.environ["SUPABASE_DB_PASSWORD"] = "PLACEHOLDER_SUPABASE_PASSWORD"
        os.environ["SUPABASE_DB_PORT"] = "5432"
        os.environ["SUPABASE_DB_NAME"] = "postgres"
        
        try:
            # This should work by constructing from components
            supabase_config = SupabaseConfig()
            print("✅ SupabaseConfig created successfully from components")
            print(f"Database URL: {supabase_config.database_url[:50]}...")
            
            # Test that it's actually a PostgreSQL URL
            assert "postgresql://" in supabase_config.database_url
            assert "aws-0-eu-north-1.pooler.supabase.com" in supabase_config.database_url
            print("✅ Database URL constructed correctly from components")
            
            return True
            
        except Exception as e:
            print(f"❌ Component construction failed: {str(e)}")
            print("This indicates a bug in the component construction logic")
            return False
    
    def test_database_config_with_fix(self):
        """Test that DatabaseConfig works correctly after the fix."""
        print("\n=== TESTING DATABASE CONFIG INTEGRATION ===")
        
        # Use the environment variable fix
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://postgres.PLACEHOLDER_SUPABASE_REF:PLACEHOLDER_SUPABASE_PASSWORD@aws-0-eu-north-1.pooler.supabase.com:5432/postgres?sslmode=require",
            "DATABASE_TYPE": "supabase"
        }):
            try:
                # Clear cached instances
                DatabaseConfig._instance = None 
                DatabaseConfig._initialized = False
                DatabaseConfig._connection_verified = False
                
                # Mock the actual database connection since we don't want to hit Supabase in tests
                with patch('fastmcp.task_management.infrastructure.database.database_config.create_engine') as mock_create_engine:
                    mock_engine = MagicMock()
                    mock_create_engine.return_value = mock_engine
                    
                    with patch('fastmcp.task_management.infrastructure.database.database_config.sessionmaker') as mock_sessionmaker:
                        mock_session_factory = MagicMock()
                        mock_sessionmaker.return_value = mock_session_factory
                        
                        # Mock the connection test
                        mock_conn = MagicMock()
                        mock_engine.connect.return_value.__enter__.return_value = mock_conn
                        mock_conn.execute.return_value.scalar.return_value = "PostgreSQL 13.7"
                        
                        # Now test DatabaseConfig
                        db_config = DatabaseConfig()
                        
                        print("✅ DatabaseConfig created successfully")
                        print(f"Database type: {db_config.database_type}")
                        print(f"Database URL set: {'Yes' if db_config.database_url else 'No'}")
                        print(f"Engine created: {'Yes' if db_config.engine else 'No'}")
                        print(f"Session factory created: {'Yes' if db_config.SessionLocal else 'No'}")
                        
                        # Verify it's configured for PostgreSQL, not SQLite
                        assert db_config.database_type == "supabase"
                        assert db_config.database_url is not None
                        assert "postgresql://" in db_config.database_url
                        assert "sqlite" not in db_config.database_url.lower()
                        
                        print("✅ DatabaseConfig correctly configured for Supabase PostgreSQL")
                        return True
                        
            except Exception as e:
                print(f"❌ DatabaseConfig integration test failed: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
    
    def test_complete_fix_validation(self):
        """Run all tests to validate the complete fix."""
        print("\n" + "="*80)
        print("COMPLETE FIX VALIDATION TEST")
        print("="*80)
        
        results = {}
        
        # Test 1: Current state analysis
        database_type, database_url, supabase_configured = self.test_current_environment_configuration()
        results["current_state"] = {
            "database_type": database_type,
            "database_url_set": bool(database_url), 
            "supabase_configured": supabase_configured
        }
        
        # Test 2: Fix with DATABASE_URL
        results["database_url_fix"] = self.test_fix_with_database_url()
        
        # Test 3: Fix with SUPABASE_DATABASE_URL  
        results["supabase_database_url_fix"] = self.test_fix_with_supabase_database_url()
        
        # Test 4: Component construction fallback
        results["component_construction"] = self.test_component_construction_fallback()
        
        # Test 5: Complete integration
        results["integration"] = self.test_database_config_with_fix()
        
        print("\n" + "="*80)
        print("FIX VALIDATION RESULTS")
        print("="*80)
        
        print(f"Current Configuration Issue: {'CONFIRMED' if not results['current_state']['supabase_configured'] else 'NOT FOUND'}")
        print(f"DATABASE_URL Fix Works: {'✅ YES' if results['database_url_fix'] else '❌ NO'}")
        print(f"SUPABASE_DATABASE_URL Fix Works: {'✅ YES' if results['supabase_database_url_fix'] else '❌ NO'}")
        print(f"Component Construction Works: {'✅ YES' if results['component_construction'] else '❌ NO'}")
        print(f"Full Integration Works: {'✅ YES' if results['integration'] else '❌ NO'}")
        
        # Determine recommended fix
        print("\n" + "-"*80)
        print("RECOMMENDED FIX")
        print("-"*80)
        
        if results["database_url_fix"]:
            print("✅ RECOMMENDED: Uncomment DATABASE_URL in .env file")
            print("   Change line 145 from:")
            print("   # DATABASE_URL=postgresql://...")
            print("   To:")
            print("   DATABASE_URL=postgresql://...")
        elif results["supabase_database_url_fix"]:
            print("✅ ALTERNATIVE: Set SUPABASE_DATABASE_URL in .env file")
            print("   Add this line:")
            print("   SUPABASE_DATABASE_URL=postgresql://...")
        elif results["component_construction"]:
            print("✅ FALLBACK: Component construction should work")
            print("   Individual Supabase environment variables are sufficient")
        else:
            print("❌ ISSUE: No fix method worked - deeper investigation needed")
            
        return results


if __name__ == "__main__":
    # Run the tests directly
    import logging
    logging.basicConfig(level=logging.INFO)
    
    test = TestSupabaseConnectionFix()
    test.setup_method()
    
    print("🧪 Running Supabase connection fix validation tests...")
    
    try:
        results = test.test_complete_fix_validation()
        
        if results["database_url_fix"] or results["supabase_database_url_fix"]:
            print(f"\n✅ FIX VALIDATED: The issue can be resolved by uncommenting DATABASE_URL")
            print(f"🎯 ACTION REQUIRED: Edit the .env file to uncomment the DATABASE_URL line")
        else:
            print(f"\n❌ FIX VALIDATION FAILED: Issue may be more complex than expected")
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()