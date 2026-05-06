# Code Quality Reviewer Prompt Template

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

**Only dispatch after spec compliance review passes.**

```
Task tool (superpowers:code-reviewer):
  Use template at requesting-code-review/code-reviewer.md
```

**In addition to standard code quality concerns, check:**
- Does each file have one clear responsibility?
- Are units decomposed for independent testing?
- Did implementation follow the file structure from the plan?
- Did this create new large files or significantly grow existing files?

**Code reviewer returns:** Strengths, Issues (Critical/Important/Minor), Assessment
