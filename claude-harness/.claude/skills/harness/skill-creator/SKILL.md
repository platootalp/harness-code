---
name: skill-creator
description: Create new skills, modify and improve existing skills, and measure skill performance. Use when creating a skill from scratch, editing, optimizing, running evals, benchmarking with variance analysis, or optimizing descriptions for better triggering accuracy.
---

# Skill Creator Overview

This is a comprehensive guide for creating, testing, and improving skills.

## Core Workflow

1. **Capture intent** - Understand what the skill should do and when it should trigger
2. **Interview and research** - Ask questions about edge cases, formats, success criteria
3. **Write the SKILL.md** - Create the skill with YAML frontmatter and markdown instructions
4. **Create test cases** - Write realistic prompts and save to `evals/evals.json`
5. **Run evaluations** - Spawn subagents (with and without skill), draft assertions, capture timing data
6. **Generate the reviewer** - Use `eval-viewer/generate_review.py` to create an HTML viewer
7. **Read feedback and improve** - Iterate based on user comments
8. **Description optimization** - Optional final step using `scripts.run_loop` to improve triggering

## Key Tools
- `agents/grader.md` - Evaluating assertions against outputs
- `agents/comparator.md` - Blind A/B comparison between outputs
- `agents/analyzer.md` - Analyzing why one version beat another
- `references/schemas.md` - JSON structures for evals
