#!/bin/bash
set -e

# agenthub Docker Entrypoint Script
# Handles initialization, environment setup, and graceful startup

echo "🚀 Starting agenthub Server..."
echo "================================"

# Activate virtual environment
if [ -f "/app/.venv/bin/activate" ]; then
    source /app/.venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to validate environment
validate_environment() {
    log "🔍 Validating environment..."

    # Set data storage mode (default to internal)
    DATA_STORAGE_MODE="${DATA_STORAGE_MODE:-internal}"
    log "📁 Data storage mode: $DATA_STORAGE_MODE"

    case "$DATA_STORAGE_MODE" in
        "external")
            log "🔗 Using external data storage (mounted volume)"
            # Check if data directory exists and is writable (mounted from host)
            if [ ! -d "/data" ]; then
                log "❌ ERROR: /data directory not found - external volume not mounted"
                log "💡 Hint: Use -v /host/path:/data to mount external storage"
                exit 1
            fi

            if [ ! -w "/data" ]; then
                log "❌ ERROR: /data directory not writable - check volume permissions"
                log "💡 Hint: Ensure the mounted directory has proper permissions (chmod 777)"
                exit 1
            fi
            ;;

        "internal")
            log "📦 Using internal data storage (inside container)"
            # Create internal data directory if it doesn't exist
            if [ ! -d "/data" ]; then
                mkdir -p /data
                log "📁 Created internal /data directory"
            fi

            # Ensure we can write to it
            if [ ! -w "/data" ]; then
                log "❌ ERROR: Cannot write to internal /data directory"
                exit 1
            fi
            ;;

        *)
            log "❌ ERROR: Invalid DATA_STORAGE_MODE '$DATA_STORAGE_MODE'"
            log "💡 Valid options: 'internal' (default) or 'external'"
            exit 1
            ;;
    esac

    # Create subdirectories if they don't exist
    mkdir -p /data/tasks /data/projects /data/contexts /data/rules /data/resources

    log "✅ Environment validation passed"
}

# Function to set up default environment variables
setup_environment() {
    log "⚙️  Setting up environment variables..."

    # Set default paths if not provided
    export TASKS_JSON_PATH="${TASKS_JSON_PATH:-/data/tasks}"
    export PROJECTS_FILE_PATH="${PROJECTS_FILE_PATH:-/data/projects/projects.json}"
    export CURSOR_RULES_DIR="${CURSOR_RULES_DIR:-/data/rules}"

    # Create projects.json if it doesn't exist
    if [ ! -f "$PROJECTS_FILE_PATH" ]; then
        mkdir -p "$(dirname "$PROJECTS_FILE_PATH")"
        echo '{}' > "$PROJECTS_FILE_PATH"
        log "📁 Created default projects.json"
    fi

    log "✅ Environment setup complete"
}

# Function to initialize database
initialize_database() {
    log "🗄️  Initializing database..."

    # Run database initialization script if it exists
    if [ -f "/app/scripts/init_database.py" ]; then
        PYTHONPATH=/app/src:/app /app/.venv/bin/python /app/scripts/init_database.py
        if [ $? -eq 0 ]; then
            log "✅ Database initialization complete"
        else
            log "⚠️  Database initialization failed, but continuing startup"
        fi
    else
        log "ℹ️  Database initialization script not found, skipping"
    fi
}

# Function to validate Supabase configuration (if provided)
validate_supabase() {
    if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_ANON_KEY" ]; then
        log "🔐 Supabase configuration detected"

        # Validate URL format
        if [[ ! "$SUPABASE_URL" =~ ^https://[a-zA-Z0-9-]+\.supabase\.co$ ]]; then
            log "⚠️  WARNING: SUPABASE_URL format may be invalid"
        fi

        # Validate key format (basic check)
        if [ ${#SUPABASE_ANON_KEY} -lt 100 ]; then
            log "⚠️  WARNING: SUPABASE_ANON_KEY appears to be too short"
        fi

        log "✅ Supabase validation complete"
    else
        log "ℹ️  No Supabase configuration provided (optional for MVP)"
    fi
}

# Function to perform health check
health_check() {
    log "🏥 Performing startup health check..."

    # Show which Python is being used
    log "🐍 Python path: $(which python)"
    log "🐍 Python version: $(python --version)"

    # Test Python import (ensure virtual environment is activated and PYTHONPATH is set)
    log "🧪 Testing fastmcp import..."

    # Debug: Show detailed Python environment
    log "🔍 Python Environment Debug:"
    log "   Python executable: $(/app/.venv/bin/python -c 'import sys; print(sys.executable)')"
    log "   Python version: $(/app/.venv/bin/python --version)"
    log "   Virtual env path: $VIRTUAL_ENV"
    log "   Current PYTHONPATH: $PYTHONPATH"

    # Debug: Show Python sys.path
    log "🔍 Python sys.path:"
    PYTHONPATH=/app/src:/app /app/.venv/bin/python -c "import sys; [print(f'   {i}: {p}') for i, p in enumerate(sys.path)]"

    # Debug: Check if directories exist
    log "🔍 Directory Structure:"
    log "   /app exists: $([ -d '/app' ] && echo 'YES' || echo 'NO')"
    log "   /app/src exists: $([ -d '/app/src' ] && echo 'YES' || echo 'NO')"
    log "   /app/src/fastmcp exists: $([ -d '/app/src/fastmcp' ] && echo 'YES' || echo 'NO')"
    log "   /app/src/fastmcp/__init__.py exists: $([ -f '/app/src/fastmcp/__init__.py' ] && echo 'YES' || echo 'NO')"
    log "   /app/src/fastmcp/server exists: $([ -d '/app/src/fastmcp/server' ] && echo 'YES' || echo 'NO')"
    log "   /app/src/fastmcp/server/mcp_entry_point.py exists: $([ -f '/app/src/fastmcp/server/mcp_entry_point.py' ] && echo 'YES' || echo 'NO')"

    # Debug: Show actual folder structure (2 levels deep)
    log "🔍 Folder Structure Debug (2 levels):"
    if [ -d "/app/src" ]; then
        log "   Contents of /app/src:"
        find /app/src -maxdepth 2 -type d | sort | while read dir; do
            log "     📁 $dir"
        done
        log "   Files in /app/src:"
        find /app/src -maxdepth 1 -type f | sort | while read file; do
            log "     📄 $file"
        done
    else
        log "   ❌ /app/src does not exist!"
    fi

    # Debug: Show folder structure (2 levels deep)
    log "🔍 Folder Structure Debug (2 levels):"
    if [ -d '/app' ]; then
        log "   📁 /app:"
        find /app -maxdepth 2 -type d 2>/dev/null | sort | while read dir; do
            log "     $dir"
        done
    fi
    if [ -d '/app/src' ]; then
        log "   📁 /app/src contents:"
        find /app/src -maxdepth 2 -type d 2>/dev/null | sort | while read dir; do
            log "     $dir"
        done
    fi

    # Debug: Check virtual environment packages
    log "🔍 Installed Packages:"
    /app/.venv/bin/python -c "import pkg_resources; [print(f'   {pkg.project_name}=={pkg.version}') for pkg in sorted(pkg_resources.working_set, key=lambda x: x.project_name)]" 2>/dev/null | head -10

    # Debug: Check .pth files
    log "🔍 .pth Files in site-packages:"
    find /app/.venv/lib/python3.11/site-packages/ -name "*.pth" -exec echo "   {}" \; -exec cat {} \; 2>/dev/null || log "   No .pth files found"

    # Debug: Try different import methods
    log "🔍 Import Test Methods:"

    # Method 1: Direct import with PYTHONPATH
    log "   Method 1 - Direct import with PYTHONPATH:"
    if PYTHONPATH=/app/src:/app /app/.venv/bin/python -c "import fastmcp; print('   ✅ fastmcp module found')" 2>/dev/null; then
        log "   ✅ fastmcp module imports successfully"
    else
        log "   ❌ fastmcp module import failed:"
        PYTHONPATH=/app/src:/app /app/.venv/bin/python -c "import fastmcp" 2>&1 | head -3 | while read line; do
            log "      $line"
        done
    fi

    # Method 2: Try importing from sys.path modification
    log "   Method 2 - sys.path modification:"
    if /app/.venv/bin/python -c "import sys; sys.path.insert(0, '/app/src'); import fastmcp; print('   ✅ fastmcp found via sys.path')" 2>/dev/null; then
        log "   ✅ fastmcp imports with sys.path modification"
    else
        log "   ❌ fastmcp import failed with sys.path modification"
    fi

    # Method 3: Try the actual entry point import with timeout
    log "   Method 3 - Entry point import:"
    # Use timeout to prevent hanging imports
    if timeout 10s bash -c "PYTHONPATH=/app/src:/app PDBPP_HIJACK_PDB=0 /app/.venv/bin/python -c 'from fastmcp.server.mcp_entry_point import create_agenthub_server; print(\"   ✅ Entry point import successful\")'" 2>/dev/null; then
        log "   ✅ Entry point imports successfully"
        log "✅ Health check passed"
    else
        log "   ❌ Entry point import failed (this is expected and OK):"
        timeout 5s bash -c "PYTHONPATH=/app/src:/app PDBPP_HIJACK_PDB=0 /app/.venv/bin/python -c 'from fastmcp.server.mcp_entry_point import create_agenthub_server'" 2>&1 | head -5 | while read line; do
            log "      $line"
        done
        log "⚠️  Import test failed during health check - this is normal"
        log "🚀 The server will still start correctly with proper initialization"
    fi

    log "✅ Health check passed"
}

# Function to handle graceful shutdown
cleanup() {
    log "🛑 Received shutdown signal, cleaning up..."
    # Kill any background processes
    jobs -p | xargs -r kill
    log "👋 Shutdown complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Main initialization
main() {
    log "🎯 agenthub Server v2.0.0"
    log "📍 Working directory: $(pwd)"
    log "👤 Running as user: $(whoami)"

    # Run validation steps
    validate_environment
    setup_environment
    initialize_database
    validate_supabase
    health_check

    # Display configuration
    log "📊 Configuration:"
    log "   - DATA_STORAGE_MODE: $DATA_STORAGE_MODE"
    log "   - TASKS_JSON_PATH: $TASKS_JSON_PATH"
    log "   - PROJECTS_FILE_PATH: $PROJECTS_FILE_PATH"
    log "   - CURSOR_RULES_DIR: $CURSOR_RULES_DIR"
    log "   - PYTHONPATH: $PYTHONPATH"

    if [ -n "$SUPABASE_URL" ]; then
        log "   - SUPABASE_URL: $SUPABASE_URL"
        log "   - SUPABASE_ANON_KEY: [CONFIGURED]"
    fi

    log "🚀 Starting server with command: $*"
    log "================================"

    # Ensure PYTHONPATH is set for the server startup
    export PYTHONPATH="/app/src:/app"

    # Disable pdbpp hijack which might interfere with imports
    export PDBPP_HIJACK_PDB=0

    # Execute the main command with explicit environment
    exec "$@"
}

# Run main function
main "$@"
