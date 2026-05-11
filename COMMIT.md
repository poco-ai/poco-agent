feat(channel-tasks): add task delegation event contract

- Add channel-local task numbers and agent identity assignee fields with migration backfill
- Return creator and assignee summaries from channel task responses
- Emit structured task events for create, assignment, status, update, and comment activity
- Parse task event numbers and assignee summaries in frontend lightweight event rows
- Record the channel task collaboration constitution and phase progress
