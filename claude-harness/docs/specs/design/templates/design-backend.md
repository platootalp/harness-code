# Backend Design: [Feature Name]

## ID
DESIGN-BE-[NUMBER]

Example: DESIGN-BE-001, DESIGN-BE-002, etc.

## Date
[ISO 8601 Date Format: YYYY-MM-DD]

Example: 2026-03-27

## Author
[Full Name] <[email@company.com](mailto:email@company.com)>

Example: Jane Smith <jane.smith@company.com>

## Related Documents

| Document Type | Document ID | Version | Notes |
|---------------|-------------|---------|-------|
| Requirements | [REQ-XXX] | [Version] | [Link or notes] |
| PRD | [PRD-XXX] | [Version] | [Link or notes] |
| UI Design | [DESIGN-UI-XXX] | [Version] | [Link or notes] |
| Frontend Design | [DESIGN-FE-XXX] | [Version] | [Link or notes] |
| Testing Plan | [TEST-XXX] | [Version] | [Link or notes] |

## Overview

[Provide a brief summary (2-3 sentences) of the backend architecture for this feature. This should cover the main technical approach, frameworks used, and key architectural decisions.

Example: "The Data Export backend service is built using Node.js with Express, following our REST API conventions. It uses a job queue architecture (Bull with Redis) for processing export requests asynchronously, with status tracking and webhook notifications for completion. The service integrates with our existing S3-compatible storage for file delivery."]

## Technical Stack

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| Runtime | [e.g., Node.js 20 LTS] | [Application runtime] | [Any relevant notes] |
| Framework | [e.g., Express.js 4.x] | [HTTP framework] | [Middleware used] |
| Language | [e.g., TypeScript 5.x] | [Language] | [Strict mode enabled?] |
| Database | [e.g., PostgreSQL 15] | [Primary data store] | [ORM: Prisma/Drizzle/Sequelize] |
| Cache | [e.g., Redis 7.x] | [Caching and job queues] | [Use cases] |
| Queue | [e.g., BullMQ / RabbitMQ] | [Async job processing] | [Job types] |
| Storage | [e.g., AWS S3] | [File storage] | [Bucket and region] |
| Auth | [e.g., JWT / OAuth2] | [Authentication] | [Implementation details] |

## API Design

### Base URL Structure

| Environment | Base URL |
|-------------|----------|
| Development | [https://api.dev.example.com/v1] |
| Staging | [https://api.staging.example.com/v1] |
| Production | [https://api.example.com/v1] |

### Authentication

[Describe how API authentication works for this service.]

| Auth Method | Implementation | Usage |
|-------------|---------------|-------|
| [Method, e.g., Bearer Token] | [How it works] | [Where used] |
| [Method, e.g., API Key] | [How it works] | [Where used] |

**Headers Required**:
```
Authorization: Bearer [token]
Content-Type: application/json
X-Request-ID: [unique-request-id]
X-Correlation-ID: [correlation-id]
```

### Endpoints

[Define all API endpoints for this feature.]

| Method | Endpoint | Request | Response | Purpose | Auth |
|--------|----------|---------|----------|---------|------|
| GET | /features | [Request type] | [Response type] | [List all features] | [Auth type] |
| POST | /features | [Request type] | [Response type] | [Create feature] | [Auth type] |
| GET | /features/{id} | [Request type] | [Response type] | [Get feature by ID] | [Auth type] |
| PUT | /features/{id} | [Request type] | [Response type] | [Update feature] | [Auth type] |
| DELETE | /features/{id} | [Request type] | [Response type] | [Delete feature] | [Auth type] |

### Endpoint Specifications

#### GET /[resource]

**Description**: [What this endpoint does]

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number |
| limit | integer | No | 20 | Items per page (max 100) |
| sort | string | No | createdAt | Sort field |
| order | string | No | desc | Sort order (asc/desc) |
| [param] | [type] | No | - | [Description] |

**Success Response** (200):
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "string",
      "createdAt": "ISO8601",
      "updatedAt": "ISO8601"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "totalPages": 5
  }
}
```

---

#### POST /[resource]

**Description**: [What this endpoint does]

**Request Body**:
```json
{
  "name": "string", // Required - Feature name
  "description": "string", // Optional - Feature description
  "type": "string", // Required - Type: standard|premium|enterprise
  "settings": {
    // Feature-specific settings
  }
}
```

**Validation Rules**:
| Field | Rules | Error Code |
|-------|-------|------------|
| name | Required, string, 1-255 chars | VALIDATION_ERROR |
| description | Optional, string, max 5000 chars | VALIDATION_ERROR |
| type | Required, enum: standard, premium, enterprise | VALIDATION_ERROR |

**Success Response** (201):
```json
{
  "data": {
    "id": "uuid",
    "name": "string",
    "description": "string",
    "type": "standard",
    "settings": {},
    "createdAt": "ISO8601",
    "updatedAt": "ISO8601"
  }
}
```

---

#### GET /[resource]/{id}

**Description**: [What this endpoint does]

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| id | UUID | Resource identifier |

**Success Response** (200):
```json
{
  "data": {
    "id": "uuid",
    "name": "string",
    "description": "string",
    "type": "standard",
    "settings": {},
    "createdAt": "ISO8601",
    "updatedAt": "ISO8601"
  }
}
```

**Error Responses**:
| Code | Meaning | Response |
|------|---------|----------|
| 404 | Resource not found | `{ "error": { "code": "NOT_FOUND", "message": "Resource not found" } }` |
| 403 | Forbidden | `{ "error": { "code": "FORBIDDEN", "message": "Access denied" } }` |

---

[Continue for each endpoint]

### Error Handling

#### Standard Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": [
      {
        "field": "fieldName",
        "message": "Field-specific error"
      }
    ],
    "requestId": "uuid",
    "timestamp": "ISO8601"
  }
}
```

#### Error Codes

| Code | HTTP Status | Meaning | Response Details |
|------|-------------|---------|------------------|
| VALIDATION_ERROR | 400 | Request validation failed | Array of field errors |
| UNAUTHORIZED | 401 | Authentication required | - |
| FORBIDDEN | 403 | Access denied | - |
| NOT_FOUND | 404 | Resource not found | - |
| CONFLICT | 409 | Resource conflict | - |
| RATE_LIMITED | 429 | Too many requests | Retry-After header |
| INTERNAL_ERROR | 500 | Server error | Request ID for logging |
| SERVICE_UNAVAILABLE | 503 | Service temporarily unavailable | - |

## Data Model

### Database Schema

[Define the database schema for this feature.]

#### Table: [table_name]

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| name | VARCHAR(255) | NOT NULL | [Description] |
| description | TEXT | - | [Description] |
| type | VARCHAR(50) | NOT NULL | [Description] |
| settings | JSONB | DEFAULT '{}' | [Description] |
| user_id | UUID | NOT NULL, FK(users.id) | Owner reference |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |
| deleted_at | TIMESTAMP | - | Soft delete timestamp |

**Indexes**:
| Index Name | Columns | Type | Description |
|------------|---------|------|-------------|
| idx_table_name_user_id | user_id | B-tree | Fast lookup by user |
| idx_table_name_type | type | B-tree | Filter by type |
| idx_table_name_created_at | created_at | B-tree | Sort by creation time |

**Constraints**:
- CHECK (type IN ('standard', 'premium', 'enterprise'))
- UNIQUE (user_id, name) WHERE deleted_at IS NULL

---

#### Table: [related_table_name]

[Repeat structure for each table]

### Entity Relationship Diagram

```
[Table A] 1 ──────* [Table B]
   │              │
   │              │
   └──────* [Table C]
```

**Relationships**:
- **[Table A] has many [Table B]**: One-to-many relationship via foreign key
- **[Table A] has one [Table C]**: One-to-one relationship

## Business Logic

[Document the business rules and logic for this feature.]

### Business Rules

| Rule ID | Rule | Conditions | Actions | Priority |
|---------|------|------------|---------|----------|
| BR-001 | [Rule name] | [When this rule applies] | [What happens] | [High/Medium/Low] |
| BR-002 | [Rule name] | [When this rule applies] | [What happens] | [Priority] |

### Service Layer

[Define the service modules that contain business logic.]

| Service | File | Responsibilities |
|---------|------|------------------|
| [ServiceName]Service | src/services/[name].ts | [What this service handles] |

#### [ServiceName]Service

**Responsibilities**:
- [Responsibility 1]
- [Responsibility 2]
- [Responsibility 3]

**Public Methods**:
| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| [methodName] | [Input type] | [Output type] | [Description] |
| [methodName] | [Input type] | [Output type] | [Description] |

### Validation Rules

| Rule | Validator | Error Code | Error Message |
|------|-----------|------------|---------------|
| [Validation rule] | [Where implemented] | [Error code] | [Error message] |

## Security

### Authentication & Authorization

| Aspect | Implementation | Details |
|--------|---------------|---------|
| Authentication | [Method used] | [How it works] |
| Authorization | [Method used, e.g., RBAC] | [Role/permission structure] |

### Role-Based Access Control (RBAC)

| Role | Permissions | Description |
|------|-------------|-------------|
| admin | [Permissions] | Full access |
| user | [Permissions] | Limited to own resources |
| guest | [Permissions] | Read-only access |

### Data Protection

| Protection | Implementation | Scope |
|------------|---------------|-------|
| Encryption at Rest | [AES-256/TDE/etc.] | [What data is encrypted] |
| Encryption in Transit | [TLS 1.3] | [All API communication] |
| PII Handling | [Masking/Tokenization] | [PII fields] |

### Rate Limiting

| Endpoint | Limit | Window | Response |
|----------|-------|--------|----------|
| [Endpoint or endpoint pattern] | [Number] | [Time window] | [429 with Retry-After] |

### Input Validation & Sanitization

- **Validation Library**: [Library used, e.g., Joi, Zod, class-validator]
- **Sanitization**: [Any input sanitization beyond validation]
- **SQL Injection Prevention**: [Parameterized queries/ORM usage]
- **XSS Prevention**: [Output encoding strategy]

## Scalability

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Response Time (p50) | < [X] ms | APM monitoring |
| Response Time (p99) | < [X] ms | APM monitoring |
| Throughput | [X] req/sec | Load testing |
| Concurrent Users | [X] | Capacity planning |

### Caching Strategy

| Data | Cache Layer | TTL | Invalidation |
|------|-------------|-----|--------------|
| [Data type] | [Redis/Memory/CDN] | [TTL] | [Invalidation strategy] |
| [Data type] | [Cache layer] | [TTL] | [Invalidation strategy] |

### Horizontal Scaling

- **Stateless Design**: [How the service maintains no client state]
- **Session Storage**: [External session store if needed]
- **Load Balancer**: [Health checks, sticky sessions if needed]
- **Auto-scaling**: [Scaling triggers and configurations]

### Database Optimization

| Optimization | Implementation | Impact |
|--------------|---------------|--------|
| Connection Pooling | [Pool size, connection limits] | Performance |
| Query Optimization | [Indexes, query analysis] | [Impact] |
| Read Replicas | [Replication lag, usage pattern] | [Impact] |

## Dependencies

| Service | Purpose | Version | Connection Details | Owner |
|---------|---------|---------|-------------------|-------|
| PostgreSQL | Primary database | 15.x | host: port: dbname: | [Team] |
| Redis | Caching, sessions | 7.x | host: port: | [Team] |
| S3 | File storage | - | bucket: region: | [Team] |
| [External API] | [Purpose] | [Version] | [URL/connection] | [Team/External] |

### External API Integrations

#### [External Service Name]

| Aspect | Details |
|--------|---------|
| Purpose | [What this integration provides] |
| Endpoint | [Base URL] |
| Auth | [Authentication method] |
| Rate Limits | [Limits imposed] |
| Retry Strategy | [Retry logic, backoff] |

## Monitoring & Observability

### Logging

| Log Level | Usage | Fields |
|-----------|-------|--------|
| error | Application errors | requestId, userId, stack trace |
| warn | Recoverable issues | requestId, context |
| info | Key events | requestId, action, duration |
| debug | Detailed debugging | requestId, full context |

### Metrics

| Metric | Type | Labels | Alert Threshold |
|--------|------|--------|-----------------|
| [metric_name] | [counter/gauge/histogram] | [labels] | [threshold] |
| [metric_name] | [type] | [labels] | [threshold] |

### Health Checks

| Endpoint | Purpose | Checks |
|----------|---------|--------|
| GET /health | Basic health | Service is running |
| GET /health/ready | Readiness | All dependencies available |
| GET /health/live | Liveness | Service can respond |

## Deployment Configuration

### Environment Variables

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| NODE_ENV | string | Yes | - | Environment: development/staging/production |
| DATABASE_URL | string | Yes | - | PostgreSQL connection string |
| REDIS_URL | string | Yes | - | Redis connection string |
| API_KEY | string | Yes | - | API authentication key |
| LOG_LEVEL | string | No | info | Logging level |

### Docker Configuration

**Dockerfile**:
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

**docker-compose.yml** (local development):
```yaml
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
```

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | YYYY-MM-DD | [Author Name] | Initial backend design |
| 1.1 | YYYY-MM-DD | [Author Name] | [Description of changes] |

---

**Template Usage Instructions:**
1. Copy this template to your design/backend directory
2. Rename the file to match your feature name
3. Fill in all sections with your specific backend design
4. Replace bracketed placeholders [like this] with actual values
5. Update endpoint IDs and numbering to follow conventions
6. Add rows to tables as needed
7. Include actual code examples for complex logic
8. Document all API contracts thoroughly for frontend integration
9. Ensure security considerations are comprehensive
10. Review with backend team leads before implementation
