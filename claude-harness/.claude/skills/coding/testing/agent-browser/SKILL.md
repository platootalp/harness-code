---
name: agent-browser
description: Browser automation CLI for AI agents. Use when the user needs to interact with websites, including navigating pages, filling forms, clicking buttons, taking screenshots, extracting data, testing web apps, or automating any browser task.
---

# agent-browser

Fast browser automation CLI for AI agents. Chrome/Chromium via CDP with accessibility-tree snapshots and compact `@eN` element refs.

## Install
```bash
npm i -g agent-browser && agent-browser install
```

## Start here

Before running any `agent-browser` command, load the actual workflow content from the CLI:

```bash
agent-browser skills get core # start here — workflows, common patterns, troubleshooting
agent-browser skills get core --full # include full command reference and templates
```

## Specialized skills

Load a specialized skill when the task falls outside browser web pages:

```bash
agent-browser skills get electron # Electron desktop apps
agent-browser skills get slack # Slack workspace automation
agent-browser skills get dogfood # Exploratory testing / QA / bug hunts
agent-browser skills get vercel-sandbox # Vercel Sandbox microVMs
agent-browser skills get agentcore # AWS Bedrock AgentCore cloud browsers
```

Run `agent-browser skills list` to see everything available.

## Why agent-browser

- Fast native Rust CLI, not a Node.js wrapper
- Works with any AI agent (Cursor, Claude Code, Codex, Continue, Windsurf, etc.)
- Chrome/Chromium via CDP with no Playwright or Puppeteer dependency
- Accessibility-tree snapshots with element refs for reliable interaction
- Sessions, authentication vault, state persistence, video recording
- Specialized skills for Electron apps, Slack, exploratory testing, cloud providers
