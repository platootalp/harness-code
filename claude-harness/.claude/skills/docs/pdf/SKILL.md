---
name: pdf
description: Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs, splitting PDFs, rotating pages, adding watermarks, creating new PDFs, filling PDF forms, encrypting/decrypting PDFs, extracting images, and OCR on scanned PDFs.
---

# PDF Processing Skill

## Overview
This skill handles PDF operations including reading/extracting text/tables, merging, splitting, rotating, watermarking, creating, form filling, encrypting/decrypting, extracting images, and OCR on scanned PDFs.

## Quick Start

```python
from pypdf import PdfReader, PdfWriter
reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")
text = ""
for page in reader.pages:
    text += page.extract_text()
```

## Libraries

- **pypdf**: merge, split, metadata extraction, rotation
- **pdfplumber**: text extraction with layout preservation and table extraction
- **reportlab**: creates PDFs using Canvas or Platypus

## Command-Line Tools

pdftotext (poppler-utils), qpdf, pdftk

## Quick Reference Table

| Task | Tool |
|------|------|
| Merge | pypdf |
| Split | pypdf |
| Extract text | pdfplumber |
| Extract tables | pdfplumber |
| Create | reportlab |
| OCR | pytesseract |
| Fill forms | pdf-lib/pypdf |
