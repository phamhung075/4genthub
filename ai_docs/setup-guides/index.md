# Setup Guides Index

## Recently Added Guides

- [Database UI Guide](./DATABASE_UI_GUIDE.md) - Database management and UI tools setup
- [Production Setup Summary](./PRODUCTION_SETUP_SUMMARY.md) - Quick production deployment overview

## Production Setup

### [PostgreSQL Docker + Keycloak Cloud Production Setup](./POSTGRESQL_KEYCLOAK_PRODUCTION.md)
**Recommended for Production** - Clean architecture using PostgreSQL Docker for database and Keycloak Cloud for authentication. No backward compatibility code.

- PostgreSQL Docker container management
- Keycloak cloud integration
- JWT token authentication
- Complete security configuration
- Performance optimization

## Quick Start Scripts

### Setup Automation
- `setup-postgres-keycloak.py` - Automated setup for PostgreSQL + Keycloak
- `test-mcp-keycloak-auth.py` - Complete authentication test suite

### Configuration Files
- `.env.example` - Environment template with all configuration options
- `docker-compose.yml` - Docker services configuration

## Authentication Configurations

### Keycloak Setup
- Realm configuration
- Client setup with secret
- Role management
- User creation
- Token validation

### PostgreSQL Docker
- Container initialization
- Database migrations
- Backup and restore
- Performance tuning
- Connection pooling

## Testing & Validation

### Authentication Testing
1. Keycloak connectivity test
2. Token generation and validation
3. MCP protected endpoint access
4. Token refresh flow
5. MCP tool authentication

### Database Testing
1. Connection validation
2. Schema verification
3. Migration status
4. Performance benchmarks

## Troubleshooting

Common issues and solutions:
- PostgreSQL connection failures
- Keycloak authentication errors
- JWT token validation issues
- Docker container problems
- Migration failures

## Security Best Practices

- Environment variable management
- Password policies
- SSL/TLS configuration
- Token lifecycle management
- Audit logging

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/ai_docs/)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Docker Documentation](https://ai_docs.docker.com/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)