PROMPT_APPEND_BASE = """
Execution policy:
- If MCP servers or Skills are available and relevant, proactively use them.
- Prefer Skill and MCP capabilities over manual reimplementation when they can solve the task directly.
""".strip()

PROMPT_APPEND_BROWSER_ENABLED = """
Browser capability note:
- Built-in browser capability is enabled for this task.
- Use browser tools when web inspection or web interaction helps.
""".strip()


def build_prompt_appendix(*, browser_enabled: bool) -> str:
    """Build the static prompt appendix for current capability flags."""
    if browser_enabled:
        return f"{PROMPT_APPEND_BASE}\n\n{PROMPT_APPEND_BROWSER_ENABLED}"
    return PROMPT_APPEND_BASE
