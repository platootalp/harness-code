# Functional Architecture

> This document describes the functional decomposition of the system: what the system does from a business capability perspective, not how it technically implements it. Use this to align stakeholders on the "what" before diving into the "how."

## Business Capabilities

> Business capabilities represent the high-level functions the system must support. These should map to business value, not internal team structure.

### Capability Map

```
TODO: Create a top-level capability map showing major capability areas.
Example:

                    [Customer Portal]
                           |
        +------------------+------------------+
        |                  |                  |
   [Account Mgmt]    [Billing]        [Support]
        |                  |                  |
   +----+----+         +---+--+          +----+----+
   |     |    |         |     |          |         |
 [View] [Upd] [Close] [Pay] [Inv]     [Ticket] [Chat]
```

### Capability Details

| Capability | Description | Business Value | Owner |
|------------|-------------|----------------|-------|
| TODO: Add capability | TODO: What does this capability do? | TODO: Why does it matter to the business? | TODO: Who is responsible? |
| TODO: Add capability | TODO: What does this capability do? | TODO: Why does it matter to the business? | TODO: Who is responsible? |

## Domain Model

> The domain model describes the key concepts, entities, and relationships within the problem space. This section captures the "language" of the business.

### Glossary

| Term | Definition | Aliases |
|------|------------|---------|
| TODO: Add term | TODO: Clear, concise definition | TODO: Other names for this concept |
| TODO: Add term | TODO: Clear, concise definition | TODO: Other names for this concept |

### Entities

> Entities are objects with a distinct identity that persists over time.

| Entity | Description | Attributes | Lifecycle |
|--------|-------------|------------|-----------|
| TODO: Add entity | TODO: What is this? | TODO: Key attributes (id, name, status, etc.) | TODO: How is this created/updated/deleted? |
| TODO: Add entity | TODO: What is this? | TODO: Key attributes | TODO: How is this created/updated/deleted? |

**Example:**
| User | Represents a system user | id (UUID), email, name, role, createdAt, lastLoginAt | Created on signup, updated on profile change, deleted on account closure (soft delete) |

### Value Objects

> Value objects are immutable objects defined by their attributes, not by a unique identity.

| Value Object | Attributes | Purpose |
|--------------|------------|---------|
| TODO: Add value object | TODO: List attributes | TODO: Why does this exist? |
| TODO: Add value object | TODO: List attributes | TODO: Why does this exist? |

**Example:**
| Money | amount (Decimal), currency (ISO code) | Represents a monetary amount without implying anything about how it is stored |
| Address | street, city, state, postalCode, country | Represents a physical location |

### Aggregates

> Aggregates are clusters of related entities and value objects that are treated as a unit for data changes.

| Aggregate Root | Contains | Invariants (Business Rules) |
|----------------|----------|------------------------------|
| TODO: Add aggregate | TODO: List contained entities and value objects | TODO: What rules must always hold? |
| TODO: Add aggregate | TODO: List contained entities and value objects | TODO: What rules must always hold? |

**Example:**
| Order | Order (root), OrderLineItem, ShippingAddress | Order total must equal sum of line items; Order cannot be modified once shipped |
| Account | Account (root), User, Subscription | Account owner must always be a User with admin role; Subscription must have at least one active User |

### Domain Events

> Domain events represent something significant that happened in the domain. Other parts of the system can react to these events.

| Event | Trigger | Payload | Consumers |
|-------|---------|---------|-----------|
| TODO: Add event | TODO: When is this fired? | TODO: What data is included? | TODO: What listens to this? |
| TODO: Add event | TODO: When is this fired? | TODO: What data is included? | TODO: What listens to this? |

**Example:**
| UserRegistered | New user completes signup | { userId, email, timestamp } | EmailService, AnalyticsService |
| OrderPlaced | Customer submits order | { orderId, customerId, totalAmount, items } | InventoryService, PaymentService, NotificationService |

## User Journeys

> User journeys describe the steps a user takes to accomplish a goal. These should be written from the user's perspective.

### Journey 1: [TODO: User Goal]

| Step | Action | User Sees/Does | System Response |
|------|--------|----------------|-----------------|
| 1 | TODO: Action | TODO: What does the user see/do? | TODO: What does the system do? |
| 2 | TODO: Action | TODO: What does the user see/do? | TODO: What does the system do? |
| 3 | TODO: Action | TODO: What does the user see/do? | TODO: What does the system do? |

**Happy Path Outcome:** TODO: Describe successful completion
**Alternative Paths:** TODO: List alternative flows (errors, cancellations, etc.)

### Journey 2: [TODO: User Goal]

| Step | Action | User Sees/Does | System Response |
|------|--------|----------------|-----------------|
| 1 | TODO: Action | TODO: What does the user see/do? | TODO: What does the system do? |
| 2 | TODO: Action | TODO: What does the user see/do? | TODO: What does the system do? |

**Happy Path Outcome:** TODO: Describe successful completion
**Alternative Paths:** TODO: List alternative flows

### Journey 3: [TODO: User Goal]

| Step | Action | User Sees/Does | System Response |
|------|--------|----------------|-----------------|
| 1 | TODO: Action | TODO: What does the user see/do? | TODO: What does the system do? |

**Happy Path Outcome:** TODO: Describe successful completion
**Alternative Paths:** TODO: List alternative flows

## Data Flow

> This section describes how data moves through the system, showing key inputs, outputs, and transformations.

### Data Flow Diagram (Text)

```
TODO: Create a text-based data flow diagram
Example:

[External System A] --> (API Gateway) --> [Auth Service] --> [User Service]
                                                        |
                                                        v
                                              [Event Bus / Message Queue]
                                                        |
                        +---------------+---------------+---------------+
                        |               |               |               |
                        v               v               v               v
               [Order Service]  [Payment Service] [Inventory Service] [Notification Service]
                        |               |               |               |
                        v               v               v               v
               [Database A]     [Payment Gateway] [Database B]    [Email/SMS Gateway]
```

### Key Integrations

| System | Integration Type | Data Exchanged | Frequency | Owner |
|--------|------------------|----------------|-----------|-------|
| TODO: Add system | REST API / GraphQL / Webhook / File Transfer / etc. | TODO: What data? | Real-time / Batch / Scheduled | TODO: Who owns this? |
| TODO: Add system | REST API / GraphQL / Webhook / File Transfer / etc. | TODO: What data? | Real-time / Batch / Scheduled | TODO: Who owns this? |

### Data Ownership

| Data Domain | Owner | Storage Location | Retention Policy |
|-------------|-------|------------------|------------------|
| TODO: Add domain | TODO: Team or role | TODO: Where is it stored? | TODO: How long is it kept? |
| TODO: Add domain | TODO: Team or role | TODO: Where is it stored? | TODO: How long is it kept? |

## Functional Requirements

> This section captures specific functional requirements that don't fit elsewhere but are critical to capture.

| ID | Requirement | Priority | Acceptance Criteria |
|----|--------------|----------|---------------------|
| FR-001 | TODO: Add requirement | Must Have / Should Have / Could Have | TODO: How do we verify this? |
| FR-002 | TODO: Add requirement | Must Have / Should Have / Could Have | TODO: How do we verify this? |
| FR-003 | TODO: Add requirement | Must Have / Should Have / Could Have | TODO: How do we verify this? |

## Non-Functional Requirements

> Non-functional requirements define quality attributes of the system.

| Category | Requirement | Target | Measurement |
|----------|-------------|--------|-------------|
| Performance | TODO: Requirement | TODO: Target | TODO: How to measure |
| Availability | TODO: Requirement | TODO: Target | TODO: How to measure |
| Scalability | TODO: Requirement | TODO: Target | TODO: How to measure |
| Security | TODO: Requirement | TODO: Target | TODO: How to measure |
| Maintainability | TODO: Requirement | TODO: Target | TODO: How to measure |

## Use Cases

> Detailed descriptions of system interactions from a user's perspective.

### UC-001: [TODO: Use Case Name]

**Actor:** TODO: Who performs this?
**Preconditions:** TODO: What must be true before?
**Postconditions:** TODO: What is true after?
**Main Flow:**
1. TODO: Step 1
2. TODO: Step 2
3. TODO: Step 3

**Alternative Flows:**
- TODO: Alternative 1
- TODO: Alternative 2

**Exception Handling:**
- TODO: Exception 1 and how it is handled
- TODO: Exception 2 and how it is handled

---

*Last Updated: [Date] | Last Updated By: [Name]*
