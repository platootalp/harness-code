# Code Reviewer Prompt Template

Use this template when dispatching a code reviewer subagent.

**Purpose:** Evaluate implementation quality, design, and correctness.

```
Task tool (superpowers:code-reviewer):
  Use template
  
  WHAT_WAS_IMPLEMENTED: [from implementer's report]
  PLAN_OR_REQUIREMENTS: Task N from [plan-file]
  BASE_SHA: [commit before task]
  HEAD_SHA: [current commit]
  DESCRIPTION: [task summary]
```

**Code reviewer returns:** Strengths, Issues (Critical/Important/Minor), Assessment
