# Requirements Review Calibration Examples

This file contains calibration examples for Requirements evaluation.
Evaluators should review these before evaluating requirements documents.

---

## Example 1: Score 5 (Exceptional)

**Document Excerpt:**

```markdown
## User Story: US-001 - User Registration

**As a** new user,
**I want to** create an account with email and password,
**So that I can** access the platform's features.

### Acceptance Criteria

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| AC-001 | Email must be valid format (RFC 5322) | Unit test with valid/invalid emails |
| AC-002 | Password must be at least 12 characters | Unit test boundary conditions |
| AC-003 | Password must contain uppercase, lowercase, number, special char | Unit test all combinations |
| AC-004 | Confirmation email sent within 30 seconds | Integration test with mock SMTP |
| AC-005 | Account inactive until email verified | Manual verification flow |

### Constraints

- Must comply with GDPR Article 7 (consent)
- Must not store passwords in plaintext (OWASP 2023)
- Email sending handled by external provider (SendGrid)

### Dependencies

- F-002 (Email Service integration)
- External: SendGrid API availability

### Assumptions

- Users have access to email during registration
- SendGrid SLA of 99.9% is acceptable
```

**Why Score 5:**

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Completeness | 5 | All sections filled: user story, ACs, constraints, dependencies, assumptions |
| Clarity | 5 | Each AC is specific and testable; verification methods provided |
| Feasibility | 5 | All criteria achievable within constraints |
| Testability | 5 | Every AC has a clear verification method |
| Consistency | 5 | Aligns with standard requirements template |

**Weighted: 100/100 → APPROVED**

---

## Example 2: Score 3 (Acceptable)

**Document Excerpt:**

```markdown
## User Story: US-001 - User Registration

**As a** new user,
**I want to** create an account,
**So that I can** use the platform.

### Acceptance Criteria

1. User can register with email
2. Password should be secure
3. User gets confirmation email
```

**Why Score 3:**

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Completeness | 3 | Missing constraints, dependencies, assumptions |
| Clarity | 3 | "secure" is vague; ACs not specific enough |
| Feasibility | 3 | Generally achievable but missing details |
| Testability | 2 | "secure" and "confirmation email" not testable as stated |
| Consistency | 4 | Follows basic template structure |

**Weighted: 60/100 → APPROVED WITH CONDITIONS**

**Issues Found:**
- "Password should be secure" - define what "secure" means
- No verification methods for acceptance criteria
- Missing constraint about password storage

---

## Example 3: Score 2 (Needs Improvement)

**Document Excerpt:**

```markdown
## Requirements for User Authentication

TODO: Add user stories

We need some kind of login system.
Should probably have password since that's standard.
Maybe 2FA later?

## User Story: US-001 - Login

**As a** user,
**I want to** log in,
**So that** I can do things.

### Acceptance Criteria

- User can log in
- System is secure
- Works well
```

**Why Score 2:**

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Completeness | 1 | Major sections missing (TODO present) |
| Clarity | 2 | "things", "standard", "works well" are meaningless |
| Feasibility | 2 | Can't assess without clear requirements |
| Testability | 1 | None of the ACs are testable |
| Consistency | 2 | Template partially followed but incomplete |

**Weighted: 40/100 → NEEDS ITERATION**

**Major Issues:**
- TODO left in document
- Acceptance criteria are not testable
- Vague language throughout ("things", "well", "probably")
- Missing all supporting sections

---

## Common Pitfalls to Avoid

### Pitfall 1: Scoring too high on incomplete docs

**Problem:** Seeing familiar structure and assuming content is complete

**Fix:** Read every word. If TODO exists, completeness = 1.

### Pitfall 2: Leniency on vague criteria

**Problem:** "secure" feels like it means something, so scoring it as acceptable

**Fix:** Ask "how would I test this?" If you can't answer, it's not testable.

### Pitfall 3: Giving credit for implied content

**Problem:** "They probably meant X" and scoring based on X

**Fix:** Score only what's written, not what you think they meant.

### Pitfall 4: Consistency inflation

**Problem:** Document follows template, so consistency gets high score

**Fix:** Consistency means alignment with OTHER documents, not just template structure.

---

## Calibration Checklist

Before evaluating a requirements document:

- [ ] Read the full document, don't skim
- [ ] Check each acceptance criterion: "Can I test this?"
- [ ] Look for TODOs or TBDs
- [ ] Verify cross-references exist
- [ ] Check that constraints are specific (not just "security is important")
- [ ] Verify assumptions are stated, not implied
- [ ] Calculate weighted score before making decision
