feat(server-collaboration): publish composer uploads on send

- stage channel composer and thread-drawer uploads as private draft attachments instead of immediate artifacts
- materialize only token-confirmed draft files into channel artifacts during message creation
- keep channel attachments, generated artifact references, and send-time validation aligned across frontend and backend
