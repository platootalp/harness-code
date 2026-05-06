# Claude Harness - Spec-Driven Development

## Overview
This harness provides a spec-driven development workflow using specialized agents
for each stage of the development process, applying **harness engineering best practices**
from Anthropic's experience with long-running AI applications.

## Core Principles

### 1. Multi-Agent Separation
**Separate the agent doing work from the agent judging it.**
Agents inherently praise their own outputs. A standalone Evaluator can be tuned to be
skeptical — far easier than making a generator critical of its own work.

### 2. Three-Agent System
- **Planner**: Expands simple prompts into full product specs (high-level design)
- **Generator**: Works in sprints, implements features against agreed contracts
- **Evaluator**: Tests via appropriate tools, grades against concrete criteria

### 3. Sprint Contracts
Before each work chunk, Generator and Evaluator negotiate what "done" looks like.
This bridges high-level spec to testable implementation.

### 4. Iterative Refinement
Multiple iteration cycles with feedback flow from Evaluator back to Generator.
Strategic decisions: refine if trending well, pivot if approach failing.

### 5. Simplify as Models Improve
Every component encodes assumptions about what the model can't do. Regularly
stress-test these assumptions. The space of interesting harness combinations
doesn't shrink — it moves.

## Workflow Chain

```
User → Planner → Sprint Contract → Generator → Evaluator → [Decision]
                                          ↑           ↓
                                          └── feedback ←┘
                                                    ↓ (if approved)
                                               Doc Agent
                                                    ↓
                                                Release
```

Each stage includes Sprint Contract negotiation and Evaluator review.

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

## New Agents (Best Practices)

| Agent | Purpose | Key Files |
|-------|---------|-----------|
| Planner Agent | Expand prompts to specs, high-level design | planner-agent.md |
| Evaluator Agent | Independent calibrated evaluation | evaluator-agent.md |

## Review Decisions

| Decision | Score | Next Step |
|----------|-------|-----------|
| Approved | 80-100 | Proceed to next stage |
| Approved with Conditions | 60-79 | Proceed, fix in next version |
| Needs Iteration | 40-59 | Return to Generator for refinement |
| Rejected | <40 | Major rework required |

## Document Structure
```
docs/
├── init/                    # Project init templates
├── project/                 # Living project docs (doc-agent)
├── review/                  # All review documents
│   └── calibration/         # Evaluator calibration examples
├── specs/                  # Development specs
│   ├── requirements/
│   ├── prd/
│   ├── design/
│   ├── dev-plan/
│   ├── testing-plan/
│   ├── release-plan/
│   └── sprint-contracts/    # Sprint contract documents
```

## Rules
1. Follow spec-driven workflow - do not skip stages
2. All specs must be reviewed before proceeding
3. Use specialized agents - do not mix responsibilities
4. Follow naming conventions exactly

## Agents Configuration
See .claude/agents/ directory for agent definitions.
See .claude/rules/ directory for workflow rules.
