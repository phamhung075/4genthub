# Makefile for Docker CLI System

# Variables
SHELL := /bin/bash
.DEFAULT_GOAL := help

# Directories
TEST_DIR := test
LIB_DIR := lib
DOCKER_DIR := docker

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
BLUE := \033[0;34m
YELLOW := \033[1;33m
NC := \033[0m

.PHONY: help test test-unit test-integration test-verbose test-coverage \
        clean install lint check validate permissions

## help: Show this help message
help:
	@echo -e "$(BLUE)Docker CLI System - Makefile$(NC)"
	@echo -e "$(BLUE)=============================$(NC)"
	@echo ""
	@echo "Available targets:"
	@grep -E '^##' $(MAKEFILE_LIST) | sed -e 's/## //'
	@echo ""

## test: Run all tests
test: permissions
	@echo -e "$(BLUE)Running all tests...$(NC)"
	@bash $(TEST_DIR)/run_all_tests.sh
	@$(MAKE) clean-test-artifacts

## test-unit: Run unit tests only
test-unit: permissions
	@echo -e "$(BLUE)Running unit tests...$(NC)"
	@for test in $(TEST_DIR)/test_core_*.sh $(TEST_DIR)/test_database_*.sh; do \
		if [[ -f "$$test" ]]; then \
			bash "$$test" || exit 1; \
		fi; \
	done

## test-integration: Run integration tests only
test-integration: permissions
	@echo -e "$(BLUE)Running integration tests...$(NC)"
	@for test in $(TEST_DIR)/test_development_*.sh $(TEST_DIR)/test_workflows_*.sh; do \
		if [[ -f "$$test" ]]; then \
			bash "$$test" || exit 1; \
		fi; \
	done

## test-verbose: Run tests with verbose output
test-verbose: permissions
	@echo -e "$(BLUE)Running tests with verbose output...$(NC)"
	@VERBOSE=1 bash $(TEST_DIR)/run_all_tests.sh

## test-coverage: Run tests and generate coverage report
test-coverage: permissions
	@echo -e "$(BLUE)Running tests with coverage...$(NC)"
	@echo -e "$(YELLOW)Note: Coverage analysis requires additional tooling$(NC)"
	@bash $(TEST_DIR)/run_all_tests.sh

## validate: Validate all shell scripts
validate:
	@echo -e "$(BLUE)Validating shell scripts...$(NC)"
	@for script in docker-cli.sh docker-menu.sh $(LIB_DIR)/*.sh $(TEST_DIR)/*.sh; do \
		if [[ -f "$$script" ]]; then \
			echo -n "Checking $$script... "; \
			if bash -n "$$script" 2>/dev/null; then \
				echo -e "$(GREEN)OK$(NC)"; \
			else \
				echo -e "$(RED)FAILED$(NC)"; \
				bash -n "$$script"; \
				exit 1; \
			fi; \
		fi; \
	done

## lint: Run shellcheck on all scripts
lint:
	@echo -e "$(BLUE)Running shellcheck...$(NC)"
	@if command -v shellcheck &> /dev/null; then \
		shellcheck -x docker-cli.sh docker-menu.sh $(LIB_DIR)/*.sh || true; \
	else \
		echo -e "$(YELLOW)shellcheck not installed. Install with: apt-get install shellcheck$(NC)"; \
	fi

## check: Run validation and linting
check: validate lint

## permissions: Fix file permissions
permissions:
	@echo -e "$(BLUE)Setting correct permissions...$(NC)"
	@chmod +x docker-cli.sh docker-menu.sh docker-menu.py 2>/dev/null || true
	@chmod +x $(TEST_DIR)/*.sh 2>/dev/null || true
	@chmod +x $(LIB_DIR)/*.sh 2>/dev/null || true
	@echo -e "$(GREEN)Permissions updated$(NC)"

## clean: Clean all test artifacts and temporary files
clean: clean-test-artifacts
	@echo -e "$(BLUE)Cleaning additional artifacts...$(NC)"
	@rm -f $(TEST_DIR)/*.log
	@rm -f .coverage
	@rm -rf test-temp test-dir concurrent-test test-perf test-artifacts
	@rm -f test-output.log test-file.txt .test-config
	@echo -e "$(GREEN)All cleaned$(NC)"

## clean-test-artifacts: Clean test-generated files
clean-test-artifacts:
	@echo -e "$(BLUE)Cleaning test artifacts...$(NC)"
	@rm -rf /tmp/docker-cli-test-mocks
	@rm -rf test-temp test-dir concurrent-test test-perf test-artifacts 2>/dev/null || true
	@rm -f test-output.log test-file.txt .test-config 2>/dev/null || true
	@rm -rf backups 2>/dev/null || true
	@rm -rf test-restricted 2>/dev/null || true
	@find . -name "*.calls" -delete 2>/dev/null || true
	@echo -e "$(GREEN)Test artifacts cleaned$(NC)"

## install: Install test dependencies
install:
	@echo -e "$(BLUE)Installing test dependencies...$(NC)"
	@if ! command -v jq &> /dev/null; then \
		echo -e "$(YELLOW)Installing jq...$(NC)"; \
		sudo apt-get update && sudo apt-get install -y jq; \
	fi
	@if ! command -v shellcheck &> /dev/null; then \
		echo -e "$(YELLOW)Installing shellcheck...$(NC)"; \
		sudo apt-get install -y shellcheck; \
	fi
	@echo -e "$(GREEN)Dependencies installed$(NC)"

## test-specific: Run a specific test file
test-specific:
	@if [[ -z "$(TEST_FILE)" ]]; then \
		echo -e "$(RED)Error: TEST_FILE not specified$(NC)"; \
		echo "Usage: make test-specific TEST_FILE=test_core_commands.sh"; \
		exit 1; \
	fi
	@echo -e "$(BLUE)Running $(TEST_FILE)...$(NC)"
	@bash $(TEST_DIR)/$(TEST_FILE)

## test-quick: Run quick smoke tests
test-quick: permissions
	@echo -e "$(BLUE)Running quick smoke tests...$(NC)"
	@bash $(TEST_DIR)/test_core_commands.sh

# Development helpers
.PHONY: dev-test dev-watch

## dev-test: Run tests in development mode
dev-test:
	@DOCKER_CLI_TEST_MODE=true DEBUG=1 make test

## dev-watch: Watch for changes and run tests
dev-watch:
	@echo -e "$(BLUE)Watching for changes...$(NC)"
	@while true; do \
		inotifywait -q -e modify,create,delete -r $(LIB_DIR) $(TEST_DIR) docker-cli.sh; \
		clear; \
		make test-quick; \
	done