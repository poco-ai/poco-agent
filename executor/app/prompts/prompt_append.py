PROMPT_APPEND_BASE = """
Execution policy:
- If MCP servers or Skills are available and relevant, proactively use them.
- Prefer Skill and MCP capabilities over manual reimplementation when they can solve the task directly.
""".strip()

PROMPT_APPEND_OFFICE_ASSISTANT = """
Office assistant policy:
- For office-oriented tasks, default to a chat-first workflow: ask only for missing materials that block progress, then move toward concrete deliverables.
- Reuse files, links, and earlier deliverables from the current session before asking the user to repeat information.
- Prefer deliverables under outputs/ and treat inputs/ as read-only unless the user explicitly asks for in-place edits.
- Prefer versioned outputs such as *_v2.docx, *_v3.xlsx, *_v2.pptx, or *_v2.pdf instead of destructive overwrite unless the user explicitly requests overwrite.
- When helper scripts are needed, write helper code to hidden working files such as .work/ or .tmp/ with file-editing tools first, then execute them with Bash so the process view can show both the code and the command.
- Keep progress updates concise and concrete: what you produced, which references you used, and what the next useful step is.
""".strip()

PROMPT_APPEND_BROWSER_ENABLED = """
Browser capability note:
- Built-in browser capability is enabled for this task.
- Use browser tools when web inspection or web interaction helps.
""".strip()

PROMPT_APPEND_MEMORY_ENABLED = """
Memory capability note:
- Built-in user-level memory tools are enabled for this task.
- Search relevant memory before re-asking the user, and store durable preferences/facts when useful.
""".strip()


def build_prompt_appendix(
    *, browser_enabled: bool, memory_enabled: bool = False
) -> str:
    """Build the static prompt appendix for current capability flags."""
    sections = [PROMPT_APPEND_BASE, PROMPT_APPEND_OFFICE_ASSISTANT]
    if memory_enabled:
        sections.append(PROMPT_APPEND_MEMORY_ENABLED)
    if browser_enabled:
        sections.append(PROMPT_APPEND_BROWSER_ENABLED)
    return "\n\n".join(sections)
