# Configuration

This document describes all configuration options for the project, including environment variables, configuration files, and secrets management.

---

## Environment Variables

<!-- TODO: Document all environment variables. Mark sensitive ones clearly. -->

### How to Set Environment Variables

```bash
# In a .env file (local development)
cp .env.example .env
vim .env

# Export for current shell session
export VAR_NAME=value

# Pass to a command
VAR_NAME=value npm start
```

### Variable Reference

#### Application

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NODE_ENV` | Yes | `development` | Environment: `development`, `staging`, `production` |
| `APP_NAME` | No | `[project name]` | Application name for logging/metrics |
| `APP_VERSION` | No | `[from package.json]` | Application version |
| `LOG_LEVEL` | No | `info` | Logging level: `trace`, `debug`, `info`, `warn`, `error`, `fatal` |
| `PORT` | No | `8080` | HTTP port the server listens on |
| `HOST` | No | `0.0.0.0` | Host interface to bind to |
| `BASE_URL` | No | `http://localhost:PORT` | Public-facing base URL (used for CORS, links in emails, etc.) |

#### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | | PostgreSQL connection string: `postgresql://user:pass@host:5432/dbname` |
| `DATABASE_POOL_MIN` | No | `2` | Minimum pool connections |
| `DATABASE_POOL_MAX` | No | `10` | Maximum pool connections |
| `DATABASE_SSL` | No | `false` | Require SSL for database connections (`true` in production) |
| `DATABASE_TIMEOUT` | No | `5000` | Query timeout in milliseconds |

#### Cache / Session Store

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection string |
| `REDIS_PASSWORD` | No | | Redis password (if required) |
| `CACHE_TTL` | No | `3600` | Default cache TTL in seconds |

#### Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | **Yes** | | Secret key for signing JWT tokens. **Must be at least 32 characters.** |
| `JWT_EXPIRY` | No | `3600` | Access token expiry in seconds (default: 1 hour) |
| `JWT_REFRESH_EXPIRY` | No | `604800` | Refresh token expiry in seconds (default: 7 days) |
| `SESSION_SECRET` | **Yes** | | Secret for session encryption. **Must be at least 32 characters.** |
| `BCRYPT_ROUNDS` | No | `12` | bcrypt cost factor (higher = more secure but slower) |

#### External Services

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SMTP_HOST` | No | | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USER` | No | | SMTP username |
| `SMTP_PASSWORD` | **Yes** (if SMTP configured) | | SMTP password |
| `SMTP_FROM` | No | `noreply@[domain]` | Default sender email address |
| `AWS_ACCESS_KEY_ID` | For AWS services | | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | For AWS services | | AWS secret key |
| `AWS_REGION` | No | `us-east-1` | AWS region |
| `S3_BUCKET` | If using S3 | | S3 bucket name for file uploads |
| `[OTHER_SERVICE]_API_KEY` | Varies | | API key for `[Other Service]` |
| `[OTHER_SERVICE]_URL` | Varies | | Base URL for `[Other Service]` |

#### Feature Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FEATURE_NEW_DASHBOARD` | No | `false` | Enable new dashboard UI |
| `FEATURE_BETA_API` | No | `false` | Enable beta API endpoints |
| `FEATURE_RATE_LIMIT` | No | `true` | Enable rate limiting |

---

## Configuration Files

<!-- TODO: Document all configuration files used by the project. -->

### File Locations

| File | Purpose | Location |
|------|---------|----------|
| `.env` | Local environment variables (not committed) | Project root |
| `.env.example` | Template for `.env` (committed) | Project root |
| `config/default.json` | Default configuration (committed) | `config/` |
| `config/[environment].json` | Environment-specific overrides | `config/` |
| `[ts/js]-config.json` | Build/tool configuration | Project root |

### Configuration Hierarchy

Configuration is loaded in the following order (later sources override earlier):

1. `config/default.json` — Base defaults
2. `config/[NODE_ENV].json` — Environment-specific (e.g., `config/production.json`)
3. Environment variables — Highest priority

### Example: config/default.json

```json
{
  "app": {
    "name": "[Your Project Name]",
    "version": "1.0.0",
    "port": 8080,
    "logLevel": "info"
  },
  "database": {
    "pool": {
      "min": 2,
      "max": 10
    },
    "ssl": false,
    "timeout": 5000
  },
  "auth": {
    "jwtExpiry": 3600,
    "refreshExpiry": 604800,
    "bcryptRounds": 12
  },
  "rateLimit": {
    "windowMs": 60000,
    "max": 100
  }
}
```

### Example: config/production.json

```json
{
  "app": {
    "logLevel": "warn"
  },
  "database": {
    "ssl": true
  },
  "rateLimit": {
    "max": 1000
  }
}
```

---

## Secrets Management

<!-- TODO: Document how secrets are managed. -->

### Local Development

Local secrets are stored in the `.env` file. **Never commit `.env` to version control.**

```
# .gitignore should include:
.env
.env.local
.env.*.local
```

### Production Secrets

<!-- TODO: Specify the secrets management tool used (AWS Secrets Manager, HashiCorp Vault, etc.) -->

| Secret | Manager | How to Access/Update |
|--------|---------|----------------------|
| `JWT_SECRET` | `[AWS Secrets Manager / Vault / etc.]` | `aws secretsmanager get-secret-value --secret-id prod/[project]/jwt_secret` |
| `DATABASE_PASSWORD` | `[Same manager]` | `[Access command]` |
| `SMTP_PASSWORD` | `[Same manager]` | `[Access command]` |
| `[Other secrets]` | `[Manager]` | `[Access command]` |

### Rotating Secrets

When rotating a secret:

1. Update the secret in the secrets manager
2. Deploy the new version (new value will be picked up)
3. Verify the service started correctly
4. Notify stakeholders if session invalidation occurs

**JWT_SECRET rotation:** Note that rotating `JWT_SECRET` will invalidate all existing tokens. Plan for a maintenance window or implement token refresh grace period.

### Secret Naming Convention

| Secret | Name in Secrets Manager |
|--------|------------------------|
| JWT Secret | `prod/[project-name]/jwt_secret` |
| Database Password | `prod/[project-name]/db_password` |
| SMTP Password | `prod/[project-name]/smtp_password` |

---

## TLS / SSL

### Certificate Management

| Environment | Certificate Source | Auto-Renewal |
|-------------|-------------------|--------------|
| Local | Self-signed via `mkcert` or `devcert` | N/A |
| Staging | Managed by load balancer / ingress | Yes |
| Production | Managed by load balancer / ingress | Yes |

### TLS Versions

Minimum supported TLS version: **TLS 1.2**

Recommended: TLS 1.3

### HSTS

HTTP Strict Transport Security is enabled in production:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

---

## Feature Flags Configuration

Feature flags can be configured via environment variables or (if using a feature flag service) via the feature flag dashboard.

### Using Environment Variables

```bash
FEATURE_NEW_DASHBOARD=true npm run dev
```

### Using a Feature Flag Service (e.g., LaunchDarkly, Unleash)

```bash
# Configure the SDK key
LAUNCHDARKLY_SDK_KEY=[your-sdk-key]
```

| Flag Name | Type | Default | Description |
|-----------|------|---------|-------------|
| `FEATURE_NEW_DASHBOARD` | boolean | `false` | Enable redesigned dashboard UI |
| `FEATURE_BETA_API` | boolean | `false` | Enable beta API endpoints |
| `FEATURE_RATE_LIMIT` | boolean | `true` | Enable API rate limiting |

---

## Environment-Specific Configuration

### Development

```bash
NODE_ENV=development
LOG_LEVEL=debug
DATABASE_URL=postgresql://user:pass@localhost:5432/devdb
REDIS_URL=redis://localhost:6379
JWT_SECRET=dev-only-secret-not-for-production-use-min32chars
```

### Staging

```bash
NODE_ENV=staging
LOG_LEVEL=info
DATABASE_URL=postgresql://user:pass@staging-db.internal:5432/stagingdb
REDIS_URL=redis://staging-redis.internal:6379
JWT_SECRET=[staging-secret-from-secrets-manager]
```

### Production

```bash
NODE_ENV=production
LOG_LEVEL=warn
DATABASE_URL=[production-database-url-from-secrets-manager]
REDIS_URL=[production-redis-url-from-secrets-manager]
JWT_SECRET=[production-secret-from-secrets-manager]
FEATURE_RATE_LIMIT=true
```

---

## Validation

The application validates configuration on startup. If required variables are missing or have invalid values, the application will fail to start with a descriptive error message.

To validate your configuration manually:

```bash
# Validate environment setup
npm run config:validate

# Print resolved configuration (secrets redacted)
npm run config:dump
```

### Required at Startup

These variables **must** be set before starting the application:

- `NODE_ENV`
- `DATABASE_URL`
- `JWT_SECRET`

### Optional but Recommended

These variables have defaults but should be reviewed for production:

- `REDIS_URL`
- `SESSION_SECRET`
- `SMTP_*` variables (if sending email)
- `AWS_*` variables (if using AWS services)
