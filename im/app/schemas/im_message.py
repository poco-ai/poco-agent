from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class InboundMessage:
    provider: str
    destination: str
    message_id: str
    text: str
    sender_id: str | None = None
    # Some providers require a delivery endpoint that differs from the channel identity.
    send_address: str | None = None
    raw: dict[str, Any] | None = None
