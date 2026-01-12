import httpx

from app.schemas.callback import AgentCallbackRequest


class CallbackClient:
    def __init__(self, callback_url: str, timeout: float = 30.0):
        self.callback_url = callback_url
        self.timeout = timeout

    async def send(self, report: AgentCallbackRequest) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.callback_url,
                    json=report.model_dump(mode="json"),
                )
                return response.is_success
        except httpx.RequestError:
            return False
