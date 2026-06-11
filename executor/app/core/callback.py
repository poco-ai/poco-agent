import httpx

from app.schemas.callback import AgentCallbackRequest
from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    get_request_id,
    get_trace_id,
)


class CallbackClient:
    def __init__(
        self,
        callback_url: str,
        callback_token: str = "",
        timeout: float = 30.0,
    ):
        self.callback_url = callback_url
        self.callback_token = callback_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {
            "X-Request-ID": get_request_id() or generate_request_id(),
            "X-Trace-ID": get_trace_id() or generate_trace_id(),
        }
        if self.callback_token:
            headers["Authorization"] = f"Bearer {self.callback_token}"
        return headers

    async def send(self, report: AgentCallbackRequest) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.callback_url,
                    json=report.model_dump(mode="json"),
                    headers=self._headers(),
                )
                return response.is_success
        except httpx.RequestError:
            return False
