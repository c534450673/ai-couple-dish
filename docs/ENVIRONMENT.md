# Environment Configuration Guide

This document describes all environment variables used in the AI Couple Dish project.

## Quick Start

1. Copy `.env.example` to `.env` in the project root
2. Fill in your configuration values
3. **Never commit `.env` files to version control**

## Backend Environment Variables

### Database Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DB_HOST` | MySQL database host | `localhost` | Yes |
| `DB_PORT` | MySQL database port | `3306` | Yes |
| `DB_NAME` | Database name | `ai_couple_dish` | Yes |
| `DB_USERNAME` | Database username | `root` | Yes |
| `DB_PASSWORD` | Database password | - | Yes |

### Redis Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REDIS_HOST` | Redis server host | `localhost` | Yes |
| `REDIS_PORT` | Redis server port | `6379` | Yes |
| `REDIS_PASSWORD` | Redis password | - | No |
| `REDIS_DATABASE` | Redis database number | `0` | No |

### JWT Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `JWT_SECRET` | JWT signing key (min 64 chars for HS512) | - | **Yes (Production)** |
| `JWT_EXPIRATION` | Token expiration time in ms | `604800000` (7 days) | No |

**⚠️ Security Warning**: In production, you MUST set a strong `JWT_SECRET`:
```bash
openssl rand -base64 64
```

### Server Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SERVER_PORT` | Backend server port | `8080` | No |
| `SPRING_PROFILES_ACTIVE` | Spring profile (`dev`, `prod`) | `dev` | Yes |
| `CORS_ORIGINS` | Allowed CORS origins | `*` | No |

### Logging Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LOG_LEVEL` | Application log level | `debug` | No |
| `LOG_LEVEL_SPRING` | Spring framework log level | `info` | No |

## Frontend Environment Variables

### H5 Version (Vite)

Variables must be prefixed with `VITE_` to be exposed to the Vite-processed code.

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8080/api` | Yes |
| `VITE_WS_URL` | WebSocket server URL | `ws://localhost:8080/ws` | No |

### UniApp Version

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `UNIAPP_API_BASE_URL` | Backend API base URL | `http://localhost:8080/api` | Yes |

## Development Setup

### 1. Backend

```bash
cd backend

# Copy environment template
cp .env.example .env

# Edit .env with your local database credentials
vim .env

# Run the application
mvn spring-boot:run
```

### 2. Frontend H5

```bash
cd frontend-h5

# Copy environment template
cp .env.example .env

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Frontend UniApp

```bash
cd frontend-uniapp

# Copy environment template
cp .env.example .env

# Install dependencies
npm install

# Start H5 development
npm run dev:h5
```

## Production Deployment

### Backend (Kubernetes)

For production, secrets should be managed via Kubernetes Secrets or external secret managers:

```bash
# Create secrets manually
kubectl create secret generic ai-couple-dish-secrets \
  --from-literal=DB_PASSWORD='your_secure_password' \
  --from-literal=JWT_SECRET='your_64_char_secret' \
  -n ai-couple-dish-prod

# Or use sealed-secrets for GitOps workflow
```

See `deploy/prod/k8s/secret.yaml.example` for the secret template.

### Backend (Docker)

```bash
# Set environment variables
export DB_PASSWORD=your_secure_password
export JWT_SECRET=$(openssl rand -base64 64)

# Run with environment variables
docker run -e DB_PASSWORD -e JWT_SECRET your_image
```

### Frontend

For frontend, build with environment-specific values:

```bash
# H5 Production Build
cd frontend-h5
VITE_API_BASE_URL=https://api.production.com/api npm run build
```

## Troubleshooting

### JWT Token Issues

If you encounter authentication errors:
1. Verify `JWT_SECRET` is set correctly
2. Ensure `JWT_SECRET` is at least 64 characters
3. Check that the same `JWT_SECRET` is used across services

### CORS Errors

If you see CORS errors:
1. Verify `CORS_ORIGINS` includes your frontend domain
2. For production, set specific origins instead of `*`

### Database Connection Issues

1. Verify MySQL is running
2. Check `DB_HOST`, `DB_PORT`, `DB_NAME` are correct
3. Ensure database user has proper permissions
4. Check firewall settings for MySQL port

## Security Best Practices

1. **Never commit `.env` files** - Add `.env` to `.gitignore`
2. **Use strong JWT secrets** - Generate with `openssl rand -base64 64`
3. **Separate environments** - Use different credentials for dev/staging/prod
4. **Rotate secrets regularly** - Especially in production
5. **Use secret managers** - Consider HashiCorp Vault, AWS Secrets Manager, etc.
