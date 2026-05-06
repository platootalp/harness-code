# Claude Agent & Document Structure Design

## Overview

Design of Claude Code harness agents and their mapping to document output structure, forming a complete spec-driven development workflow.

## Agent Types

### 1. Requirements Agent
- **Purpose**: Elicit, capture, and document user requirements
- **Output**: `docs/specs/requirements/YYYY-MM-DD-feature-name.md`
- **Template**: `docs/specs/requirements/templates/requirements.md`

### 2. PRD Agent
- **Purpose**: Transform requirements into product requirements document
- **Input**: Requirements output
- **Output**: `docs/specs/prd/YYYY-MM-DD-feature-name.md`
- **Template**: `docs/specs/prd/templates/prd.md`

### 3. Design Agent
- **Purpose**: Create technical design documents
- **Input**: PRD output
- **Output**:
  - `docs/specs/design/YYYY-MM-DD-feature-name-design-ui.md`
  - `docs/specs/design/YYYY-MM-DD-feature-name-design-frontend.md`
  - `docs/specs/design/YYYY-MM-DD-feature-name-design-backend.md`
- **Templates**:
  - `docs/specs/design/templates/design-ui.md`
  - `docs/specs/design/templates/design-frontend.md`
  - `docs/specs/design/templates/design-backend.md`

### 4. Dev-Plan Agent
- **Purpose**: Create development implementation plan
- **Input**: Design output
- **Output**: `docs/specs/dev-plan/YYYY-MM-DD-feature-name.md`
- **Template**: `docs/specs/dev-plan/templates/dev-plan.md`

### 5. Testing-Plan Agent
- **Purpose**: Create testing strategy and test cases
- **Input**: Design + Dev-Plan output
- **Output**: `docs/specs/testing-plan/YYYY-MM-DD-feature-name.md`
- **Template**: `docs/specs/testing-plan/templates/testing-plan.md`

### 6. Release-Plan Agent
- **Purpose**: Create release/deployment plan
- **Input**: Dev-Plan + Testing-Plan output
- **Output**: `docs/specs/release-plan/YYYY-MM-DD-feature-name.md`
- **Template**: `docs/specs/release-plan/templates/release-plan.md`

### 7. Review Agent
- **Purpose**: Review any spec document at any stage
- **Input**: Any spec document output
- **Output**: `docs/review/YYYY-MM-DD-feature-name-stage-review.md`
- **Template**: Corresponding review template in `docs/review/`
- **Behavior**: Loop back to author if issues found, approve when passed

### 8. Doc Agent
- **Purpose**: Maintain living project documentation
- **Input**: All spec outputs from previous stages
- **Output**: Living docs in `docs/project/`
  - `docs/project/overview/overview.md`
  - `docs/project/architecture/architecture.md`
  - `docs/project/api/api.md`
  - `docs/project/usage/usage.md`
  - `docs/project/configuration/configuration.md`
  - `docs/project/glossary/glossary.md`

## Workflow Chain

```
User Input
    ↓
Requirements Agent → [Review Loop] → (approved)
    ↓
PRD Agent → [Review Loop] → (approved)
    ↓
Design Agent → [Review Loop] → (approved)
    ↓
Dev-Plan Agent → [Review Loop] → (approved)
    ↓
Testing-Plan Agent → [Review Loop] → (approved)
    ↓
Release-Plan Agent → [Review Loop] → (approved)
    ↓
Doc Agent → (living project docs updated)
```

## Document Directory Structure

```
docs/
├── init/                              # Project init templates
│   ├── overview.md
│   ├── product-architecture.md
│   ├── schedule.md
│   └── technical-architecture.md
├── project/                           # Living project docs (Doc Agent output)
│   ├── overview/
│   ├── architecture/
│   ├── api/
│   ├── usage/
│   ├── configuration/
│   └── glossary/
├── review/                            # All review templates (Review Agent output)
│   ├── requirements-review.md
│   ├── prd-review.md
│   ├── design-review.md
│   ├── dev-plan-review.md
│   ├── testing-plan-review.md
│   └── release-plan-review.md
└── specs/                             # Development specs (all spec agents output)
    ├── requirements/
    ├── prd/
    ├── design/
    ├── dev-plan/
    ├── testing-plan/
    └── release-plan/
```

## Agent Naming Convention

| Agent | Output Prefix |
|-------|---------------|
| Requirements Agent | `REQ-001` |
| PRD Agent | `PRD-001` |
| Design Agent | `DESIGN-001` |
| Dev-Plan Agent | `DEV-001` |
| Testing-Plan Agent | `TEST-001` |
| Release-Plan Agent | `REL-001` |
| Review Agent | `{STAGE}-REVIEW-001` |
| Doc Agent | Project docs (no prefix) |

## Review Loop Process

1. Spec agent produces document
2. Review agent evaluates against review template
3. If issues found → document returned to author with feedback
4. Author revises and resubmits
5. Repeat until Review Agent approves
6. Proceed to next stage

## Implementation Notes

- Each agent uses corresponding template from `docs/specs/*/templates/`
- Agents use front matter for metadata (ID, date, author)
- File naming: `YYYY-MM-DD-feature-name.md`
- Review templates in `docs/review/` cover all stages
