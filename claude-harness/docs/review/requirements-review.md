# Requirements Review: [Feature Name]

## ID
REQ-[NUMBER]-REVIEW

## Date
[YYYY-MM-DD]

## Reviewer
[Reviewer Name] \<[email@company.com]\>

## Author
[Author Name] \<[email@company.com]\>

## Document Information
| Field | Value |
|-------|-------|
| Requirements Document Version | [X.Y] |
| Related PRD | [PRD-ID, if applicable] |
| Related Design Doc | [DESIGN-ID, if applicable] |
| Jira Epic/Feature | [JIRA-XXX] |

---

## Review Summary
[Provide a brief executive summary of the requirements review. Include overall health of requirements, key concerns, and recommendation summary.]

**Overall Assessment:** [Green/Yellow/Red]

---

## Review Checklist

### 1. Completeness

#### 1.1 User Stories
- [ ] All user roles/personas have corresponding user stories
- [ ] User stories follow INVEST quality criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable)
- [ ] User story acceptance criteria are complete
- [ ] User story priorities are assigned and justified
- [ ] User story estimates are provided

#### 1.2 Functional Requirements
- [ ] All functional requirements are specified
- [ ] Each functional requirement traces to one or more user stories
- [ ] Feature flags/toggles are identified if applicable
- [ ] API requirements are specified (endpoints, methods, data formats)
- [ ] Data handling requirements are complete (CRUD operations, persistence)

#### 1.3 Non-Functional Requirements
- [ ] Performance requirements are specified (response time, throughput, latency)
- [ ] Scalability requirements are defined (concurrent users, data volume)
- [ ] Availability requirements are defined (uptime percentage, maintenance windows)
- [ ] Security requirements are specified (authentication, authorization, encryption, compliance)
- [ ] Reliability requirements are defined (error rates, recovery time)
- [ ] Maintainability requirements are specified (logging, monitoring, alerting)

#### 1.4 Edge Cases and Boundary Conditions
- [ ] Happy path scenarios are covered
- [ ] Error scenarios are documented
- [ ] Edge cases are identified (empty data, maximum limits, timeout conditions)
- [ ] Invalid input handling is specified
- [ ] Concurrent access scenarios are considered
- [ ] Failure modes and recovery are documented

#### 1.5 Dependencies
- [ ] External system dependencies are identified
- [ ] Third-party service dependencies are documented
- [ ] Data dependencies (上游/下游) are specified
- [ ] Integration points are clearly defined
- [ ] Dependency risks are assessed

---

### 2. Clarity

#### 2.1 Requirement Language
- [ ] Requirements use SHALL/MUST for mandatory statements
- [ ] Requirements use SHOULD for recommended items
- [ ] Requirements use COULD/WULD for optional items
- [ ] No ambiguous terms (e.g., "and/or", "etc.", "as appropriate")
- [ ] Requirements avoid implementation details unless necessary

#### 2.2 Traceability
- [ ] Each requirement has a unique identifier
- [ ] Requirements are organized hierarchically (epic > feature > user story > task)
- [ ] Dependencies between requirements are documented
- [ ] Parent-child relationships between requirements are clear

#### 2.3 Conflict Resolution
- [ ] No contradictory requirements exist
- [ ] Conflicting priorities are resolved
- [ ] Overlapping scope is clarified

---

### 3. Feasibility

#### 3.1 Technical Feasibility
- [ ] Proposed solutions are technically implementable
- [ ] Technology stack is appropriate for requirements
- [ ] No vendor lock-in without business justification
- [ ] Technical debt implications are considered

#### 3.2 Resource Feasibility
- [ ] Required skills are available in the team
- [ ] Time constraints are realistic
- [ ] Budget constraints are respected
- [ ] Infrastructure requirements are achievable

#### 3.3 Constraint Compliance
- [ ] Regulatory/compliance requirements are met
- [ ] Security policies are followed
- [ ] Architectural standards are respected
- [ ] Coding standards are considered

---

### 4. Testability

#### 4.1 Verification Criteria
- [ ] Each requirement has clear acceptance criteria
- [ ] Acceptance criteria are objectively measurable
- [ ] Test methods are implied by acceptance criteria
- [ ] Pass/fail conditions are unambiguous

#### 4.2 Measurable Metrics
- [ ] Performance requirements have specific thresholds
- [ ] Availability requirements have defined uptime percentages
- [ ] Error tolerance levels are specified
- [ ] Data accuracy requirements are quantified

#### 4.3 Test Environment Considerations
- [ ] Requirements are testable in expected environments
- [ ] Test data requirements are specified
- [ ] Test tooling needs are identified

---

### 5. Business Value

#### 5.1 Alignment
- [ ] Requirements align with product vision
- [ ] Requirements support business objectives
- [ ] Requirements solve actual user problems
- [ ] ROI considerations are documented

#### 5.2 Prioritization
- [ ] Requirements are prioritized (MoSCoW, Kano, or similar)
- [ ] Priority rationale is documented
- [ ] MVP vs. nice-to-have items are distinguished
- [ ] Technical dependencies affecting priority are noted

---

## Issues Found

| ID | Category | Issue | Severity | Status | Recommendation | Blocked By |
|----|----------|-------|----------|--------|----------------|------------|
| REQ-001 | [Category] | [Issue description] | [Critical/Major/Minor] | [Open/Resolved/WontFix] | [Recommendation] | [ID or N/A] |
| REQ-002 | [Category] | [Issue description] | [Critical/Major/Minor] | [Open/Resolved/WontFix] | [Recommendation] | [ID or N/A] |

**Issue Summary:**
- Critical: [X]
- Major: [X]
- Minor: [X]

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk description] | [High/Medium/Low] | [High/Medium/Low] | [Mitigation strategy] |

---

## Open Questions

| # | Question | Owner | Answer | Resolution |
|---|----------|-------|--------|------------|
| 1 | [Question] | [Owner] | [Answer] | [Resolution] |

---

## Dependencies

### Blocked By
| Dependency | Owner | Status | Impact |
|------------|-------|--------|--------|
| [Dependency] | [Owner] | [Pending/Ready/Blocked] | [Impact description] |

### Blocking
| Dependency | Owner | Status | Impact |
|------------|-------|--------|--------|
| [Dependency] | [Owner] | [Pending/Ready/Blocked] | [Impact description] |

---

## Decision

### Outcome
- [ ] **Approved** - All requirements are complete, clear, feasible, and testable
- [ ] **Approved with Conditions** - Requirements approved with noted issues to address
- [ ] **Rejected** - Requirements require significant revision before approval
- [ ] **Deferred** - Requirements review postponed pending additional information

### Conditions (if Approved with Conditions)
| # | Condition | Owner | Due Date |
|---|-----------|-------|----------|
| 1 | [Condition description] | [Owner] | [YYYY-MM-DD] |

### Rejection Reasons (if Rejected)
- [Reason 1]
- [Reason 2]

---

## Sign-off

| Role | Name | Organization/Team | Date | Signature |
|------|------|-------------------|------|-----------|
| Product Owner | [Name] | [Team] | [YYYY-MM-DD] | __________ |
| Tech Lead | [Name] | [Team] | [YYYY-MM-DD] | __________ |
| QA Lead | [Name] | [Team] | [YYYY-MM-DD] | __________ |
| Security Reviewer | [Name] | [Team] | [YYYY-MM-DD] | __________ |
| Requirements Reviewer | [Name] | [Team] | [YYYY-MM-DD] | __________ |

---

## Appendix

### A. Requirement Traceability Matrix (RTM)

| Requirement ID | Description | User Story | Design Element | Test Case | Status |
|----------------|-------------|------------|----------------|-----------|--------|
| REQ-001 | [Description] | US-001 | [DESIGN-XXX] | [TEST-XXX] | [Complete/In Progress] |

### B. Glossary
| Term | Definition |
|------|------------|
| [Term] | [Definition] |

### C. Reference Documents
| Document | Version | Location |
|----------|---------|----------|
| [Document name] | [X.Y] | [URL/Path] |
