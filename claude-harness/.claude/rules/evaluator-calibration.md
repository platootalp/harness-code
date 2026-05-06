# Evaluator Calibration Rule

## Why Calibration Matters

An uncalibrated Evaluator tends toward:
- **Leniency bias:** Everything looks "good enough"
- **Inconsistency:** Similar items get different scores
- **Subjectivity:** Personal preferences creep in

Calibration ensures Evaluator judgments are:
- Consistent across similar items
- Aligned with explicit criteria
- Verifiable and reproducible

## Calibration Process

### Phase 1: Initial Setup

1. **Create Calibration Examples**

   For each review type, create 3-5 examples with:
   - Document excerpt (problematic)
   - Expected score
   - Detailed score breakdown

2. **Store Examples**

   ```
   docs/review/calibration/
   ├── requirements-calibration.md
   ├── prd-calibration.md
   ├── design-calibration.md
   ├── dev-plan-calibration.md
   ├── testing-plan-calibration.md
   └── release-plan-calibration.md
   ```

### Phase 2: Before Each Evaluation

1. Read 2-3 calibration examples for the review type
2. Align your judgment with the examples
3. Note any edge cases

### Phase 3: After Each Evaluation

1. Record your judgment in the evaluation metadata
2. Note any uncertainty or edge cases
3. Flag if judgment diverged from calibration

### Phase 4: Periodic Review (Every 10 Evaluations)

1. Analyze judgment patterns
2. Find divergence cases
3. Update prompts or calibration examples
4. Document changes

## Calibration Example Format

```markdown
# {Review Type} Calibration Examples

## Example 1: Score 5 (Exceptional)

**Excerpt:**
{Markdown excerpt from document}

**Why Score 5:**
- Completeness: All sections filled with specific details
- Clarity: No ambiguous language, can be implemented directly
- Feasibility: All claims verifiable and achievable
- Testability: Clear acceptance criteria
- Consistency: Aligns perfectly with other documents

**Score Breakdown:**
| Dimension | Score | Justification |
|-----------|-------|---------------|
| Completeness | 5 | ... |
| Clarity | 5 | ... |
| Feasibility | 5 | ... |
| Testability | 5 | ... |
| Consistency | 5 | ... |

## Example 2: Score 3 (Acceptable)

**Excerpt:**
{Markdown excerpt from document}

**Why Score 3:**
- Completeness: Most sections filled but some gaps
- Clarity: Generally clear but one ambiguous requirement
- ...

## Example 3: Common Pitfall

**Issue:** Overly lenient scoring on incomplete documents
**How to Avoid:** Check each section systematically before scoring
```

## Counteracting Leniency

### Checklist for Skeptical Evaluation

- [ ] Assume the worst-case interpretation
- [ ] Check if each claim is actually verifiable
- [ ] Look for gaps, not just what's present
- [ ] Verify cross-references are accurate
- [ ] Ask: "If I were implementing this, would I know what to do?"
- [ ] Ask: "Is this testable? How would I prove it?"

### Red Flags

| Flag | What It Means | How to Handle |
|------|---------------|---------------|
| TODO left in doc | Incomplete work | Score down on completeness |
| "TBD" without rationale | Unresolved decision | Score down on clarity |
| Vague acceptance criteria | Not testable | Score down on testability |
| Contradicts other doc | Inconsistency | Score down on consistency |

## Score-to-Decision Mapping

| Weighted Score | Decision | Meaning |
|----------------|----------|---------|
| 80-100 | **Approved** | Ready for next stage |
| 60-79 | **Approved with Conditions** | Minor fixes in next version |
| 40-59 | **Needs Revision** | Significant work required |
| <40 | **Rejected** | Major rework required |

## Maintaining Calibration Log

Each evaluation should include:

```markdown
## Calibration Metadata

- Calibration examples reviewed: [list]
- Edge cases encountered: [list]
- Uncertainty noted: [yes/no]
- If yes: [what was uncertain]
- Judgment confidence: [High/Medium/Low]
```

Periodically (monthly or every 50 evaluations):
1. Review all uncertainty notes
2. Check if patterns emerge
3. Update calibration examples if needed
4. Document any prompt changes
