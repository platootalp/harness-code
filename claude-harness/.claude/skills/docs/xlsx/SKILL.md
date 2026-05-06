---
name: xlsx
description: "Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to: open, read, edit, or fix an existing .xlsx, .xlsm, .csv, or .tsv file; create a new spreadsheet; or convert between tabular file formats."
---

# SKILL.md - Spreadsheet Operations

## Overview
This skill handles spreadsheet file operations including creating, editing, reading, and analyzing .xlsx, .xlsm, .csv, and .tsv files.

## Color Coding (Financial Models)
- **Blue text**: Hardcoded inputs
- **Black text**: Formulas and calculations
- **Green text**: Internal worksheet links
- **Red text**: External file links
- **Yellow background**: Key assumptions needing attention

## Formula Rules
Use Excel formulas, NOT hardcoded values. Always let Excel calculate totals, percentages, ratios, and differences.

## Workflow
1. Choose tool: pandas for data, openpyxl for formulas/formatting
2. Create or load workbook
3. Modify cells, add formulas, apply formatting
4. Save file
5. Recalculate formulas using: `python scripts/recalc.py output.xlsx`
