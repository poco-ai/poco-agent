---
name: xlsx
description: Use when creating, revising, or analyzing spreadsheets such as quotation sheets, budgets, trackers, tabular reports, or Excel workbooks (.xlsx, .xlsm, .csv).
---

# XLSX

Use this skill for spreadsheet work inside Poco.

## Apply This Skill When

- the user asks for an Excel workbook, quotation sheet, budget, tracker, or tabular report
- the task centers on `.xlsx`, `.xlsm`, `.csv`, or `.tsv` files
- the user wants spreadsheet outputs to be revised across multiple turns

## Core Rules

- Put final user-facing files under `outputs/`.
- Prefer versioned outputs such as `报价单_v2.xlsx`.
- Keep numeric values numeric; do not silently write numbers as text.
- If the workbook contains money, use explicit currency or financial number formats.

## Execution Pattern

1. Read the latest requirements, uploads, and earlier workbook versions.
2. If scripting is needed, prefer Python with workbook-friendly libraries that are actually available in the sandbox.
3. Write helper code to `.work/xlsx/...` with file-editing tools first, then run it with `Bash`.
4. Reopen the generated workbook in code and verify the expected sheets, ranges, and key values exist.

## Quality Bar

- Quotes, totals, taxes, discounts, and subtotals must be internally consistent.
- Formulas should be explicit and easy to inspect.
- For external data fetched from the web, include a source sheet or source columns when practical.
- When the user sends new source files later, produce the next workbook version instead of overwriting the previous result by default.
