fix(server-channel): name agent direct messages by handle

- Create agent direct-message channels with @handle names and handle-based slugs
- Project existing agent DMs with current handles when listing channels
- Keep newly opened DMs in local channel state before routing to the conversation
- Cover agent DM naming and legacy projection behavior in backend tests
