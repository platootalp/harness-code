# Review Process Rule

## Review Flow
1. Document author completes document
2. Author runs /review command
3. Review Agent evaluates against checklist
4. Review Agent outputs decision

## Review Decisions

| Decision | Weighted Score | Meaning | Next Step |
|----------|----------------|---------|-----------|
| Approved | 80-100 | Document meets all criteria | Proceed to next stage |
| Approved with Conditions | 60-79 | Minor issues noted | Proceed, fix in next version |
| Needs Iteration | 40-59 | Substantial revision required | Return to Generator for refinement |
| Rejected | <40 | Major issues must be fixed | Major rework required; may need Planner escalation |

## Scoring Dimensions

| Dimension | Weight | Score Range | What to Evaluate |
|-----------|--------|-------------|------------------|
| Completeness | 25% | 1-5 | All sections filled, no TODOs unexplained |
| Clarity | 25% | 1-5 | Unambiguous language, implementable without clarification |
| Feasibility | 20% | 1-5 | Technically achievable within constraints |
| Testability | 15% | 1-5 | Can be verified through concrete tests |
| Consistency | 15% | 1-5 | Aligns with other approved documents |

## Weighted Score Calculation

```
Weighted Score = (Completeness×0.25 + Clarity×0.25 + Feasibility×0.20 + Testability×0.15 + Consistency×0.15) × 20
```

Example: Scores of 4,4,3,3,4 = (4×0.25 + 4×0.25 + 3×0.20 + 3×0.15 + 4×0.15) × 20 = 72 → Approved with Conditions

## Review Checklist Categories
- Completeness: All sections filled, no gaps
- Clarity: Unambiguous, implementable language
- Feasibility: Technically achievable
- Testability: Can be verified
- Consistency: Aligns with other documents

## Review Tracking
All reviews are saved to docs/review/ for traceability.
