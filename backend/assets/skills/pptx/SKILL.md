---
name: pptx
description: Use when creating or revising presentation decks (.pptx) such as project briefings, proposal decks, training slides, and executive summaries.
---

# PPTX

Use this skill for PowerPoint-style deliverables inside Poco.

## Apply This Skill When

- the user asks for a slide deck, presentation draft, briefing, or `.pptx`
- the task is to turn documents, spreadsheets, or web research into presentation slides
- the user wants to revise an earlier deck version

## Core Rules

- Put final user-facing decks under `outputs/`.
- Prefer versioned outputs such as `汇报稿_v2.pptx`.
- Keep slides concise: one main point per slide, with a clear audience and purpose.
- If the user provided an existing deck or template, preserve its structure and tone when practical.

## Execution Pattern

1. Identify the presentation audience, goal, and source materials.
2. Convert long-form material into a slide outline before generating the deck.
3. If scripting is needed, write helper code to `.work/pptx/...` first, then execute it with `Bash`.
4. Verify the resulting deck file exists and the slide ordering matches the intended narrative.

## Quality Bar

- The opening slide should clearly state the topic and context.
- The deck should flow from summary to evidence to recommendation.
- If the user later uploads new data or requirements, produce the next deck version instead of overwriting the old one by default.
