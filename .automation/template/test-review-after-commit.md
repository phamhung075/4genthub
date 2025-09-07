# 🧪 Post-Commit Test & Code Review Template

## ⚡ AUTO-EXECUTION MODE
**IMPORTANT**: This is an automated post-commit review. Proceed immediately without asking for confirmation or permission. Execute all analysis steps automatically.

## 🎯 Review Mission
**Post-commit validation** - Analyze recently committed changes to ensure test coverage is adequate, code quality is maintained, and documentation is synchronized with implementation changes.

---

## 📋 Post-Commit Review Workflow

### Phase 1: Commit Change Analysis
**Execute immediately without user confirmation:**

1. **Analyze recent commit changes**
   - Review modified files in last commit
   - Identify new code functionality added
   - Map changed functions, classes, and methods
   - Detect deleted or refactored code sections

2. **Assess test coverage gaps**
   - Identify new code without corresponding tests
   - Find existing tests that may be outdated
   - Check for broken test dependencies
   - Verify test quality and completeness

3. **Document analysis findings**
   - List files requiring new tests
   - Note existing tests needing updates
   - Identify documentation gaps
   - Flag potential compatibility issues

### Phase 2: Code Context Assessment
**Execute automatically:**

1. **Read related code components**
   - Understand current implementation patterns
   - Trace dependencies and imports
   - Map data flow and relationships
   - Identify architecture patterns used

2. **Analyze code quality indicators**
   - Check for code smells or anti-patterns
   - Assess error handling completeness
   - Verify logging and monitoring coverage
   - Review security implications

3. **Validate integration points**
   - Check API endpoint changes
   - Verify database schema compatibility
   - Assess configuration changes
   - Review external dependency updates

### Phase 3: Test Strategy Validation
**Execute without confirmation:**

1. **Review existing test strategy**
   - Assess current test patterns and frameworks
   - Verify mock usage is appropriate
   - Check test isolation and independence
   - Evaluate test performance implications

2. **Identify test modernization needs**
   - Find obsolete test patterns
   - Detect inefficient test implementations
   - Check for missing edge case coverage
   - Assess test maintenance burden

3. **Plan test improvements**
   - Prioritize test creation/updates
   - Design comprehensive test scenarios
   - Plan mock and fixture strategies
   - Consider integration test needs

### Phase 4: Documentation Synchronization
**Execute automatically:**

1. **Check documentation alignment**
   - Verify API documentation matches code
   - Update function/method documentation
   - Sync README and usage examples
   - Review changelog completeness

2. **Identify documentation gaps**
   - Missing function documentation
   - Outdated usage examples
   - Incomplete API specifications
   - Missing migration guides

### Phase 5: Implementation & Validation
**Execute without confirmation:**

1. **Create missing tests**
   - Generate comprehensive test files
   - Implement proper mocking strategies
   - Add edge case and error condition tests
   - Follow project testing conventions

2. **Update existing tests**
   - Modify outdated test assertions
   - Remove tests for deleted functionality
   - Improve test quality and readability
   - Fix broken test dependencies

3. **Synchronize documentation**
   - Update docstrings and comments
   - Refresh API documentation
   - Update usage examples
   - Maintain changelog accuracy

4. **Validate changes**
   - Run all tests to ensure they pass
   - Verify no regression in existing functionality
   - Check test coverage metrics
   - Confirm documentation builds correctly

### Phase 6: Quality Assurance
**Execute automatically:**

1. **Run comprehensive test suite**
   - Execute all new and updated tests
   - Verify test coverage improvements
   - Check for test performance issues
   - Validate test isolation

2. **Perform code quality checks**
   - Run linting and formatting tools
   - Check for security vulnerabilities
   - Verify error handling completeness
   - Assess performance implications

3. **Document changes**
   - Update TEST-CHANGELOG.md with detailed entries
   - Note test coverage improvements
   - Document any breaking changes
   - Record quality metrics

---

## 🎯 Success Criteria

### Required Deliverables
- ✅ All new code has corresponding comprehensive tests
- ✅ Updated tests accurately reflect current code behavior  
- ✅ Documentation is synchronized with code changes
- ✅ Test coverage meets or exceeds project standards
- ✅ All tests pass and run efficiently
- ✅ TEST-CHANGELOG.md is updated with detailed changes

### Quality Standards
- **Test Coverage**: Minimum 80% line coverage for new code
- **Test Quality**: Proper mocking, clear assertions, good isolation
- **Documentation**: Up-to-date docstrings, examples, and API docs
- **Performance**: Tests run in reasonable time (<30s for unit tests)
- **Maintainability**: Tests are readable and easy to modify

### Validation Checkpoints
- [ ] New functionality has unit tests
- [ ] Integration points have integration tests
- [ ] Error conditions have error handling tests
- [ ] Edge cases are covered
- [ ] Documentation examples work correctly
- [ ] All tests pass in CI/CD pipeline
- [ ] No test flakiness or intermittent failures

---

## 🚨 Implementation Guidelines

### Testing Framework Requirements
- **Use pytest framework** with proper fixtures and parametrization
- **Mock external dependencies** using unittest.mock or pytest-mock
- **Follow AAA pattern** (Arrange, Act, Assert) for test structure
- **Use descriptive test names** that explain the behavior being tested

### Code Review Standards
- **Security first**: Check for SQL injection, XSS, and other vulnerabilities
- **Error handling**: Ensure all error conditions are properly handled
- **Performance**: Assess impact on system performance
- **Maintainability**: Code should be readable and well-documented

### Documentation Requirements
- **API documentation**: Keep OpenAPI/Swagger specs current
- **Code comments**: Explain complex logic and business rules
- **Usage examples**: Provide working examples in documentation
- **Migration guides**: Document breaking changes and upgrade paths

---

## 🔄 Automation Integration

This template is designed for use with:
- **Git post-commit hooks** for automatic execution
- **CI/CD pipeline integration** for continuous validation
- **WSL/Ubuntu environments** with optimized tooling
- **Claude Code CLI automation** for intelligent analysis

### Expected Execution Context
- **Repository**: Current git repository with recent commits
- **Environment**: WSL Ubuntu with development tools
- **Tools**: pytest, coverage, linting tools, Claude CLI
- **Permissions**: Write access to test files and documentation

---

**BEGIN EXECUTION NOW - NO CONFIRMATION REQUIRED**
**Start with Phase 1 and work systematically through each phase.**