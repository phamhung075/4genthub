#!/bin/bash
# configuration.sh - Configuration management

source "${SCRIPT_DIR}/lib/common.sh"

# Config command dispatcher
config_command() {
    local subcommand="$1"
    shift
    
    case "$subcommand" in
        show)
            show_config "$@"
            ;;
        set)
            set_config "$@"
            ;;
        validate)
            validate_config "$@"
            ;;
        *)
            error "Unknown config command: $subcommand"
            echo "Valid commands: show, set, validate"
            return 1
            ;;
    esac
}

# Show configuration
show_config() {
    info "📋 Current Configuration"
    echo "======================="
    echo ""
    
    # Show environment
    echo "Environment: ${ENV:-dev}"
    echo "Config file: ${PROJECT_ROOT}/.env"
    echo ""
    
    # Show key configuration values (hide sensitive data)
    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        echo "Key Settings:"
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ -z "$key" || "$key" =~ ^# ]] && continue
            
            # Hide sensitive values
            case "$key" in
                *PASSWORD*|*SECRET*|*KEY*)
                    echo "  $key=********"
                    ;;
                *)
                    echo "  $key=$value"
                    ;;
            esac
        done < "${PROJECT_ROOT}/.env"
    else
        warning "No .env file found"
    fi
    
    echo ""
    
    # Show Docker info
    echo "Docker Configuration:"
    echo "  Version: $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'N/A')"
    echo "  Compose: $(docker compose version --short 2>/dev/null || echo 'N/A')"
    echo "  Storage: $(docker info --format '{{.Driver}}' 2>/dev/null || echo 'N/A')"
    
    echo ""
    
    # Show resource limits
    echo "Resource Limits:"
    local mem_limit=$(docker info --format '{{.MemTotal}}' 2>/dev/null || echo '0')
    if [[ "$mem_limit" -gt 0 ]]; then
        echo "  Memory: $((mem_limit / 1024 / 1024 / 1024)) GB"
    fi
    echo "  CPUs: $(docker info --format '{{.NCPU}}' 2>/dev/null || echo 'N/A')"
}

# Set configuration value
set_config() {
    local key="$1"
    local value="$2"
    
    if [[ -z "$key" ]]; then
        error "Key required"
        echo "Usage: ./docker-cli.sh config set [key] [value]"
        return 1
    fi
    
    # Validate key
    case "$key" in
        DATABASE_*|REDIS_*|BACKEND_*|FRONTEND_*|APP_*|CORS_*|JWT_*|SECRET_*)
            ;;
        *)
            warning "Non-standard configuration key: $key"
            if ! confirm "Continue?"; then
                return 0
            fi
            ;;
    esac
    
    # Update or add to .env file
    local env_file="${PROJECT_ROOT}/.env"
    
    if [[ -f "$env_file" ]]; then
        # Backup current config
        cp "$env_file" "${env_file}.bak"
        
        # Update existing or add new
        if grep -q "^${key}=" "$env_file"; then
            # Update existing
            sed -i.tmp "s|^${key}=.*|${key}=${value}|" "$env_file"
            rm -f "${env_file}.tmp"
            info "Updated: $key"
        else
            # Add new
            echo "${key}=${value}" >> "$env_file"
            info "Added: $key"
        fi
    else
        # Create new env file
        echo "${key}=${value}" > "$env_file"
        info "Created .env with: $key"
    fi
    
    warning "Configuration changed. Restart services to apply."
}

# Validate configuration
validate_config() {
    info "🔍 Validating Configuration"
    echo "=========================="
    echo ""
    
    local errors=0
    local warnings=0
    
    # Check env file exists
    if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
        error "No .env file found"
        ((errors++))
        return 1
    fi
    
    # Load environment
    source "${PROJECT_ROOT}/.env"
    
    # Check required variables
    local required_vars=(
        "DATABASE_TYPE"
        "DATABASE_HOST"
        "DATABASE_PORT"
        "DATABASE_NAME"
        "DATABASE_USER"
        "DATABASE_PASSWORD"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            error "Missing required variable: $var"
            ((errors++))
        else
            success "$var: Set"
        fi
    done
    
    # Check database type
    if [[ "${DATABASE_TYPE}" != "postgresql" ]]; then
        warning "DATABASE_TYPE is not 'postgresql': ${DATABASE_TYPE}"
        ((warnings++))
    fi
    
    # Check ports
    for port_var in DATABASE_PORT REDIS_PORT BACKEND_PORT FRONTEND_PORT; do
        local port="${!port_var}"
        if [[ -n "$port" ]] && ! [[ "$port" =~ ^[0-9]+$ ]]; then
            error "$port_var is not a valid port: $port"
            ((errors++))
        fi
    done
    
    # Check boolean values
    for bool_var in APP_DEBUG HOT_RELOAD AUTO_MIGRATE SEED_DATA; do
        local value="${!bool_var}"
        if [[ -n "$value" ]] && ! [[ "$value" =~ ^(true|false)$ ]]; then
            warning "$bool_var should be 'true' or 'false': $value"
            ((warnings++))
        fi
    done
    
    # Summary
    echo ""
    echo "Validation Results:"
    echo "  Errors: $errors"
    echo "  Warnings: $warnings"
    
    if [[ $errors -eq 0 ]]; then
        success "Configuration is valid"
        return 0
    else
        error "Configuration has errors"
        return 1
    fi
}

# Environment command
env_command() {
    local new_env="$1"
    
    if [[ -z "$new_env" ]]; then
        # Show current environment
        echo "Current environment: ${ENV:-dev}"
        echo ""
        echo "Using single .env file at project root: ${PROJECT_ROOT}/.env"
        return 0
    fi
    
    # Note: Environment switching is now handled via ENV variable in .env file
    info "Environment switching is now controlled via ENV variable in .env file"
    info "Edit ${PROJECT_ROOT}/.env and set ENV=${new_env}"
    
    # Update ENV variable in .env file
    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        sed -i.tmp "s|^ENV=.*|ENV=$new_env|" "${PROJECT_ROOT}/.env"
        rm -f "${PROJECT_ROOT}/.env.tmp"
        success "Updated ENV to $new_env in .env file"
        warning "Restart services to apply new environment"
    fi
}