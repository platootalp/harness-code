---
name: mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).
---

# MCP Server Development Guide

## Overview
This guide helps create MCP (Model Context Protocol) servers enabling LLMs to interact with external services through well-designed tools.

## Four-Phase Process

### Phase 1: Research & Planning
- Study the MCP specification at `modelcontextprotocol.io`
- Review framework docs (TypeScript SDK or Python SDK)
- Prioritize comprehensive API coverage
- Use descriptive tool naming with consistent prefixes

### Phase 2: Implementation
- **Recommended Stack**: TypeScript with Streamable HTTP (remote) or stdio (local)
- Use Zod (TypeScript) or Pydantic (Python) for input schemas
- Include `outputSchema` and annotations (`readOnlyHint`, `destructiveHint`, etc.)
- Return structured content alongside text descriptions

### Phase 3: Review & Test
- Verify no duplicated code
- Ensure consistent error handling with actionable messages
- Build and test using MCP Inspector

### Phase 4: Create Evaluations
- Develop 10 independent, read-only, complex questions
- Each question should have a single verifiable answer
- Format as XML with `<question>` and `<answer>` elements

## Key Documentation References
- MCP Best Practices guide
- Language-specific implementation guides (TypeScript/Python)
- Evaluation guide for testing effectiveness
