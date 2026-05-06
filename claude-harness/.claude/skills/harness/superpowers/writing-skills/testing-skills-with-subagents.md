# Testing Skills With Subagents

**Core Concept:** Skill creation IS test-driven development.

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

## The RED-GREEN-REFACTOR Cycle

- **RED:** Run scenarios WITHOUT skill, watch agent fail, document exact rationalizations
- **GREEN:** Write minimal skill addressing specific failures, verify agent now complies
- **REFACTOR:** Identify NEW rationalizations after GREEN testing, close loopholes

## Key Requirements

- Must run baseline tests BEFORE writing skill (don't skip RED)
- Use pressure scenarios with 3+ combined pressures (time, sunk cost, authority, exhaustion)
- Force explicit A/B/C choices, not open-ended questions

## Pressure Types to Test

- Time pressure (deadlines, deploy windows)
- Sunk cost ("wasted" hours)
- Authority (senior overrides)
- Economic (job/promotion stakes)
- Exhaustion (end of day)
- Social (looking dogmatic)

## Bulletproof Skill Indicators

Agent chooses correct option under maximum pressure, cites skill sections.
