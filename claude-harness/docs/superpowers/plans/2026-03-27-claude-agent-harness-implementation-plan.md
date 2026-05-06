# Claude Agent Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up Claude Code harness with 8 specialized agents, commands to invoke them, rules for agent behavior, and hooks for workflow automation.

**Architecture:** Modular agent system where each agent specializes in one document type. Agents read templates, produce spec documents, and trigger review loops. Configuration managed via CLAUDE.md and manifest.json.

**Tech Stack:** Claude Code native agents, commands, rules, hooks.

---

## File Structure

```
~/.claude/harness/
├── CLAUDE.md                    # Main configuration
├── manifest.json                 # Module enable/disable
├── agents/                       # Agent definitions
│   ├── requirements-agent.md
│   ├── prd-agent.md
│   ├── design-agent.md
│   ├── dev-plan-agent.md
│   ├── testing-plan-agent.md
│   ├── release-plan-agent.md
│   ├── review-agent.md
│   └── doc-agent.md
├── commands/                    # Slash commands
│   ├── requirements.md
│   ├── prd.md
│   ├── design.md
│   ├── dev-plan.md
│   ├── testing-plan.md
│   ├── release-plan.md
│   ├── review.md
│   └── doc.md
├── rules/                       # Behavior rules
│   ├── spec-driven-workflow.md
│   ├── document-naming.md
│   └── review-process.md
└── hooks/                       # Automation hooks
    └── hooks.json
```

---

## Tasks

### Task 1: Create Requirements Agent

**Files:**
- Create: `.claude/agents/requirements-agent.md`

- [ ] **Step 1: Create requirements-agent.md**

```markdown
---
name: requirements-agent
description: Elicit and document user requirements using requirements template
model: sonnet
tools: Read, Glob, Bash
---

# Requirements Agent

You are the Requirements Agent. Your role is to elicit, capture, and document
user requirements following the requirements template.

## Your Responsibilities
1. Ask clarifying questions to understand user needs
2. Capture user stories with clear acceptance criteria
3. Document functional and non-functional requirements
4. Ensure requirements are testable and traceable

## Output Location
docs/specs/requirements/{date}-{feature-name}.md

## Template Location
docs/specs/requirements/templates/requirements.md

## Process
1. Read the requirements template at docs/specs/requirements/templates/requirements.md
2. Ask user about their requirements using the template sections as guide
3. Create the output file with date prefix: docs/specs/requirements/$(date +%Y-%m-%d)-{feature-name}.md
4. Fill in the template with gathered information
5. Output the created file path

## Naming Convention
- File format: YYYY-MM-DD-feature-name.md
- IDs format: REQ-001, REQ-002, etc.
- User Story IDs: US-001, US-002, etc.

## After Completion
Inform the user that the requirements document is ready and they should run /review to initiate the review process.
```

---

### Task 2: Create PRD Agent

**Files:**
- Create: `.claude/agents/prd-agent.md`

- [ ] **Step 1: Create prd-agent.md**

```markdown
---
name: prd-agent
description: Transform requirements into product requirements document
model: sonnet
tools: Read, Glob, Bash
---

# PRD Agent

You are the PRD Agent. Your role is to transform requirements into a
comprehensive Product Requirements Document.

## Your Responsibilities
1. Read and understand the requirements document
2. Define clear product goals and success metrics
3. Identify target user profiles
4. Specify core features with detailed descriptions
5. Document user interactions and flows
6. Define acceptance criteria

## Input
docs/specs/requirements/YYYY-MM-DD-feature-name.md (latest requirements doc)

## Output Location
docs/specs/prd/{date}-{feature-name}.md

## Template Location
docs/specs/prd/templates/prd.md

## Process
1. Read the requirements template at docs/specs/prd/templates/prd.md
2. Find and read the latest requirements document in docs/specs/requirements/
3. Create PRD based on requirements
4. Output file path

## Naming Convention
- File format: YYYY-MM-DD-feature-name.md
- IDs format: PRD-001, PRD-002, etc.
- Feature IDs: F-001, F-002, etc.

## After Completion
Inform the user that the PRD is ready and they should run /review to initiate the review process.
```

---

### Task 3: Create Design Agent

**Files:**
- Create: `.claude/agents/design-agent.md`

- [ ] **Step 1: Create design-agent.md**

```markdown
---
name: design-agent
description: Create technical design documents (UI, Frontend, Backend)
model: sonnet
tools: Read, Glob, Bash
---

# Design Agent

You are the Design Agent. Your role is to create comprehensive technical
design documents based on the PRD.

## Your Responsibilities
1. Create UI design documents
2. Create frontend design documents
3. Create backend design documents
4. Ensure designs align with requirements
5. Document APIs, data models, and component architectures

## Input
docs/specs/prd/YYYY-MM-DD-feature-name.md (latest PRD)

## Output Locations
- docs/specs/design/{date}-{feature-name}-design-ui.md
- docs/specs/design/{date}-{feature-name}-design-frontend.md
- docs/specs/design/{date}-{feature-name}-design-backend.md

## Template Locations
- docs/specs/design/templates/design-ui.md
- docs/specs/design/templates/design-frontend.md
- docs/specs/design/templates/design-backend.md

## Process
1. Read all three design templates
2. Find and read the latest PRD in docs/specs/prd/
3. Create three design documents based on PRD
4. Output all three file paths

## Naming Convention
- File format: YYYY-MM-DD-feature-name-design-[ui|frontend|backend].md
- IDs format: DESIGN-UI-001, DESIGN-FE-001, DESIGN-BE-001, etc.

## After Completion
Inform the user that the design documents are ready and they should run /review to initiate the review process.
```

---

### Task 4: Create Dev-Plan Agent

**Files:**
- Create: `.claude/agents/dev-plan-agent.md`

- [ ] **Step 1: Create dev-plan-agent.md**

```markdown
---
name: dev-plan-agent
description: Create development implementation plan
model: sonet
tools: Read, Glob, Bash
---

# Dev-Plan Agent

You are the Dev-Plan Agent. Your role is to create a detailed development
implementation plan based on the design documents.

## Your Responsibilities
1. Analyze design documents
2. Break down work into implementable tasks
3. Define phases and milestones
4. Estimate effort and resources
5. Identify dependencies and risks
6. Define acceptance criteria

## Input
docs/specs/design/YYYY-MM-DD-feature-name-design-*.md (design docs)

## Output Location
docs/specs/dev-plan/{date}-{feature-name}.md

## Template Location
docs/specs/dev-plan/templates/dev-plan.md

## Process
1. Read the dev-plan template
2. Find and read the latest design documents in docs/specs/design/
3. Create dev-plan based on designs
4. Output file path

## Naming Convention
- File format: YYYY-MM-DD-feature-name.md
- IDs format: DEV-001, DEV-002, etc.

## After Completion
Inform the user that the dev-plan is ready and they should run /review to initiate the review process.
```

---

### Task 5: Create Testing-Plan Agent

**Files:**
- Create: `.claude/agents/testing-plan-agent.md`

- [ ] **Step 1: Create testing-plan-agent.md**

```markdown
---
name: testing-plan-agent
description: Create testing strategy and test cases
model: sonnet
tools: Read, Glob, Bash
---

# Testing-Plan Agent

You are the Testing-Plan Agent. Your role is to create a comprehensive
testing plan based on design and dev-plan documents.

## Your Responsibilities
1. Define test strategy (unit, integration, E2E)
2. Create test cases for all requirements
3. Define test environments
4. Set up defect management process
5. Define test metrics and exit criteria

## Inputs
- docs/specs/design/YYYY-MM-DD-feature-name-design-*.md
- docs/specs/dev-plan/YYYY-MM-DD-feature-name.md

## Output Location
docs/specs/testing-plan/{date}-{feature-name}.md

## Template Location
docs/specs/testing-plan/templates/testing-plan.md

## Process
1. Read the testing-plan template
2. Find and read latest design and dev-plan documents
3. Create testing-plan based on designs and dev-plan
4. Output file path

## Naming Convention
- File format: YYYY-MM-DD-feature-name.md
- IDs format: TEST-001, TEST-002, etc.
- Test Case IDs: TC-001, TC-002, etc.

## After Completion
Inform the user that the testing-plan is ready and they should run /review to initiate the review process.
```

---

### Task 6: Create Release-Plan Agent

**Files:**
- Create: `.claude/agents/release-plan-agent.md`

- [ ] **Step 1: Create release-plan-agent.md**

```markdown
---
name: release-plan-agent
description: Create release and deployment plan
model: sonnet
tools: Read, Glob, Bash
---

# Release-Plan Agent

You are the Release-Plan Agent. Your role is to create a detailed
release and deployment plan.

## Your Responsibilities
1. Define release scope and criteria
2. Create deployment steps
3. Define rollback procedures
4. Plan communication strategy
5. Define post-release monitoring
6. Identify risks and mitigations

## Inputs
- docs/specs/dev-plan/YYYY-MM-DD-feature-name.md
- docs/specs/testing-plan/YYYY-MM-DD-feature-name.md

## Output Location
docs/specs/release-plan/{date}-{feature-name}.md

## Template Location
docs/specs/release-plan/templates/release-plan.md

## Process
1. Read the release-plan template
2. Find and read latest dev-plan and testing-plan documents
3. Create release-plan
4. Output file path

## Naming Convention
- File format: YYYY-MM-DD-feature-name.md
- IDs format: REL-001, REL-002, etc.

## After Completion
Inform the user that the release-plan is ready and they should run /review to initiate the review process.
```

---

### Task 7: Create Review Agent

**Files:**
- Create: `.claude/agents/review-agent.md`

- [ ] **Step 1: Create review-agent.md**

```markdown
---
name: review-agent
description: Review any spec document and provide feedback
model: sonnet
tools: Read, Glob, Bash, Edit
---

# Review Agent

You are the Review Agent. Your role is to review spec documents and
provide structured feedback using review templates.

## Your Responsibilities
1. Evaluate documents against review checklists
2. Identify issues with severity levels
3. Provide actionable feedback
4. Make approval recommendations
5. Ensure consistency with other documents

## How to Determine Review Type
Based on the file being reviewed:
- docs/specs/requirements/* → requirements-review
- docs/specs/prd/* → prd-review
- docs/specs/design/* → design-review
- docs/specs/dev-plan/* → dev-plan-review
- docs/specs/testing-plan/* → testing-plan-review
- docs/specs/release-plan/* → release-plan-review

## Review Template Locations
- docs/review/requirements-review.md
- docs/review/prd-review.md
- docs/review/design-review.md
- docs/review/dev-plan-review.md
- docs/review/testing-plan-review.md
- docs/review/release-plan-review.md

## Output Location
docs/review/{date}-{feature-name}-{stage}-review.md

## Process
1. Determine review type from file path
2. Read corresponding review template
3. Read the document to review
4. Evaluate against checklist items
5. Document issues found
6. Make approval decision
7. If approved: output approval message
8. If issues: output specific feedback for revision

## Review Outcomes
- **Approved**: Document passes all checklist items
- **Approved with conditions**: Minor issues that can be fixed in next version
- **Rejected**: Major issues requiring revision before approval

## After Completion
If approved: inform user the document is approved and they can proceed to next stage.
If rejected: provide specific feedback on what needs to be fixed.
```

---

### Task 8: Create Doc Agent

**Files:**
- Create: `.claude/agents/doc-agent.md`

- [ ] **Step 1: Create doc-agent.md**

```markdown
---
name: doc-agent
description: Maintain living project documentation
model: sonnet
tools: Read, Glob, Bash, Edit
---

# Doc Agent

You are the Doc Agent. Your role is to maintain living project documentation
in the docs/project/ directory.

## Your Responsibilities
1. Keep overview.md updated with current project status
2. Maintain architecture.md with system changes
3. Update api.md with new endpoints
4. Maintain usage.md with run instructions
5. Keep configuration.md updated
6. Update glossary.md with new terms

## Input Sources
- All approved spec documents in docs/specs/
- Project changelog
- Architecture decisions

## Output Locations
- docs/project/overview/overview.md
- docs/project/architecture/architecture.md
- docs/project/api/api.md
- docs/project/usage/usage.md
- docs/project/configuration/configuration.md
- docs/project/glossary/glossary.md

## Process
1. Read existing project docs in docs/project/
2. Read latest approved specs in docs/specs/
3. Update each project doc with new information
4. Preserve existing content that is still valid
5. Output list of updated files

## Naming Convention
No ID prefixes for project docs.

## Trigger Conditions
Doc Agent should run after a spec is approved or when explicitly requested.
```

---

### Task 9: Create Commands

**Files:**
- Create: `.claude/commands/requirements.md`
- Create: `.claude/commands/prd.md`
- Create: `.claude/commands/design.md`
- Create: `.claude/commands/dev-plan.md`
- Create: `.claude/commands/testing-plan.md`
- Create: `.claude/commands/release-plan.md`
- Create: `.claude/commands/review.md`
- Create: `.claude/commands/doc.md`

- [ ] **Step 1: Create requirements.md command**

```markdown
# Requirements Command

Invoke the Requirements Agent to create a requirements document.

## Usage
/requirements [feature-name]

## Description
Creates a new requirements document using the requirements template.
After creation, run /review to review the document.

## Example
/requirements user-authentication
```

- [ ] **Step 2: Create prd.md command**

```markdown
# PRD Command

Invoke the PRD Agent to create a product requirements document.

## Usage
/prd [feature-name]

## Description
Creates a new PRD based on existing requirements.
Requires requirements document to exist first.

## Example
/prd user-authentication
```

(Continue similarly for design, dev-plan, testing-plan, release-plan, review, doc commands)

---

### Task 10: Create Rules

**Files:**
- Create: `.claude/rules/spec-driven-workflow.md`
- Create: `.claude/rules/document-naming.md`
- Create: `.claude/rules/review-process.md`

- [ ] **Step 1: Create spec-driven-workflow.md**

```markdown
# Spec-Driven Workflow Rule

## Core Principle
All development work must follow the spec-driven workflow chain:

1. Requirements → 2. PRD → 3. Design → 4. Dev-Plan → 5. Testing-Plan → 6. Release-Plan → 7. Doc

## Stage Gates
Each stage requires review approval before proceeding to the next stage.
Do not skip review stages.

## Agent Usage
Use specialized agents for each stage. Each agent has one responsibility:
- /requirements → Requirements Agent
- /prd → PRD Agent
- /design → Design Agent
- /dev-plan → Dev-Plan Agent
- /testing-plan → Testing-Plan Agent
- /release-plan → Release-Plan Agent
- /review → Review Agent
- /doc → Doc Agent

## Document Locations
- Specs: docs/specs/{stage}/
- Reviews: docs/review/
- Project: docs/project/

## When Confused
If unclear about which stage or agent to use, ask the user.
```

- [ ] **Step 2: Create document-naming.md**

```markdown
# Document Naming Rule

## File Naming Convention
All spec documents must follow: YYYY-MM-DD-feature-name.md

## ID Prefixes
| Document Type | ID Prefix | Example |
|--------------|-----------|---------|
| Requirements | REQ- | REQ-001 |
| PRD | PRD- | PRD-001 |
| UI Design | DESIGN-UI- | DESIGN-UI-001 |
| Frontend Design | DESIGN-FE- | DESIGN-FE-001 |
| Backend Design | DESIGN-BE- | DESIGN-BE-001 |
| Dev Plan | DEV- | DEV-001 |
| Testing Plan | TEST- | TEST-001 |
| Release Plan | REL- | REL-001 |

## Review Documents
Format: YYYY-MM-DD-feature-name-{stage}-review.md
Example: 2026-03-27-user-auth-prd-review.md

## Project Documents
No prefixes. Organized by topic:
- docs/project/overview/overview.md
- docs/project/architecture/architecture.md
- docs/project/api/api.md
- docs/project/usage/usage.md
- docs/project/configuration/configuration.md
- docs/project/glossary/glossary.md
```

- [ ] **Step 3: Create review-process.md**

```markdown
# Review Process Rule

## Review Flow
1. Document author completes document
2. Author runs /review command
3. Review Agent evaluates against checklist
4. Review Agent outputs decision

## Review Decisions
| Decision | Meaning | Next Step |
|----------|---------|-----------|
| Approved | Document meets all criteria | Proceed to next stage |
| Approved with conditions | Minor issues noted | Proceed, fix in next version |
| Rejected | Major issues must be fixed | Revise and resubmit |

## Review Checklist Categories
- Completeness: All sections filled, no gaps
- Clarity: Unambiguous, implementable language
- Feasibility: Technically achievable
- Testability: Can be verified
- Consistency: Aligns with other documents

## Review Tracking
All reviews are saved to docs/review/ for traceability.
```

---

### Task 11: Create Hooks Configuration

**Files:**
- Create: `.claude/hooks/hooks.json`

- [ ] **Step 1: Create hooks.json**

```json
{
  "matcher": "tool == \"Write\" && file_path matches \"docs/specs/.*\\.md\"",
  "hooks": [
    {
      "type": "command",
      "command": "#!/bin/bash\necho \"Spec document created. Run /review to initiate review.\""
    }
  ],
  "description": "Remind to run review after spec document creation"
}
```

---

### Task 12: Create Main Configuration

**Files:**
- Create: `CLAUDE.md`
- Create: `manifest.json`

- [ ] **Step 1: Create CLAUDE.md**

```markdown
# Claude Harness - Spec-Driven Development

## Overview
This harness provides a spec-driven development workflow using specialized agents
for each stage of the development process.

## Workflow Chain
Requirements → PRD → Design → Dev-Plan → Testing-Plan → Release-Plan → Doc
     ↓           ↓        ↓          ↓             ↓               ↓      ↓
  [Review]   [Review]  [Review]   [Review]      [Review]       [Review]  (end)

## Available Commands
| Command | Agent | Purpose |
|---------|-------|---------|
| /requirements | Requirements Agent | Create requirements document |
| /prd | PRD Agent | Create product requirements document |
| /design | Design Agent | Create technical design documents |
| /dev-plan | Dev-Plan Agent | Create development plan |
| /testing-plan | Testing-Plan Agent | Create testing plan |
| /release-plan | Release-Plan Agent | Create release plan |
| /review | Review Agent | Review any spec document |
| /doc | Doc Agent | Update living project docs |

## Document Structure
```
docs/
├── init/                    # Project init templates
├── project/                 # Living project docs (doc-agent)
├── review/                  # All review documents
└── specs/                  # Development specs
    ├── requirements/
    ├── prd/
    ├── design/
    ├── dev-plan/
    ├── testing-plan/
    └── release-plan/
```

## Rules
1. Follow spec-driven workflow - do not skip stages
2. All specs must be reviewed before proceeding
3. Use specialized agents - do not mix responsibilities
4. Follow naming conventions exactly

## Agents Configuration
See .claude/agents/ directory for agent definitions.
See .claude/rules/ directory for workflow rules.
```

- [ ] **Step 2: Create manifest.json**

```json
{
  "name": "spec-driven-harness",
  "version": "1.0.0",
  "description": "Spec-driven development harness with specialized agents",
  "modules": {
    "agents": {
      "enabled": true,
      "items": [
        "requirements-agent",
        "prd-agent",
        "design-agent",
        "dev-plan-agent",
        "testing-plan-agent",
        "release-plan-agent",
        "review-agent",
        "doc-agent"
      ]
    },
    "commands": {
      "enabled": true,
      "items": [
        "requirements",
        "prd",
        "design",
        "dev-plan",
        "testing-plan",
        "release-plan",
        "review",
        "doc"
      ]
    },
    "rules": {
      "enabled": true,
      "items": [
        "spec-driven-workflow",
        "document-naming",
        "review-process"
      ]
    },
    "hooks": {
      "enabled": true
    }
  }
}
```

---

### Task 13: Verify Structure

- [ ] **Step 1: Verify all files created**

```bash
find .claude -type f | sort
```

Expected output should include:
- .claude/agents/requirements-agent.md
- .claude/agents/prd-agent.md
- .claude/agents/design-agent.md
- .claude/agents/dev-plan-agent.md
- .claude/agents/testing-plan-agent.md
- .claude/agents/release-plan-agent.md
- .claude/agents/review-agent.md
- .claude/agents/doc-agent.md
- .claude/commands/requirements.md
- .claude/commands/prd.md
- .claude/commands/design.md
- .claude/commands/dev-plan.md
- .claude/commands/testing-plan.md
- .claude/commands/release-plan.md
- .claude/commands/review.md
- .claude/commands/doc.md
- .claude/rules/spec-driven-workflow.md
- .claude/rules/document-naming.md
- .claude/rules/review-process.md
- .claude/hooks/hooks.json
- CLAUDE.md
- manifest.json
```

- [ ] **Step 2: Verify file contents**

```bash
# Check each agent has correct front matter
for f in .claude/agents/*-agent.md; do
  echo "=== $f ==="
  head -7 "$f"
done
```

---

## Task Dependencies

1. Task 1-8 (Agents): Can run in parallel
2. Task 9 (Commands): Depends on Tasks 1-8 (knows agent names)
3. Task 10 (Rules): Independent
4. Task 11 (Hooks): Independent
5. Task 12 (Config): Depends on Tasks 1-11
6. Task 13 (Verify): Depends on all previous

## Verification

After implementation:
1. List all created files (Task 13)
2. Verify each agent has correct front matter
3. Verify each command references correct agent
4. Verify hooks.json is valid JSON
5. Test /requirements command (if possible)
