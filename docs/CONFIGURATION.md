# Configuration Structure

## Overview

The backend uses Spring Boot's profile mechanism to manage different environment configurations.

## Profile Structure

```
application.yml              # Base configuration (shared)
├── application-local.yml    # Local development
├── application-dev.yml      # Docker/K8s development
└── application-prod.yml     # Production
```

## Profile Activation

| Profile | Activation | Use Case |
|---------|------------|----------|
| `local` | Default (no flag) | Local IDE development |
| `dev` | `SPRING_PROFILES_ACTIVE=dev` | Docker/K8s dev environment |
| `prod` | `SPRING_PROFILES_ACTIVE=prod` | Production deployment |

## Configuration Priority

Higher priority overrides lower:

1. Command line arguments (highest)
2. Environment variables
3. Profile-specific YAML (`application-{profile}.yml`)
4. Base YAML (`application.yml`)
5. Default values in code (lowest)

## Environment Variables

All sensitive configurations MUST be provided via environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `DB_HOST` | Database host | Yes |
| `DB_PORT` | Database port | No (default: 3306) |
| `DB_NAME` | Database name | Yes |
| `DB_USERNAME` | Database username | Yes |
| `DB_PASSWORD` | Database password | **Yes** |
| `REDIS_HOST` | Redis host | Yes |
| `REDIS_PORT` | Redis port | No (default: 6379) |
| `REDIS_PASSWORD` | Redis password | No |
| `JWT_SECRET` | JWT signing key | **Yes (Production)** |
| `SPRING_PROFILES_ACTIVE` | Active profile | No (default: local) |

## Profile Inheritance

Each profile inherits from `application.yml` and overrides specific values.

### application.yml (Base)
- MyBatis Plus configuration
- JWT configuration (defaults)
- File upload configuration
- Logging pattern

### application-local.yml (Local Development)
- Local MySQL connection (localhost)
- Local Redis connection
- Debug logging

### application-dev.yml (Development)
- Docker/K8s MySQL connection (service name)
- Docker/K8s Redis connection
- Debug logging

### application-prod.yml (Production)
- Cloud database connection
- Production Redis
- Info-level logging
- TLS enabled for database

## Best Practices

### DO

✅ Use environment variables for all secrets
✅ Use profile-specific files for environment differences
✅ Keep sensitive values out of YAML files
✅ Use default values for non-sensitive configurations

### DON'T

❌ Don't hardcode passwords in YAML files
❌ Don't commit real credentials to version control
❌ Don't use weak JWT secrets in production
❌ Don't expose detailed error messages in production

## Example: Running with Different Profiles

```bash
# Local development (default)
java -jar backend.jar

# Development environment (Docker/K8s)
SPRING_PROFILES_ACTIVE=dev java -jar backend.jar

# Production environment
SPRING_PROFILES_ACTIVE=prod \
  DB_HOST=mydb.cloud.com \
  DB_PASSWORD=secure_password \
  JWT_SECRET=$(openssl rand -base64 64) \
  java -jar backend.jar
```
