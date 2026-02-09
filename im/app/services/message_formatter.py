import json
from typing import Any

from app.core.settings import get_settings


class MessageFormatter:
    def __init__(self) -> None:
        self.settings = get_settings()

    def session_url(self, session_id: str) -> str:
        base = self.settings.frontend_public_url.rstrip("/")
        lng = (self.settings.frontend_default_language or "zh").strip() or "zh"
        return f"{base}/{lng}/chat/{session_id}"

    def format_task_created(
        self, *, session_id: str, run_id: str | None, status: str | None
    ) -> str:
        parts = [
            "已创建任务",
            f"session_id: {session_id}",
        ]
        if run_id:
            parts.append(f"run_id: {run_id}")
        if status:
            parts.append(f"run_status: {status}")
        parts.append(f"前端查看: {self.session_url(session_id)}")
        return "\n".join(parts)

    def format_terminal_notification(
        self,
        *,
        session_id: str,
        title: str | None,
        status: str,
        run_id: str | None,
        last_error: str | None,
    ) -> str:
        clean_title = (title or "").strip()
        header = (
            "任务完成"
            if status == "completed"
            else ("任务失败" if status == "failed" else f"任务结束({status})")
        )
        lines = [header]
        if clean_title:
            lines.append(f"标题: {clean_title}")
        lines.append(f"session_id: {session_id}")
        if run_id:
            lines.append(f"run_id: {run_id}")
        if status == "failed" and last_error:
            err = last_error.strip()
            if len(err) > 800:
                err = err[:800] + "...(truncated)"
            lines.append(f"错误: {err}")
        lines.append(f"前端查看: {self.session_url(session_id)}")
        return "\n".join(lines)

    def format_user_input_request(
        self,
        *,
        request_id: str,
        session_id: str,
        tool_name: str,
        tool_input: dict[str, Any] | None,
        expires_at: str | None,
        title: str | None = None,
    ) -> str:
        lines: list[str] = ["需要你的输入"]
        clean_title = (title or "").strip()
        if clean_title:
            lines.append(f"标题: {clean_title}")
        lines.append(f"session_id: {session_id}")
        lines.append(f"request_id: {request_id}")
        lines.append(f"tool: {tool_name}")
        if expires_at:
            lines.append(f"expires_at: {expires_at}")

        if tool_name == "ExitPlanMode":
            plan = ""
            if isinstance(tool_input, dict):
                plan = str(tool_input.get("plan") or "").strip()
            if plan:
                if len(plan) > 1200:
                    plan = plan[:1200] + "...(truncated)"
                lines.append("")
                lines.append("Plan:")
                lines.append(plan)
            lines.append("")
            lines.append("回复命令：")
            lines.append(f"/approve {request_id}")
            lines.append(f"/reject {request_id}")
            return "\n".join(lines)

        # AskUserQuestion
        questions = []
        if isinstance(tool_input, dict):
            raw = tool_input.get("questions")
            if isinstance(raw, list):
                questions = [q for q in raw if isinstance(q, dict)]

        if questions:
            lines.append("")
            lines.append("问题：")
            for idx, q in enumerate(questions, start=1):
                header = str(q.get("header") or "").strip()
                question = str(q.get("question") or "").strip()
                multi = bool(q.get("multiSelect"))
                if header:
                    lines.append(f"{idx}. {header}")
                if question:
                    lines.append(f"   - {question}")
                lines.append(f"   - 多选: {'是' if multi else '否'}")
                options = q.get("options")
                if isinstance(options, list) and options:
                    lines.append("   - 选项:")
                    for opt in options:
                        if not isinstance(opt, dict):
                            continue
                        label = str(opt.get("label") or "").strip()
                        desc = str(opt.get("description") or "").strip()
                        if not label:
                            continue
                        suffix = f" ({desc})" if desc else ""
                        lines.append(f"     * {label}{suffix}")

        lines.append("")
        lines.append("请使用 JSON 回复（key 为问题文本 question）：")
        example = {"<question>": "<answer>"}
        lines.append(f"/answer {request_id} {json.dumps(example, ensure_ascii=False)}")
        lines.append(f"前端查看: {self.session_url(session_id)}")
        return "\n".join(lines)
