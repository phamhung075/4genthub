# Integration Testing and Validation

## Task: Create Comprehensive Integration Tests

### Objective
Create integration tests to ensure the ORM migration works correctly with both SQLite and PostgreSQL.

### Files to Create

1. **Create**: `/tests/integration/test_database_switching.py`
   - Test that DATABASE_TYPE correctly switches implementations
   - Verify both databases work with same code

2. **Create**: `/tests/integration/test_orm_relationships.py`
   - Test all model relationships work correctly
   - Verify cascading deletes
   - Check foreign key constraints

3. **Create**: `/tests/integration/test_json_fields.py`
   - Test JSON field storage and retrieval
   - Verify compatibility between SQLite and PostgreSQL JSON handling

4. **Create**: `/scripts/validate_migration.py`
   - Script to validate all tables exist
   - Check data integrity
   - Compare schema between SQLite and PostgreSQL

### Test Scenarios
1. **Database Switching**
   - Set DATABASE_TYPE=sqlite, verify SQLite is used
   - Set DATABASE_TYPE=postgresql, verify PostgreSQL is used
   - Test fallback behavior

2. **Data Migration**
   - Create data in SQLite
   - Run migration to PostgreSQL
   - Verify all data transferred correctly

3. **Performance Comparison**
   - Basic CRUD operations
   - Complex queries with joins
   - JSON field operations

4. **Error Handling**
   - Database connection failures
   - Invalid data types
   - Constraint violations

### Validation Checklist
- [ ] All repositories work with both databases
- [ ] No data loss during migration
- [ ] Performance is acceptable
- [ ] Error messages are appropriate
- [ ] Backward compatibility maintained