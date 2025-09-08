#!/bin/bash
# Docker Configuration Validation Script
# DhafnckMCP Project - Validate and optimize Docker configurations

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
DOCKER_DIR="$PROJECT_ROOT/docker-system"
REPORT_FILE="$PROJECT_ROOT/docker-validation-report.txt"

echo -e "${CYAN}${BOLD}🐳 DhafnckMCP Docker Configuration Validation${RESET}"
echo -e "${CYAN}${BOLD}===========================================${RESET}"
echo ""

# Function to check if docker is available
check_docker() {
    echo -e "${YELLOW}🔍 Checking Docker availability...${RESET}"
    
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}  ❌ Docker is not installed${RESET}"
        return 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}  ❌ Docker daemon is not running${RESET}"
        return 1
    fi
    
    echo -e "${GREEN}  ✅ Docker is available and running${RESET}"
    
    if command -v docker-compose >/dev/null 2>&1; then
        echo -e "${GREEN}  ✅ docker-compose is available${RESET}"
        COMPOSE_CMD="docker-compose"
    elif docker compose version >/dev/null 2>&1; then
        echo -e "${GREEN}  ✅ docker compose (plugin) is available${RESET}"
        COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}  ❌ Neither docker-compose nor docker compose plugin found${RESET}"
        return 1
    fi
    
    echo ""
    return 0
}

# Function to discover docker-compose files
discover_compose_files() {
    echo -e "${YELLOW}🔍 Discovering Docker Compose configurations...${RESET}"
    
    # Find all docker-compose files in the project
    local compose_files=()
    while IFS= read -r -d '' file; do
        compose_files+=("$file")
    done < <(find "$PROJECT_ROOT" -name "docker-compose*.yml" -o -name "docker-compose*.yaml" -not -path "*/node_modules/*" -not -path "*/.git/*" -print0)
    
    echo "  📊 Found ${#compose_files[@]} Docker Compose files:"
    
    for file in "${compose_files[@]}"; do
        local rel_path=$(realpath --relative-to="$PROJECT_ROOT" "$file")
        local size=$(stat -c%s "$file" 2>/dev/null || echo "0")
        echo "    • $rel_path ($size bytes)"
    done
    
    echo ""
    
    # Store for later use
    printf '%s\n' "${compose_files[@]}" > /tmp/dhafnck_compose_files.txt
}

# Function to validate individual compose files
validate_compose_files() {
    echo -e "${YELLOW}🔍 Validating Docker Compose file syntax...${RESET}"
    
    local validation_errors=0
    local validation_warnings=0
    
    while IFS= read -r file; do
        if [ -z "$file" ]; then continue; fi
        
        local rel_path=$(realpath --relative-to="$PROJECT_ROOT" "$file")
        echo "  • Validating $rel_path..."
        
        cd "$(dirname "$file")"
        local filename=$(basename "$file")
        
        # Test syntax validation
        if $COMPOSE_CMD -f "$filename" config >/dev/null 2>/dev/null; then
            echo -e "${GREEN}    ✅ Syntax is valid${RESET}"
            
            # Check for common issues
            local warnings=()
            
            # Check for missing environment files
            if grep -q "env_file:" "$filename"; then
                local env_files=$(grep -A5 "env_file:" "$filename" | grep -E "^\s*-" | sed 's/^\s*-\s*//' || true)
                while IFS= read -r env_file; do
                    if [ -n "$env_file" ] && [ ! -f "$env_file" ]; then
                        warnings+=("Missing env_file: $env_file")
                    fi
                done <<< "$env_files"
            fi
            
            # Check for hardcoded credentials
            if grep -qE "(password|secret|key).*:.*['\"][^'\"]*['\"]" "$filename"; then
                warnings+=("Potential hardcoded credentials found")
            fi
            
            # Check for missing volumes
            if grep -q "volumes:" "$filename"; then
                local named_volumes=$(grep -E "^\s+[a-zA-Z].*:$" "$filename" | sed 's/:\s*$//' | tr -d ' ' || true)
                while IFS= read -r volume; do
                    if [ -n "$volume" ] && ! grep -q "^volumes:" "$filename"; then
                        warnings+=("Named volume '$volume' not declared in volumes section")
                    fi
                done <<< "$named_volumes"
            fi
            
            # Display warnings
            if [ ${#warnings[@]} -gt 0 ]; then
                validation_warnings=$((validation_warnings + 1))
                echo -e "${YELLOW}    ⚠️  Warnings (${#warnings[@]}):${RESET}"
                for warning in "${warnings[@]}"; do
                    echo "      - $warning"
                done
            fi
        else
            validation_errors=$((validation_errors + 1))
            echo -e "${RED}    ❌ Syntax validation failed${RESET}"
            echo "    Error details:"
            $COMPOSE_CMD -f "$filename" config 2>&1 | head -5 | sed 's/^/      /'
        fi
        
        cd "$PROJECT_ROOT"
    done < /tmp/dhafnck_compose_files.txt
    
    echo ""
    
    if [ "$validation_errors" -gt 0 ]; then
        echo -e "${RED}❌ Found $validation_errors compose files with syntax errors${RESET}"
        return 1
    elif [ "$validation_warnings" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found $validation_warnings compose files with warnings${RESET}"
        return 2
    else
        echo -e "${GREEN}✅ All compose files have valid syntax${RESET}"
        return 0
    fi
}

# Function to analyze docker-menu.sh integration
analyze_docker_menu_integration() {
    echo -e "${YELLOW}🔍 Analyzing docker-menu.sh integration...${RESET}"
    
    local docker_menu="$DOCKER_DIR/docker-menu.sh"
    
    if [ ! -f "$docker_menu" ]; then
        echo -e "${RED}  ❌ docker-menu.sh not found at $docker_menu${RESET}"
        return 1
    fi
    
    echo "  • Analyzing compose file usage in docker-menu.sh..."
    
    # Find referenced compose files
    local referenced_files=()
    while IFS= read -r line; do
        if [[ "$line" =~ docker-compose.*-f[[:space:]]+([^[:space:]]+) ]]; then
            referenced_files+=("${BASH_REMATCH[1]}")
        fi
    done < "$docker_menu"
    
    echo "  📋 Referenced compose files in docker-menu.sh:"
    if [ ${#referenced_files[@]} -eq 0 ]; then
        echo -e "${YELLOW}    ⚠️  No explicit -f references found${RESET}"
    else
        for ref in "${referenced_files[@]}"; do
            echo "    • $ref"
        done
    fi
    
    # Check for unused compose files
    echo ""
    echo "  🔍 Checking for unused compose files..."
    local unused_files=()
    
    while IFS= read -r file; do
        if [ -z "$file" ]; then continue; fi
        
        local filename=$(basename "$file")
        local rel_path=$(realpath --relative-to="$DOCKER_DIR" "$file" 2>/dev/null || echo "$file")
        
        if ! grep -q "$filename" "$docker_menu"; then
            unused_files+=("$rel_path")
        fi
    done < /tmp/dhafnck_compose_files.txt
    
    if [ ${#unused_files[@]} -gt 0 ]; then
        echo -e "${YELLOW}  ⚠️  Potentially unused compose files:${RESET}"
        for unused in "${unused_files[@]}"; do
            echo "    • $unused"
        done
    else
        echo -e "${GREEN}  ✅ All compose files appear to be used${RESET}"
    fi
    
    # Check environment file loading
    echo ""
    echo "  🔍 Checking environment file integration..."
    if grep -q "\.env\.dev" "$docker_menu"; then
        echo -e "${GREEN}  ✅ docker-menu.sh loads .env.dev${RESET}"
    else
        echo -e "${YELLOW}  ⚠️  docker-menu.sh may not load .env.dev${RESET}"
    fi
    
    if grep -q "env_file.*\.env" "$docker_menu" || grep -q "\-\-env-file" "$docker_menu"; then
        echo -e "${GREEN}  ✅ docker-menu.sh passes environment to compose${RESET}"
    else
        echo -e "${YELLOW}  ⚠️  docker-menu.sh may not pass environment files${RESET}"
    fi
    
    echo ""
}

# Function to test docker-compose configurations
test_compose_configs() {
    echo -e "${YELLOW}🧪 Testing Docker Compose configurations...${RESET}"
    
    local test_results=()
    
    # Test with current environment
    cd "$DOCKER_DIR"
    
    # Load environment if available
    if [ -f "$PROJECT_ROOT/.env.dev" ]; then
        echo "  • Loading .env.dev for testing..."
        set -a
        source "$PROJECT_ROOT/.env.dev" >/dev/null 2>&1 || true
        set +a
    elif [ -f "$PROJECT_ROOT/.env" ]; then
        echo "  • Loading .env for testing..."
        set -a
        source "$PROJECT_ROOT/.env" >/dev/null 2>&1 || true
        set +a
    fi
    
    # Test main compose files referenced by docker-menu.sh
    local main_configs=(
        "docker-compose.yml"
        "docker-compose.dev.yml"
        "docker-compose.production.yml"
        "docker-compose.keycloak.yml"
        "docker-compose.pgadmin.yml"
    )
    
    for config in "${main_configs[@]}"; do
        if [ -f "$config" ]; then
            echo "  • Testing $config..."
            
            if $COMPOSE_CMD -f "$config" config >/dev/null 2>&1; then
                echo -e "${GREEN}    ✅ $config processes successfully${RESET}"
                test_results+=("$config: PASS")
            else
                echo -e "${RED}    ❌ $config has processing errors${RESET}"
                $COMPOSE_CMD -f "$config" config 2>&1 | head -3 | sed 's/^/      /'
                test_results+=("$config: FAIL")
            fi
        else
            echo -e "${CYAN}    ℹ️  $config not found (optional)${RESET}"
            test_results+=("$config: NOT_FOUND")
        fi
    done
    
    # Test optimized configuration if it exists
    if [ -f "docker/docker-compose.optimized.yml" ]; then
        echo "  • Testing optimized configuration..."
        cd docker
        if $COMPOSE_CMD -f "docker-compose.optimized.yml" config >/dev/null 2>&1; then
            echo -e "${GREEN}    ✅ Optimized config processes successfully${RESET}"
        else
            echo -e "${YELLOW}    ⚠️  Optimized config needs regeneration${RESET}"
        fi
        cd ..
    fi
    
    echo ""
    
    # Summary
    local pass_count=$(printf '%s\n' "${test_results[@]}" | grep -c ": PASS" || echo "0")
    local fail_count=$(printf '%s\n' "${test_results[@]}" | grep -c ": FAIL" || echo "0")
    
    echo "  📊 Test Summary: $pass_count passed, $fail_count failed"
    
    if [ "$fail_count" -gt 0 ]; then
        return 1
    else
        return 0
    fi
}

# Function to check for configuration conflicts
check_configuration_conflicts() {
    echo -e "${YELLOW}🔍 Checking for configuration conflicts...${RESET}"
    
    local conflicts=0
    
    # Check for port conflicts
    echo "  • Checking for port conflicts..."
    local used_ports=()
    
    while IFS= read -r file; do
        if [ -z "$file" ]; then continue; fi
        
        local ports=$(grep -E "^\s*-\s*[\"']?[0-9]+:[0-9]+[\"']?" "$file" | sed -E 's/.*-[[:space:]]*[\"'"'"']?([0-9]+):[0-9]+[\"'"'"']?.*/\1/' || true)
        while IFS= read -r port; do
            if [ -n "$port" ]; then
                used_ports+=("$port")
            fi
        done <<< "$ports"
    done < /tmp/dhafnck_compose_files.txt
    
    # Find duplicate ports
    local duplicate_ports=($(printf '%s\n' "${used_ports[@]}" | sort | uniq -d))
    if [ ${#duplicate_ports[@]} -gt 0 ]; then
        conflicts=$((conflicts + 1))
        echo -e "${RED}    ❌ Duplicate ports found: ${duplicate_ports[*]}${RESET}"
    else
        echo -e "${GREEN}    ✅ No port conflicts found${RESET}"
    fi
    
    # Check for service name conflicts
    echo "  • Checking for service name conflicts..."
    local service_names=()
    
    while IFS= read -r file; do
        if [ -z "$file" ]; then continue; fi
        
        local services=$(grep -E "^\s+[a-zA-Z][^:]*:" "$file" | sed -E 's/^\s+([^:]+):.*/\1/' || true)
        while IFS= read -r service; do
            if [ -n "$service" ] && [ "$service" != "services" ] && [ "$service" != "volumes" ] && [ "$service" != "networks" ]; then
                service_names+=("$service")
            fi
        done <<< "$services"
    done < /tmp/dhafnck_compose_files.txt
    
    local duplicate_services=($(printf '%s\n' "${service_names[@]}" | sort | uniq -d))
    if [ ${#duplicate_services[@]} -gt 0 ]; then
        echo -e "${YELLOW}    ⚠️  Duplicate service names (may be intentional): ${duplicate_services[*]}${RESET}"
    else
        echo -e "${GREEN}    ✅ No service name conflicts found${RESET}"
    fi
    
    echo ""
    return $conflicts
}

# Function to generate optimization recommendations
generate_recommendations() {
    echo -e "${YELLOW}💡 Generating optimization recommendations...${RESET}"
    
    local recommendations=()
    
    # Analyze file count and complexity
    local compose_count=$(wc -l < /tmp/dhafnck_compose_files.txt)
    if [ "$compose_count" -gt 5 ]; then
        recommendations+=("Consider consolidating similar compose files to reduce maintenance overhead")
    fi
    
    # Check for unused files
    local docker_menu="$DOCKER_DIR/docker-menu.sh"
    local unused_count=0
    
    while IFS= read -r file; do
        if [ -z "$file" ]; then continue; fi
        local filename=$(basename "$file")
        if ! grep -q "$filename" "$docker_menu" 2>/dev/null; then
            unused_count=$((unused_count + 1))
        fi
    done < /tmp/dhafnck_compose_files.txt
    
    if [ "$unused_count" -gt 0 ]; then
        recommendations+=("Remove or document $unused_count potentially unused compose files")
    fi
    
    # Check for environment file consistency
    if [ -f "$PROJECT_ROOT/.env.dev" ] && [ -f "$PROJECT_ROOT/.env" ]; then
        recommendations+=("Consider using only .env.dev for development to avoid confusion")
    fi
    
    # Docker-specific recommendations
    recommendations+=("Ensure all compose files use consistent volume naming")
    recommendations+=("Consider using Docker Buildkit for improved build performance")
    recommendations+=("Add health checks to critical services")
    recommendations+=("Use multi-stage builds to reduce image sizes")
    
    echo "  📝 Optimization Recommendations:"
    local i=1
    for rec in "${recommendations[@]}"; do
        echo "    $i. $rec"
        i=$((i + 1))
    done
    
    echo ""
}

# Function to generate comprehensive validation report
generate_validation_report() {
    echo -e "${YELLOW}📄 Generating comprehensive validation report...${RESET}"
    
    cat > "$REPORT_FILE" << EOF
DhafnckMCP Docker Configuration Validation Report
===============================================
Date: $(date)
Docker Version: $(docker --version 2>/dev/null || echo "Not available")
Compose Version: $(docker-compose --version 2>/dev/null || docker compose version 2>/dev/null || echo "Not available")

Configuration Analysis:
- Total compose files: $(wc -l < /tmp/dhafnck_compose_files.txt)
- Docker-menu.sh integration: $([ -f "$DOCKER_DIR/docker-menu.sh" ] && echo "Present" || echo "Missing")
- Environment files: $(find "$PROJECT_ROOT" -name ".env*" -not -path "*/node_modules/*" -not -path "*/.git/*" | wc -l)

Compose Files Found:
$(cat /tmp/dhafnck_compose_files.txt | while read -r file; do
    if [ -n "$file" ]; then
        echo "  - $(realpath --relative-to="$PROJECT_ROOT" "$file")"
    fi
done)

Docker-menu.sh Integration:
$(if [ -f "$DOCKER_DIR/docker-menu.sh" ]; then
    echo "  - Script location: $DOCKER_DIR/docker-menu.sh"
    echo "  - Uses .env.dev: $(grep -q "\.env\.dev" "$DOCKER_DIR/docker-menu.sh" && echo "Yes" || echo "No")"
    echo "  - Environment passing: $(grep -q "\-\-env-file" "$DOCKER_DIR/docker-menu.sh" && echo "Yes" || echo "No")"
else
    echo "  - docker-menu.sh not found"
fi)

Validation Summary:
✅ Actions Performed:
  - Docker availability check
  - Compose file discovery
  - Syntax validation
  - Integration analysis  
  - Configuration testing
  - Conflict detection
  - Recommendation generation

Next Steps:
1. Address any validation errors found
2. Consider optimization recommendations
3. Test all configurations with docker-menu.sh
4. Update documentation as needed
5. Remove this report after issues are resolved

Troubleshooting:
- If services fail to start, check environment variables
- If builds fail, try docker system prune and rebuild
- If ports conflict, check for running containers
- For permission issues, check Docker daemon status
EOF
    
    echo -e "${GREEN}  ✅ Report saved to: $REPORT_FILE${RESET}"
}

# Main execution function
main() {
    echo -e "${CYAN}Starting Docker configuration validation...${RESET}"
    echo ""
    
    local exit_code=0
    
    # Step 1: Check Docker availability
    if ! check_docker; then
        echo -e "${RED}❌ Docker is not available - cannot continue${RESET}"
        exit 1
    fi
    
    # Step 2: Discover compose files
    discover_compose_files
    
    # Step 3: Validate compose files
    if ! validate_compose_files; then
        case $? in
            1) echo -e "${RED}❌ Critical validation errors found${RESET}"; exit_code=1 ;;
            2) echo -e "${YELLOW}⚠️  Validation warnings found${RESET}" ;;
        esac
    fi
    
    # Step 4: Analyze docker-menu.sh integration
    analyze_docker_menu_integration
    
    # Step 5: Test configurations
    if ! test_compose_configs; then
        echo -e "${RED}❌ Configuration testing failed${RESET}"
        exit_code=1
    fi
    
    # Step 6: Check for conflicts
    if ! check_configuration_conflicts; then
        echo -e "${YELLOW}⚠️  Configuration conflicts detected${RESET}"
    fi
    
    # Step 7: Generate recommendations
    generate_recommendations
    
    # Step 8: Generate report
    generate_validation_report
    
    # Cleanup
    rm -f /tmp/dhafnck_compose_files.txt
    
    echo -e "${GREEN}${BOLD}✅ Docker Configuration Validation Complete!${RESET}"
    echo ""
    echo -e "${CYAN}📋 Summary:${RESET}"
    echo "  • Compose files analyzed: $(wc -l < "$REPORT_FILE" | grep -o '[0-9]*' | head -1 || echo "Unknown")"
    echo "  • Docker-menu.sh integration: Analyzed"
    echo "  • Configuration conflicts: Checked"
    echo "  • Report location: $REPORT_FILE"
    
    if [ "$exit_code" -eq 0 ]; then
        echo -e "${GREEN}  • Overall status: PASSED${RESET}"
    else
        echo -e "${YELLOW}  • Overall status: NEEDS ATTENTION${RESET}"
    fi
    
    echo ""
    echo -e "${YELLOW}📝 Next Steps:${RESET}"
    echo "  1. Review validation report: cat $REPORT_FILE"
    echo "  2. Address any critical issues found"
    echo "  3. Test configurations: ./docker-system/docker-menu.sh"
    echo "  4. Implement optimization recommendations"
    echo ""
    
    if [ "$exit_code" -eq 0 ]; then
        echo -e "${GREEN}🎉 Docker configurations are ready for use!${RESET}"
    else
        echo -e "${YELLOW}⚠️  Please address the issues found before production use${RESET}"
    fi
    
    exit $exit_code
}

# Verify we're in the right directory
if [ ! -f "$PROJECT_ROOT/CLAUDE.md" ]; then
    echo -e "${RED}❌ Error: This doesn't appear to be the DhafnckMCP project root${RESET}"
    echo "Expected to find CLAUDE.md in: $PROJECT_ROOT"
    exit 1
fi

# Run main function
main "$@"