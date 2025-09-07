#!/bin/bash

set -e

echo "🗄️  Running Database Migrations"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Load environment
if [ -f ".env.pro" ]; then
    export $(cat .env.pro | grep -v '^#' | xargs)
    print_status "Loaded production environment variables"
else
    print_error "Production environment file (.env.pro) not found"
fi

# Check if backend container is running
BACKEND_CONTAINER="srv-captain--${CAPROVER_BACKEND_APP_NAME}"

if docker ps | grep -q $BACKEND_CONTAINER; then
    print_status "Backend container is running"
    
    # Run migrations using the backend container
    print_status "Executing database migrations..."
    docker exec $BACKEND_CONTAINER python -m dhafnck_mcp_main.src.infrastructure.database.migrations.run_migrations || {
        print_warning "Direct migration failed, trying alternative approach..."
        
        # Alternative approach using database connection
        docker exec $BACKEND_CONTAINER python -c "
from dhafnck_mcp_main.src.infrastructure.database.session import get_engine
from dhafnck_mcp_main.src.infrastructure.database.models import Base
import os

# Create all tables
engine = get_engine()
Base.metadata.create_all(bind=engine)
print('✅ Database tables created/updated successfully')
" || print_error "Alternative migration approach also failed"
    }
    
    print_status "Database migrations completed"
    
    # Verify database connection
    print_status "Verifying database connection..."
    docker exec $BACKEND_CONTAINER python -c "
from dhafnck_mcp_main.src.infrastructure.database.session import SessionLocal
try:
    db = SessionLocal()
    db.execute('SELECT 1')
    db.close()
    print('✅ Database connection verified')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
" || print_error "Database verification failed"
    
else
    print_warning "Backend container not found or not running"
    print_status "Attempting to run migrations via direct database connection..."
    
    # Try to connect directly to PostgreSQL container
    DB_CONTAINER="srv-captain--dhafnck-postgres"
    
    if docker ps | grep -q $DB_CONTAINER; then
        print_status "Database container found, creating tables directly..."
        
        # Create basic table structure (fallback approach)
        docker exec $DB_CONTAINER psql -U $DATABASE_USER -d $DATABASE_NAME -c "
        -- Create basic tables if they don't exist
        CREATE TABLE IF NOT EXISTS projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS git_branches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
            git_branch_name VARCHAR(255) NOT NULL,
            git_branch_description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_id, git_branch_name)
        );
        
        CREATE TABLE IF NOT EXISTS tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            git_branch_id UUID REFERENCES git_branches(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(50) DEFAULT 'todo',
            priority VARCHAR(50) DEFAULT 'medium',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS contexts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            level VARCHAR(50) NOT NULL,
            context_id UUID NOT NULL,
            user_id UUID,
            project_id UUID,
            git_branch_id UUID,
            data JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(level, context_id, user_id)
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_tasks_git_branch_id ON tasks(git_branch_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_contexts_level ON contexts(level);
        CREATE INDEX IF NOT EXISTS idx_contexts_context_id ON contexts(context_id);
        
        SELECT 'Database structure created successfully' as result;
        " || print_error "Direct database table creation failed"
        
        print_status "Basic database structure created"
    else
        print_error "Neither backend nor database container found"
    fi
fi

print_status "Migration process completed!"
echo ""
echo "🔍 To verify the migration:"
echo "   1. Check application logs: caprover logs --caproverApp ${CAPROVER_BACKEND_APP_NAME}"
echo "   2. Test API endpoints: curl https://your-backend-url/health"
echo "   3. Connect to database: docker exec -it ${DB_CONTAINER:-srv-captain--dhafnck-postgres} psql -U ${DATABASE_USER} -d ${DATABASE_NAME}"