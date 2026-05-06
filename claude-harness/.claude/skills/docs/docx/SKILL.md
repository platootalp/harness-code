---
name: docx
description: "Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files). Triggers include: any mention of 'Word doc', 'word document', '.docx', or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads."
---

# DOCX Skill

This skill handles Word document creation, editing, and analysis using .docx files (ZIP archives containing XML).

## Core Workflows

**Creating New Documents:** Use docx-js (npm install -g docx) with JavaScript. Set page size explicitly (US Letter: 12240x15840 DXA), use `LevelFormat.BULLET` for lists (never unicode), and apply dual widths for tables with both `columnWidths` and cell `width` set to DXA values.

**Editing Existing Documents:** Unpack → Edit XML → Repack. Use `python scripts/office/unpack.py`, edit directly with the Edit tool, then `python scripts/office/pack.py`.

## Critical Rules

- Always set page size explicitly (defaults to A4, not US Letter)
- Use DXA for widths, never PERCENTAGE
- Tables need dual widths (columnWidths + cell width)
- PageBreak must be inside a Paragraph
- ImageRun requires `type` parameter
- Use ShadingType.CLEAR for table backgrounds
- Never use tables as dividers

## XML Editing

For tracked changes, use `<w:ins>` and `<w:del>` elements. Comments require running `comment.py` then adding markers where commentRangeStart/End are siblings of `<w:r>`, never inside them.

## Dependencies

pandoc (text extraction), docx npm package, LibreOffice (PDF conversion), Poppler (image export).
