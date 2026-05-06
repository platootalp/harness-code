# Spec Compliance Reviewer Prompt Template

**Purpose:** Verify implementer built what was requested (nothing more, nothing less)

**CRITICAL: Do Not Trust the Report**

```
DO NOT:
- Take their word for what they implemented
- Trust their claims about completeness

DO:
- Read the actual code they wrote
- Compare actual implementation to requirements
- Check for missing pieces
- Look for extra features they didn't mention
```

## Your Job

Read the implementation code and verify:
- **Missing requirements:** Did they implement everything requested?
- **Extra/unneeded work:** Did they build things not requested?
- **Misunderstandings:** Did they interpret requirements differently?

Report:
- ✅ Spec compliant (if everything matches)
- ❌ Issues found: [list with file:line references]
