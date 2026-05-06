---
name: llm-wiki
description: Build and maintain a personal knowledge base where an LLM incrementally builds and maintains a structured, interlinked collection of markdown files. Based on Andrej Karpathy's LLM Wiki pattern.
allowed-tools: Read Glob Grep Bash Write Edit
---

# LLM Wiki

Build and maintain a personal knowledge base where the LLM incrementally builds and maintains a structured, interlinked collection of markdown files.

## Core Philosophy

**Instead of RAG (retrieving raw chunks at query time):**

- LLM **reads new sources** and **actively integrates** knowledge into the wiki
- Wiki pages are already synthesized, cross-referenced, and up-to-date
- The wiki is a **persistent, compounding artifact** — cross-references already exist
- One source can update **10-15 wiki pages** in one pass

## Three-Layer Architecture

### Layer 1: Raw Sources
Immutable source documents (articles, papers, images, data). The source of truth.
- Store in `sources/` directory
- Never modify after ingestion

### Layer 2: Wiki
LLM-generated markdown files — the **LLM owns this layer entirely**.
- `wiki/index.md` — content-oriented catalog with links and one-line summaries
- `wiki/log.md` — chronological append-only record of operations
- `wiki/entities/` — entity pages (people, projects, tools)
- `wiki/concepts/` — concept pages (ideas, patterns, techniques)
- `wiki/synthesis/` — synthesis pages (comparisons, analyses)

### Layer 3: Schema
Configuration defining wiki structure and conventions. Lives in `SCHEMA.md` alongside the wiki.

---

## Three Core Operations

### 1. INGEST — Process a New Source

```
When the user says "ingest this article" or "add this to the wiki":
```

**Step 1: Acquire the Source**
- If URL: use WebSearch/WebFetch to retrieve content
- If file path: Read the file
- Save raw source to `sources/` with date prefix: `sources/2026-04-20-article-title.md`

**Step 2: Read and Analyze**
- Read the full source content
- Identify: key entities, main concepts, relationships, claims, and takeaways

**Step 3: Create Summary Page**
- Create `wiki/synthesis/{slug}.md` with:
  - Source citation and date
  - One-paragraph summary
  - Key points (bullet list)
  - Related entities and concepts

**Step 4: Update Entity/Concept Pages**
- For each entity found: update or create `wiki/entities/{name}.md`
- For each concept found: update or create `wiki/concepts/{slug}.md`
- Add cross-references to the new summary page

**Step 5: Update Index**
- Add entry to `wiki/index.md` with:
  - Link to summary page
  - One-line summary
  - Category tags
  - Date ingested

**Step 6: Append to Log**
- Append to `wiki/log.md`:
  ```
  ## [YYYY-MM-DD] ingest | {Title}
  - Source: {path or URL}
  - Entities: {list}
  - Concepts: {list}
  - Pages created/updated: {list}
  ```

### 2. QUERY — Answer a Question

```
When the user asks a question against the wiki:
```

**Step 1: Search Index**
- Read `wiki/index.md`
- Find relevant pages based on keywords

**Step 2: Read Relevant Pages**
- Read all pages identified in Step 1
- For deep queries, also check `wiki/concepts/` and `wiki/entities/`

**Step 3: Synthesize Answer**
- Combine information from multiple pages
- Provide answer with citations: `[source](path)`

**Step 4: File Back (if answer is valuable)**
- If the answer synthesizes multiple sources in a new way:
  - Consider creating a new synthesis page
  - Update relevant entity/concept pages

### 3. LINT — Health Check

```
When the user says "lint the wiki" or "check wiki health":
```

**Step 1: Scan All Pages**
- Use Glob to find all `.md` files in `wiki/`
- Check for:
  - **Contradictions**: Same claim stated differently across pages
  - **Stale claims**: Statements that may be outdated
  - **Orphan pages**: Pages with no incoming links
  - **Missing cross-references**: Related topics without links
  - **Data gaps**: Expected information that's missing

**Step 2: Check Index**
- Verify all pages in `wiki/` are referenced in `wiki/index.md`
- Check for dead links

**Step 3: Report Findings**
- List issues found with file paths and line references
- Suggest fixes for contradictions and stale claims

---

## Wiki Structure Convention

### File Naming
- Entities: `wiki/entities/{lowercase-name-with-dashes}.md`
- Concepts: `wiki/concepts/{descriptive-slug}.md`
- Synthesis: `wiki/synthesis/{source-slug}.md`

### Frontmatter (for all wiki pages)
```yaml
---
title: {Title}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
tags: [tag1, tag2]
See also: [wiki/entities/..., wiki/concepts/...]
---
```

### Cross-Reference Format
```markdown
See [[wiki/entities/entity-name]] for details.
Related: [[wiki/concepts/concept-name]]
```

---

## Log Format

All operations append to `wiki/log.md`:

```
## [YYYY-MM-DD] ingest | {Title}
## [YYYY-MM-DD] query | {Question summary}
## [YYYY-MM-DD] lint | {Issues found: N}
```

---

## Why This Works

> "LLMs don't get bored, don't forget to update a cross-reference, and can touch 15 files in one pass."

Traditional RAG retrieves raw chunks at query time — the knowledge is never really "digested." LLM Wiki creates a **compounding artifact** where:
- Synthesis already done
- Cross-references already created
- Good answers feel like talking to someone who has read everything

---

## Recommended Tools

- **qmd**: Wiki search (BM25/vector with LLM re-ranking, CLI and MCP server)
- **Obsidian Web Clipper**: Convert web articles to markdown
- **Obsidian**: IDE with graph view, Dataview plugin for frontmatter queries
