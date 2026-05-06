---
name: pptx
description: "Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, presentations; reading, parsing, or extracting text from .pptx files; editing, modifying presentations; combining or splitting slide files."
---

# PPTX Skill

## Quick Reference

| Task | Guide |
|------|-------|
| Read/analyze content | `python -m markitdown presentation.pptx` |
| Edit or create from template | Read editing.md |
| Create from scratch | Read pptxgenjs.md |

## Reading Content

```bash
python -m markitdown presentation.pptx
python scripts/thumbnail.py presentation.pptx
```

## Design Principles

- Pick bold, content-informed color palettes
- Use dominant color (60-70% visual weight) with supporting tones
- Dark backgrounds for title slides, light for content
- Commit to a visual motif and repeat across slides
- Every slide needs visual elements - never text-only slides

## Dependencies
- `pip install "markitdown[pptx]"`
- `pip install Pillow`
- `npm install -g pptxgenjs`
- LibreOffice for PDF conversion
