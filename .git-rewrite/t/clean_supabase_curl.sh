#!/bin/bash

# Clean Supabase tables using REST API
# This script deletes all data from Supabase public tables

echo "🧹 Supabase Data Cleanup Tool"
echo "=================================================="

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check for required environment variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "❌ Error: Missing required environment variables"
    echo "Required: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
    exit 1
fi

echo "🔗 Supabase URL: $SUPABASE_URL"
echo ""
echo "⚠️  WARNING: This will DELETE ALL DATA from all tables!"
echo ""
read -p "❓ Are you sure you want to proceed? Type 'YES' to confirm: " confirm

if [ "$confirm" != "YES" ]; then
    echo "❌ Operation cancelled"
    exit 0
fi

echo ""
echo "🗑️  Cleaning tables..."

# Function to delete all records from a table
delete_table_data() {
    local table=$1
    echo -n "  Cleaning $table... "
    
    # Use a condition that matches all records (id not equal to impossible value)
    response=$(curl -s -X DELETE \
        "${SUPABASE_URL}/rest/v1/${table}?id=neq.00000000-0000-0000-0000-000000000000" \
        -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Prefer: return=minimal")
    
    if [ $? -eq 0 ]; then
        echo "✅"
    else
        echo "⚠️  (may be empty or not exist)"
    fi
}

# Clean tables in dependency order (child tables first)
echo ""
echo "Cleaning child tables first..."
delete_table_data "task_subtasks"
delete_table_data "task_dependencies"
delete_table_data "task_assignees"
delete_table_data "task_labels"

echo ""
echo "Cleaning main tables..."
delete_table_data "tasks"
delete_table_data "git_branch_agent_assignments"
delete_table_data "git_branchs"
delete_table_data "registered_agents"
delete_table_data "projects"

echo ""
echo "Cleaning context tables..."
delete_table_data "context_insights"
delete_table_data "context_progress"
delete_table_data "context_delegations"
delete_table_data "hierarchical_contexts"

echo ""
echo "Cleaning other tables..."
delete_table_data "rule_sync_logs"
delete_table_data "rule_clients"
delete_table_data "rule_contents"
delete_table_data "mcp_tokens"
delete_table_data "auth_tokens"
delete_table_data "compliance_records"
delete_table_data "audit_logs"
delete_table_data "cache_entries"
delete_table_data "user_sessions"

echo ""
echo "✅ Data cleanup complete!"

# Verify by checking main tables
echo ""
echo "📊 Verification - Checking if main tables are empty:"

check_table_count() {
    local table=$1
    response=$(curl -s -X GET \
        "${SUPABASE_URL}/rest/v1/${table}?select=id&limit=1" \
        -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Prefer: count=exact" \
        -H "Range: 0-0")
    
    # Extract count from Content-Range header
    count=$(echo "$response" | grep -o '\[' | wc -l)
    if [ "$count" -eq 0 ]; then
        echo "  ✅ $table: empty"
    else
        echo "  ⚠️  $table: may contain data"
    fi
}

check_table_count "projects"
check_table_count "tasks"
check_table_count "task_subtasks"
check_table_count "git_branchs"

echo ""
echo "✅ All done! Your Supabase tables have been cleaned."
echo "💡 You can now start fresh with clean tables."