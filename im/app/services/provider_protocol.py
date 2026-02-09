from typing import Protocol


class MessageProvider(Protocol):
    provider: str
    max_text_length: int

    @property
    def enabled(self) -> bool: ...

    async def send_text(self, *, destination: str, text: str) -> None: ...
