# API Documentation

## Base URL

<!-- TODO: Fill in the base URL(s) for the API. -->

| Environment | Base URL |
|-------------|----------|
| Local Development | `http://localhost:[PORT]` |
| Staging | `https://api-staging.[domain].com` |
| Production | `https://api.[domain].com` |
| API Version | `v[Version, e.g., 1]` |

**Full Base URL Format:** `[Base URL]/[Version]/`

Example: `https://api.example.com/v1`

---

## Authentication

<!-- TODO: Document the authentication mechanism. -->

### Authentication Method

`[Describe the auth method — Bearer tokens (JWT), API keys, OAuth 2.0, Basic Auth, etc.]`

### Header Format

```
<!-- TODO: Show the exact header format -->

Authorization: Bearer [YOUR_TOKEN_HERE]
```

### Obtaining a Token

#### Via Login Endpoint

```
POST /v1/auth/login
Content-Type: application/json

{
  "email": "[user@example.com]",
  "password": "[your-password]"
}
```

**Response:**

```json
{
  "access_token": "[JWT token]",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "[refresh token if applicable]"
}
```

#### Via API Key (if applicable)

`[For API key auth — explain how to generate/obtain API keys, where to include them]`

### Token Scopes

| Scope | Description |
|-------|-------------|
| `read` | Read-only access to resources |
| `write` | Create and update resources |
| `delete` | Delete resources |
| `admin` | Administrative operations |

---

## Request Format

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes (most endpoints) | `Bearer [token]` |
| `Content-Type` | Yes (POST/PUT/PATCH) | `application/json` |
| `Accept` | No | `application/json` (default) |
| `X-Request-ID` | No | Client-generated UUID for request tracing |

### Query Parameters

`[Document conventions for query params — pagination, filtering, sorting]`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number |
| `per_page` | integer | `20` | Items per page (max: 100) |
| `sort` | string | `[default field]` | Sort field (prefix `-` for descending) |
| `filter[field]` | string | | Filter by field value |

### Example Request

```bash
curl -X GET "https://api.example.com/v1/users?page=1&per_page=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

---

## Response Format

### Success Response

```json
{
  "data": {
    "id": "usr_abc123",
    "email": "user@example.com",
    "name": "Jane Doe",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "meta": {
    "request_id": "req_xyz789"
  }
}
```

### List Response (Paginated)

```json
{
  "data": [
    { "[object 1]" },
    { "[object 2]" }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8,
    "next": "/v1/users?page=2",
    "prev": null
  },
  "meta": {
    "request_id": "req_xyz789"
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error message",
    "details": [
      {
        "field": "email",
        "message": "Must be a valid email address"
      }
    ]
  },
  "meta": {
    "request_id": "req_xyz789"
  }
}
```

---

## Endpoints

<!-- TODO: Document all API endpoints. Use a table for summary, then detailed sections for each. -->

### Summary

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `GET` | `/v1/[resource]` | `[List/description]` | Yes |
| `POST` | `/v1/[resource]` | `[Create/description]` | Yes |
| `GET` | `/v1/[resource]/{id}` | `[Get single/description]` | Yes |
| `PUT` | `/v1/[resource]/{id}` | `[Update (full)/description]` | Yes |
| `PATCH` | `/v1/[resource]/{id}` | `[Update (partial)/description]` | Yes |
| `DELETE` | `/v1/[resource]/{id}` | `[Delete/description]` | Yes |

---

### Authentication

#### `POST /v1/auth/login`

**Description:** Authenticate user and obtain access token.

**Auth Required:** No

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | User email address |
| `password` | string | Yes | User password |

**Example Request:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Success Response (200):**

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2g..."
  }
}
```

**Error Responses:**

| Status | Code | Description |
|--------|------|-------------|
| `400` | `VALIDATION_ERROR` | Invalid request body |
| `401` | `INVALID_CREDENTIALS` | Email or password incorrect |

---

#### `POST /v1/auth/refresh`

**Description:** Refresh an access token using a refresh token.

**Auth Required:** No (uses refresh token in body)

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | Yes | Valid refresh token |

**Success Response (200):**

```json
{
  "data": {
    "access_token": "[new access token]",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}
```

---

### Users

#### `GET /v1/users`

**Description:** List all users (paginated).

**Auth Required:** Yes (`read` scope)

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number |
| `per_page` | integer | `20` | Items per page |
| `sort` | string | `created_at` | Sort field (prefix `-` for desc) |
| `filter[status]` | string | | Filter by user status |

**Success Response (200):**

```json
{
  "data": [
    {
      "id": "usr_abc123",
      "email": "alice@example.com",
      "name": "Alice Smith",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "usr_def456",
      "email": "bob@example.com",
      "name": "Bob Jones",
      "status": "inactive",
      "created_at": "2024-01-10T08:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 2,
    "total_pages": 1
  }
}
```

---

#### `GET /v1/users/{id}`

**Description:** Get a specific user by ID.

**Auth Required:** Yes

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | User ID (e.g., `usr_abc123`) |

**Success Response (200):**

```json
{
  "data": {
    "id": "usr_abc123",
    "email": "alice@example.com",
    "name": "Alice Smith",
    "status": "active",
    "roles": ["admin"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-02-20T14:00:00Z"
  }
}
```

**Error Responses:**

| Status | Code | Description |
|--------|------|-------------|
| `404` | `NOT_FOUND` | User does not exist |

---

#### `POST /v1/users`

**Description:** Create a new user.

**Auth Required:** Yes (`admin` scope)

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Unique email address |
| `name` | string | Yes | Full name |
| `password` | string | Yes | Password (min 8 chars) |
| `role` | string | No | Role assignment (default: `user`) |

**Example Request:**

```json
{
  "email": "newuser@example.com",
  "name": "New User",
  "password": "securepassword123",
  "role": "user"
}
```

**Success Response (201):**

```json
{
  "data": {
    "id": "usr_new789",
    "email": "newuser@example.com",
    "name": "New User",
    "status": "active",
    "created_at": "2024-03-27T10:00:00Z"
  }
}
```

---

#### `PATCH /v1/users/{id}`

**Description:** Update a user (partial update).

**Auth Required:** Yes (`admin` scope or self)

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | User ID |

**Request Body (all fields optional):**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Updated name |
| `status` | string | `active` or `inactive` |

**Success Response (200):**

```json
{
  "data": {
    "id": "usr_abc123",
    "email": "alice@example.com",
    "name": "Alice Johnson",
    "status": "active",
    "updated_at": "2024-03-27T12:00:00Z"
  }
}
```

---

#### `DELETE /v1/users/{id}`

**Description:** Delete a user (soft delete).

**Auth Required:** Yes (`admin` scope)

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | User ID |

**Success Response (204):** No content

---

## Error Codes

<!-- TODO: Document all error codes the API can return. -->

### Standard Error Codes

| Code | HTTP Status | Description | Resolution |
|------|------------|-------------|------------|
| `VALIDATION_ERROR` | 400 | Request body/params failed validation | Check `details` array for field-specific errors |
| `INVALID_CREDENTIALS` | 401 | Email/password incorrect | Verify credentials |
| `TOKEN_EXPIRED` | 401 | Access token has expired | Use refresh token to get new access token |
| `INVALID_TOKEN` | 401 | Token is malformed or invalid | Re-authenticate |
| `FORBIDDEN` | 403 | Insufficient permissions | Request appropriate scopes or contact admin |
| `NOT_FOUND` | 404 | Resource does not exist | Verify the resource ID is correct |
| `CONFLICT` | 409 | Resource already exists (e.g., duplicate email) | Use a different identifier |
| `RATE_LIMITED` | 429 | Too many requests | Wait and retry; see Rate Limiting section |
| `INTERNAL_ERROR` | 500 | Unexpected server error | Report to engineering team |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily down | Retry with exponential backoff |

### Error Response Example

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Must be a valid email address"
      },
      {
        "field": "password",
        "message": "Must be at least 8 characters"
      }
    ]
  },
  "meta": {
    "request_id": "req_abc123xyz"
  }
}
```

---

## Rate Limiting

<!-- TODO: Document rate limiting policy. -->

### Limits by Tier

| Tier | Requests per Minute | Requests per Hour |
|------|--------------------:|------------------:|
| Free | 60 | 1,000 |
| Pro | 300 | 10,000 |
| Enterprise | 1,000 | 50,000 |

### Rate Limit Headers

Every response includes these headers:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests per window |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |

### Handling 429 Responses

When rate limited, wait until `X-RateLimit-Reset` and retry. Implement exponential backoff for repeated 429s.

**429 Response Body:**

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Please retry after [time].",
    "retry_after": 30
  }
}
```

---

## Webhooks

<!-- TODO: Document webhook configuration if applicable. -->

### Configuring Webhooks

`[Explain how to register webhook endpoints]`

### Event Types

| Event | Description |
|-------|-------------|
| `user.created` | A new user was created |
| `user.updated` | A user was updated |
| `user.deleted` | A user was deleted |

### Webhook Payload

```json
{
  "id": "evt_123456",
  "type": "user.created",
  "created_at": "2024-03-27T10:00:00Z",
  "data": {
    "id": "usr_abc123",
    "email": "user@example.com",
    "name": "New User"
  }
}
```

### Verifying Webhook Signatures

`[If using signed webhooks — explain the signature verification process]`
