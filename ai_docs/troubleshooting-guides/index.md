# Troubleshooting Guides Index

This directory contains troubleshooting guides for common issues and their resolutions in the 4genthub system.

## Available Guides

### Recently Added
- **[Fix Keycloak Token Integration](./FIX_KEYCLOAK_TOKEN_INTEGRATION.md)** - Keycloak authentication integration troubleshooting

### Critical Fixes
- **[Critical MCP Tools Fixes - 2025-08-30](critical-mcp-tools-fixes-2025-08-30.md)** - Resolution of two critical issues (Fixed by Coding Agent):
  - Subtask User ID Not Null Constraint (`psycopg2.errors.NotNullViolation`) - Fixed parameter filtering issue
  - Context Creation Type Checking Errors (`argument of type 'NoneType' is not iterable`) - Added proper type checks
- **[MCP Testing Issues Comprehensive Results - 2025-08-30](mcp-tools-comprehensive-test-results-2025-08-30.md)** - Comprehensive test results and analysis of MCP tool functionality

## Guide Categories

- **Critical Fixes**: System-breaking issues that prevent core functionality
- **Performance Issues**: Performance degradation and optimization guides  
- **Configuration Problems**: Setup and configuration troubleshooting
- **Integration Issues**: Problems with external systems and APIs
- **Development Issues**: Development environment and debugging guides

## How to Use These Guides

1. **Identify the Issue**: Look for error messages, symptoms, or behavior patterns
2. **Find the Relevant Guide**: Use the index or search for keywords
3. **Follow the Steps**: Each guide provides step-by-step resolution instructions
4. **Verify the Fix**: Test the solution according to the verification steps
5. **Report Results**: Update the guide if you discover additional information

## Contributing

When adding new troubleshooting guides:

1. Use the template format: Problem → Root Cause → Solution → Verification
2. Include relevant file paths and code snippets
3. Document the impact and affected functionality  
4. Provide testing/verification steps
5. Update this index with the new guide

## Emergency Contact

For critical production issues that require immediate attention, escalate through the appropriate channels while documenting the issue for future troubleshooting guides.

---

*Last Updated: 2025-08-30*