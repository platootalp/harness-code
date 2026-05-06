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
