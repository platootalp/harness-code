# Workflows

## Project Initialization Workflow (0→1)

For new projects from scratch.

```
requirements → product-architecture → technical-architecture → schedule
    ↓                ↓                     ↓                  ↓
 [review]         [review]              [review]           [review]
```

### Steps

| Step | Document | Purpose |
|------|----------|---------|
| 1 | Requirements | Gather and specify what the system must do |
| 2 | Product Architecture | Define business capabilities, domain model, user journeys |
| 3 | Technical Architecture | Design technology stack, system components, data model |
| 4 | Schedule | Establish milestones, timeline, dependencies |

### Output

```
docs/project/
├── requirements.md
├── product-architecture.md
├── technical-architecture.md
└── schedule.md
```

---

## Iterative Development Workflow

For adding features or making changes to an existing project.

```
requirements → prd → design → dev-plan → testing-plan → release-plan
    ↓           ↓       ↓         ↓            ↓             ↓
 [review]   [review] [review]  [review]     [review]      [review]
```

### Steps

| Step | Document | Purpose |
|------|----------|---------|
| 1 | Requirements | Capture user stories and functional requirements |
| 2 | PRD | Define product requirements, goals, success metrics |
| 3 | Design | Create UI, frontend, and/or backend design |
| 4 | Dev Plan | Plan implementation approach and steps |
| 5 | Testing Plan | Define test strategy and test cases |
| 6 | Release Plan | Plan deployment, rollback, communication |

### Output

```
docs/specs/
├── requirements/
├── prd/
├── design/
├── dev-plan/
├── testing-plan/
└── release-plan/
```

---

## Review Process

All reviews follow the same pattern:

1. Author completes document
2. Reviewer checks against review template
3. Issues documented with severity
4. Decision: Approved / Approved with conditions / Rejected
5. Sign-off recorded

### Review Files

All reviews live in `docs/review/`:

```
docs/review/`
├── requirements-review.md
├── prd-review.md
├── design-review.md
├── dev-plan-review.md
├── testing-plan-review.md
└── release-plan-review.md
```

### Review Checklist Categories

- **Completeness** — All sections filled, no gaps
- **Clarity** — Unambiguous, implementable language
- **Feasibility** — Technically achievable
- **Testability** — Can be verified
- **Consistency** — Aligns with other documents

### Decision Criteria

| Decision | Meaning |
|----------|---------|
| Approved | Ready to proceed |
| Approved with conditions | Proceed with noted fixes |
| Rejected | Major rework required |
