---
name: docx
description: Use when creating or revising Word documents (.docx) such as proposals, plans, notices, contracts, reports, and formatted templates. Also use when an existing .docx file or template must be preserved and updated.
---

# DOCX

Use this skill for Word-document work inside Poco.

## Apply This Skill When

- the user asks for a `.docx` output
- the user uploads an existing `.docx` template or previous version
- the task involves formal written deliverables such as proposals, quotations, notices, plans, or reports

## Core Rules

- If a template or prior `.docx` is provided, treat its formatting as the source of truth.
- Do not flatten a formatted `.docx` to plain text and blindly rebuild it if layout preservation matters.
- Put final files under `outputs/`.
- Prefer versioned outputs such as `实施方案_v2.docx` when revising existing work.

## Execution Pattern

1. Inspect the supplied template, prior version, or source materials first.
2. Decide whether the task is:
   - content-only revision on top of an existing `.docx`, or
   - generation of a new `.docx` deliverable
3. If scripting is needed, write helper code to `.work/docx/...` with file-editing tools first, then run it with `Bash`.
4. Verify the produced `.docx` exists and can be reopened or parsed after generation.

## Quality Bar

- The title, headings, tables, and section structure should match the requested document type.
- Names, dates, quantities, and figures must be synchronized with the latest source materials.
- If a template was provided, preserve its layout as much as the available tooling allows.
- If the user later provides new reference files, treat them as inputs for the next version rather than rewriting history.
