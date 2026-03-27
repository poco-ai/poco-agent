---
name: pdf
description: Use when creating, revising, converting, merging, or extracting PDF documents, especially when the user needs a final shareable PDF deliverable or wants to inspect an existing PDF.
---

# PDF

Use this skill for PDF-oriented work inside Poco.

## Apply This Skill When

- the user asks for a `.pdf` output
- the task involves converting office content into a final shareable PDF
- the user uploads an existing PDF for extraction, merging, splitting, or revision

## Core Rules

- If both an editable office file and a shareable PDF are useful, prefer generating the editable source first and the PDF second.
- Put final PDF outputs under `outputs/`.
- Prefer versioned outputs such as `汇报稿_v2.pdf` or `实施方案_v3.pdf`.
- If external facts or statistics are used, keep citations real and verifiable.

## Execution Pattern

1. Decide whether the task is PDF creation, conversion, or processing of an existing PDF.
2. Probe tool availability before relying on optional binaries such as `pandoc`, `libreoffice`, or other converters.
3. If scripting is needed, write helper code to `.work/pdf/...` first, then run it with `Bash`.
4. Verify the generated PDF exists and extract or inspect basic content when feasible.

## Quality Bar

- The final PDF should be readable, complete, and consistent with the requested language.
- If page count or page ordering matters, verify it explicitly.
- When revising a previously generated PDF, default to a new versioned file rather than destructive overwrite.
