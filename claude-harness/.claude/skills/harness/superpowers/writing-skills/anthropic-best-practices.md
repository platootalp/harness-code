# Anthropic Skill Authoring Best Practices

## Core Principles

**Concise is Key**
- Only add context Claude doesn't already have
- Good Skills are concise: ~50 tokens vs 150 tokens for verbose

**Set Appropriate Degrees of Freedom**
- **High freedom**: Text instructions for tasks with multiple valid approaches
- **Medium freedom**: Pseudocode or scripts with parameters
- **Low freedom**: Specific scripts for fragile operations

## Skill Structure

**Naming**: Use gerund form (verb + -ing): "Processing PDFs", "Analyzing spreadsheets"

**Description Requirements**:
- Always write in third person
- Be specific and include key terms
- Include what the Skill does AND when to use it

## Progressive Disclosure

- Keep SKILL.md under 500 lines
- Use separate files: reference.md, examples.md, FORMS.md
