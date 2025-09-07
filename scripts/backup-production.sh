#!/bin/bash

set -e

echo "💾 DhafnckMCP Production Backup"
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

# Configuration
BACKUP_DIR="/tmp/dhafnck-mcp-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="dhafnck_mcp_backup_$TIMESTAMP"

# Load environment
if [ -f ".env.pro" ]; then
    export $(cat .env.pro | grep -v '^#' | xargs)
    print_status "Loaded production environment variables"
else
    print_error "Production environment file (.env.pro) not found"
fi

# Create backup directory
mkdir -p $BACKUP_DIR
print_status "Created backup directory: $BACKUP_DIR"

# 1. Database Backup
print_status "Creating database backup..."
DB_CONTAINER="srv-captain--dhafnck-postgres"
DB_BACKUP_FILE="$BACKUP_DIR/${BACKUP_NAME}_database.sql"

if docker ps | grep -q $DB_CONTAINER; then
    docker exec $DB_CONTAINER pg_dump \
        -U $DATABASE_USER \
        -d $DATABASE_NAME \
        --no-password > $DB_BACKUP_FILE
    
    # Compress database backup
    gzip $DB_BACKUP_FILE
    print_status "Database backup created: ${DB_BACKUP_FILE}.gz"
else
    print_warning "Database container not found, skipping database backup"
fi

# 2. Configuration Backup
print_status "Creating configuration backup..."
CONFIG_BACKUP_DIR="$BACKUP_DIR/${BACKUP_NAME}_config"
mkdir -p $CONFIG_BACKUP_DIR

# Backup environment files
if [ -f ".env.pro" ]; then
    cp .env.pro $CONFIG_BACKUP_DIR/
fi

if [ -f "dhafnck-frontend/.env.production" ]; then
    cp dhafnck-frontend/.env.production $CONFIG_BACKUP_DIR/
fi

# Backup configuration files
if [ -d "dhafnck_mcp_main/configuration" ]; then
    cp -r dhafnck_mcp_main/configuration $CONFIG_BACKUP_DIR/
fi

# Backup Docker files
cp -f Dockerfile* $CONFIG_BACKUP_DIR/ 2>/dev/null || true
cp -f docker-compose*.yml $CONFIG_BACKUP_DIR/ 2>/dev/null || true
cp -f captain-definition $CONFIG_BACKUP_DIR/ 2>/dev/null || true

if [ -f "dhafnck-frontend/captain-definition" ]; then
    cp dhafnck-frontend/captain-definition $CONFIG_BACKUP_DIR/frontend-captain-definition
fi

# Compress configuration backup
tar -czf "${CONFIG_BACKUP_DIR}.tar.gz" -C "$BACKUP_DIR" "${BACKUP_NAME}_config"
rm -rf $CONFIG_BACKUP_DIR
print_status "Configuration backup created: ${CONFIG_BACKUP_DIR}.tar.gz"

# 3. Agent Library Backup
print_status "Creating agent library backup..."
AGENT_BACKUP_FILE="$BACKUP_DIR/${BACKUP_NAME}_agents.tar.gz"

if [ -d "dhafnck_mcp_main/agent-library" ]; then
    tar -czf $AGENT_BACKUP_FILE -C "dhafnck_mcp_main" agent-library
    print_status "Agent library backup created: $AGENT_BACKUP_FILE"
else
    print_warning "Agent library directory not found, skipping agent backup"
fi

# 4. Application Logs Backup (if accessible)
print_status "Creating application logs backup..."
LOGS_BACKUP_FILE="$BACKUP_DIR/${BACKUP_NAME}_logs.tar.gz"

# Try to get logs from CapRover containers
BACKEND_CONTAINER="srv-captain--${CAPROVER_BACKEND_APP_NAME}"
FRONTEND_CONTAINER="srv-captain--${CAPROVER_FRONTEND_APP_NAME}"

LOGS_DIR="$BACKUP_DIR/logs_temp"
mkdir -p $LOGS_DIR

# Backend logs
if docker ps | grep -q $BACKEND_CONTAINER; then
    docker logs $BACKEND_CONTAINER > $LOGS_DIR/backend.log 2>&1
    print_status "Backend logs captured"
fi

# Frontend logs
if docker ps | grep -q $FRONTEND_CONTAINER; then
    docker logs $FRONTEND_CONTAINER > $LOGS_DIR/frontend.log 2>&1
    print_status "Frontend logs captured"
fi

# Database logs
if docker ps | grep -q $DB_CONTAINER; then
    docker logs $DB_CONTAINER > $LOGS_DIR/database.log 2>&1
    print_status "Database logs captured"
fi

# Compress logs
if [ "$(ls -A $LOGS_DIR)" ]; then
    tar -czf $LOGS_BACKUP_FILE -C "$BACKUP_DIR" logs_temp
    rm -rf $LOGS_DIR
    print_status "Application logs backup created: $LOGS_BACKUP_FILE"
else
    rm -rf $LOGS_DIR
    print_warning "No logs found to backup"
fi

# 5. Create backup manifest
MANIFEST_FILE="$BACKUP_DIR/${BACKUP_NAME}_manifest.txt"
cat > $MANIFEST_FILE << EOF
DhafnckMCP Production Backup Manifest
=====================================

Backup Date: $(date)
Backup Name: $BACKUP_NAME

Files included in this backup:
EOF

# List all backup files
for file in $BACKUP_DIR/${BACKUP_NAME}_*; do
    if [ -f "$file" ]; then
        echo "- $(basename $file) ($(du -h $file | cut -f1))" >> $MANIFEST_FILE
    fi
done

print_status "Backup manifest created: $MANIFEST_FILE"

# 6. Upload to cloud storage (if configured)
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$S3_BACKUP_BUCKET" ]; then
    print_status "Uploading backups to S3..."
    
    for file in $BACKUP_DIR/${BACKUP_NAME}_*; do
        if [ -f "$file" ]; then
            aws s3 cp "$file" "s3://$S3_BACKUP_BUCKET/$(basename $file)" || print_warning "Failed to upload $(basename $file)"
        fi
    done
    
    print_status "Backups uploaded to S3 bucket: $S3_BACKUP_BUCKET"
else
    print_warning "S3 configuration not found, backups stored locally only"
fi

# 7. Cleanup old backups (keep last 7 days locally)
print_status "Cleaning up old local backups..."
find $BACKUP_DIR -name "dhafnck_mcp_backup_*" -mtime +7 -delete 2>/dev/null || true

# Summary
echo ""
print_status "Backup completed successfully!"
echo ""
echo "📋 Backup Summary:"
echo "   Backup Name: $BACKUP_NAME"
echo "   Location: $BACKUP_DIR"
echo "   Files created:"

for file in $BACKUP_DIR/${BACKUP_NAME}_*; do
    if [ -f "$file" ]; then
        echo "   - $(basename $file) ($(du -h $file | cut -f1))"
    fi
done

echo ""
echo "🔍 To restore from backup:"
echo "   1. Database: gunzip < ${BACKUP_NAME}_database.sql.gz | docker exec -i $DB_CONTAINER psql -U $DATABASE_USER -d $DATABASE_NAME"
echo "   2. Configuration: tar -xzf ${BACKUP_NAME}_config.tar.gz"
echo "   3. Agents: tar -xzf ${BACKUP_NAME}_agents.tar.gz"
echo ""
echo "📅 Next backup should run on: $(date -d '+1 day')"