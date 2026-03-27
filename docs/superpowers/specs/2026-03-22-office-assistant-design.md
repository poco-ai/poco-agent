# Poco Office Assistant Design

- Status: Approved in conversation
- Date: 2026-03-22
- Branch: `codex/office-assistant-spec`
- Scope: Poco existing open-source product, chat-first office assistant experience for internal company deployment

## 1. Overview

This design defines a new product layer on top of Poco's existing execution platform so that the system behaves like a Chinese, chat-first office assistant for internal users.

The target experience is:

- users stay inside one conversation
- users upload Word, Excel, PPT, PDF, and web references as needed
- the assistant generates formal deliverables such as quotation sheets, proposals, and presentation drafts
- later turns can use newly uploaded materials to produce `v2`, `v3`, and newer versions
- users can always identify the latest version, preview or download it, and inspect how it was produced inside the sandbox

The first release does not require strict in-place editing of the same source Office file. Versioned regeneration is acceptable and is the primary strategy.

## 2. Product Goal

Build an internal "Manus-like" office assistant on top of Poco, optimized for:

- Chinese conversation as the default interaction language
- office deliverables rather than software engineering output
- transparent sandbox execution with visible commands and scripts
- iterative document production inside a single chat session

The product should feel like an assistant continuously advancing a piece of work, not like an engineering console exposing raw tools.

## 3. Goals

### 3.1 Primary Goals

- Support chat-first creation of Word, Excel, and PPT deliverables.
- Support multi-turn refinement with new uploaded files and links.
- Preserve prior versions and highlight the latest version.
- Make execution process visible through terminal and tool detail viewers.
- Reuse the current sandbox, browser, tool execution, workspace export, and document preview foundations.

### 3.2 Secondary Goals

- Distinguish formal deliverables from reference inputs.
- Let users inspect the process for a selected deliverable version instead of viewing all tool activity at once.
- Keep the first release suitable for intranet deployment with moderate server resources.

## 4. Non-Goals

The first release will not aim to provide:

- true desktop-level computer use
- strict in-place editing of the same Office binary file
- BPM-style workflow builders
- multi-user collaborative editing
- full enterprise-grade permissions and audit features
- fully automated skill orchestration beyond current Poco capabilities

## 5. Existing Foundation To Reuse

The current repository already provides most of the execution substrate needed for this product:

- chat session and attachment flow
  - `frontend/features/chat`
  - `frontend/features/task-composer`
- structured tool execution persistence
  - `backend/app/models/tool_execution.py`
  - `backend/app/services/tool_execution_service.py`
- right-side execution layout
  - `frontend/features/chat/components/layout/execution-container.tsx`
  - `frontend/features/chat/components/layout/desktop-execution-layout.tsx`
- process detail viewers
  - `frontend/features/chat/components/execution/computer-panel/terminal-viewer.tsx`
  - `frontend/features/chat/components/execution/computer-panel/generic-tool-viewer.tsx`
- workspace export and manifest-driven file listing
  - `executor_manager/app/services/workspace_export_service.py`
  - `backend/app/api/v1/sessions.py`
- file preview infrastructure for Office and related formats
  - `frontend/features/chat/components/execution/file-panel/document-viewer/index.tsx`

This project should add an office-assistant product layer, not rebuild the runtime.

## 6. Product Principles

### 6.1 Chat First

Users should not need to configure workflows before the assistant can help. The assistant should accept requests, ask for missing materials when needed, and keep the conversation centered on progress.

### 6.2 Deliverable First

The primary unit of value is the deliverable, not the file tree and not the tool log.

### 6.3 Version Friendly

`v2`, `v3`, and newer files are acceptable. The product must make version identity obvious rather than pretending old and new files are the same binary.

### 6.4 Transparent Execution

Users should be able to inspect commands, Python scripts, browser steps, and file operations that produced the output. Transparency builds trust.

### 6.5 Chinese Default

The office-assistant experience should be Chinese-first in copy and interaction framing, while preserving the existing internationalization architecture.

## 7. User Experience Design

## 7.1 Core Interaction Model

Each chat session acts as a persistent workspace for one evolving piece of work. Inside the same session, the assistant can:

- read new user instructions
- consume newly uploaded reference files
- inspect web links
- generate new Office deliverables
- regenerate newer versions of existing deliverables

The user experience should not require the user to explicitly define a workflow. The system should infer whether the user is creating a new deliverable or continuing work on an existing one.

## 7.2 Main Layout

Reuse the existing `chat + right panel` layout.

### Left Side

- standard chat timeline
- user messages with attachments
- assistant messages with progress-oriented summaries
- assistant messages containing deliverable cards

### Right Side

Reuse the current two-panel concept, but reinterpret it:

- `Artifacts` becomes a deliverable-oriented panel
- `Computer` becomes a process-oriented panel

The product language exposed to end users should gradually shift from engineering terms such as "artifacts" toward office-oriented terms such as "deliverables" and "process".

## 7.3 Assistant Message Structure

Each important assistant turn should present four layers:

1. brief natural-language summary
2. deliverable cards
3. reference summary
4. next-step suggestion

Example:

- I generated a quotation sheet and an implementation proposal based on your latest materials.
- Deliverables:
  - `报价单 v2.xlsx`
  - `实施方案 v2.docx`
- References used:
  - `客户需求表.xlsx`
  - `招标说明.docx`
  - latest pricing note from the chat
- Next steps:
  - add a remarks sheet
  - generate a PPT draft

## 7.4 Deliverable Cards

Each deliverable card should support:

- preview
- download
- view process
- view previous version

The chat area should emphasize deliverables, not raw tool chains. Raw tool summaries can remain available but should no longer dominate the message body.

## 7.5 Right Panel Design

### Deliverables View

The existing file panel should be reshaped into three conceptual groups:

- Current Deliverables
- Reference Inputs
- All Files

The preview area should default to the latest selected deliverable version.

### Process View

The existing computer panel should default to the process of the selected deliverable version, not to all session activity.

The user should still be able to switch to full-session process history when needed.

## 8. Domain Model

The first release should introduce a lightweight deliverable model in the backend.

## 8.1 Reference Inputs

Reference inputs are all materials provided or referenced by the user:

- uploaded Office files
- uploaded PDFs
- uploaded text documents
- web links
- previously generated deliverable versions used as source material

Reference inputs are not themselves considered formal deliverables by default.

A previously generated deliverable version can appear in two roles at the same
time:

- as a historical deliverable version in the deliverable timeline
- as a reference input for a newer deliverable version

Using a prior deliverable version as source material must not remove or
reclassify its original deliverable identity.

## 8.2 Deliverables

`deliverables` represents a logical output object such as:

- quotation sheet
- implementation proposal
- presentation draft

Suggested fields:

- `id`
- `session_id`
- `kind` such as `docx`, `xlsx`, `pptx`
- `logical_name`
- `latest_version_id`
- `status` such as `draft`, `active`, `superseded`
- `created_at`
- `updated_at`

Recommended persistence invariant:

- one logical deliverable per `(session_id, kind, logical_name)`

## 8.3 Deliverable Versions

`deliverable_versions` represents concrete generated files such as `报价单 v2.xlsx`.

Suggested fields:

- `id`
- `deliverable_id`
- `session_id`
- `run_id`
- `source_message_id`
- `version_no`
- `file_path`
- `file_name`
- `mime_type`
- `input_refs_json`
- `related_tool_execution_ids_json`
- `detection_metadata_json`
- `created_at`

The first release can store input references and related tool execution ids as JSON fields to avoid introducing unnecessary relational complexity.

`run_id` refers to the existing Poco execution-cycle identifier already used
across backend, executor manager, and executor callbacks for a single run of
work inside a session. It is not a new concept introduced by this design.

`source_message_id` refers to the user-authored message that triggered the run
which produced this version. If the version is created by a scheduled or
non-user-triggered run with no direct user message, this field may be null.

Recommended `input_refs_json` shape:

```json
{
  "file_refs": [
    {
      "path": "inputs/customer_requirements.xlsx",
      "ref_type": "upload",
      "message_id": 123
    },
    {
      "path": "outputs/quotation_v1.xlsx",
      "ref_type": "deliverable_version",
      "deliverable_version_id": "uuid"
    }
  ],
  "web_refs": [
    {
      "url": "https://example.com/spec",
      "message_id": 124
    }
  ],
  "message_refs": [123, 124]
}
```

Recommended `related_tool_execution_ids_json` shape:

```json
{
  "strong": ["uuid-1", "uuid-2"],
  "moderate": ["uuid-3"]
}
```

Recommended `detection_metadata_json` shape:

```json
{
  "confidence": 0.93,
  "normalized_logical_name": "quotation",
  "candidate_rank": 1,
  "same_run_candidates": [
    {
      "file_path": "outputs/quotation_v2.xlsx",
      "confidence": 0.93
    }
  ]
}
```

## 8.4 Lifecycle Invariants

The first release should define the following lifecycle rules explicitly:

- deliverable detection must be idempotent for the same completed run
- repeated callback retries or repeated detection invocations must not create
  duplicate logical deliverables or duplicate deliverable versions
- `latest_version_id` must be derived from the highest committed
  `deliverable_versions.version_no` for a deliverable, not from wall-clock
  detection completion order
- `version_no` must be assigned transactionally inside the backend when a new
  version record is created

Recommended persistence invariant for deliverable versions:

- one version record per `(session_id, run_id, file_path)` in phase 1

This is intentionally conservative: if the same run is processed twice, the
backend should upsert rather than insert again.

## 9. Deliverable Detection

Deliverable detection should be rule-based in the first release.

## 9.1 Candidate Selection

Prioritize these file types as deliverable candidates:

- `.docx`
- `.xlsx`
- `.pptx`
- `.pdf` when the file is produced by the current run as a user-facing export

Exclude:

- scripts
- logs
- hidden files
- temporary tool outputs
- screenshots
- raw uploaded references

Exception:

- if a user-uploaded Office or PDF file is materially modified during the
  current run and is presented as the user-facing result, it may be promoted
  from pure reference input to a deliverable version for that run

## 9.2 Version Detection

Prefer files that are:

- added in the current run
- modified in the current run
- referenced by structured tool inputs or outputs
- clearly named as user-facing documents

When a single run produces multiple Office or PDF outputs, each surviving
candidate is evaluated independently and may become:

- a new logical deliverable, or
- a new version of an existing logical deliverable

The grouping key for this decision is:

- `session_id`
- normalized `logical_name`
- file kind / extension family

If the same run produces multiple files that normalize to the same grouping key,
the highest-confidence candidate becomes the primary detected version for that
key and the remaining candidates are recorded in `detection_metadata_json` for
debugging and possible future UI disclosure.

`latest_version_id` must then point to the version with the highest committed
`version_no` for that logical deliverable.

## 9.3 Logical Name Normalization

Normalize file names to merge versions of the same deliverable:

- strip common version suffixes such as `v2`, `v3`, `final`, `修订版`, timestamps
- keep the normalized base name as `logical_name`
- separate objects by extension to avoid merging `报价单.docx` and `报价单.xlsx`

The first release should use a deterministic, rule-based normalization pipeline:

1. lowercase the base file name
2. remove the extension
3. trim surrounding whitespace and punctuation
4. remove common suffix patterns at the end of the name, including:
   - `v\d+`
   - `_v\d+`
   - `-v\d+`
   - `final`
   - `final-\d+`
   - `修订版`
   - `最终版`
   - `_?\d{8}`
   - `_?\d{14}`
5. collapse repeated separators such as `_`, `-`, and spaces
6. trim again

Examples:

- `报价单_v2.xlsx` -> `报价单`
- `报价单-final.xlsx` -> `报价单`
- `方案_修订版.docx` -> `方案`
- `报价单_20260322.xlsx` -> `报价单`

If normalization results in an empty string, fall back to the original base
name without extension.

## 9.4 Tool Linkage

When creating a deliverable version, store related tool execution ids based on:

- direct file path match in `Write`, `Edit`, `Read`
- file path or file name appearing in `Bash` input or output
- close temporal neighbors in the same run when part of the same generation chain

The first release should only include strongly and moderately related tool executions in the deliverable process view.

## 10. Backend Design

## 10.1 New Models

Add:

- `backend/app/models/deliverable.py`
- `backend/app/models/deliverable_version.py`

Add matching repositories, schemas, and services following current Poco backend layering.

## 10.2 Detection Service

Add a backend service such as:

- `backend/app/services/deliverable_detection_service.py`

Responsibilities:

- read workspace manifest for a completed run
- inspect file changes from session state
- inspect tool executions for the run
- detect deliverable candidates
- create or extend logical deliverables
- create deliverable version records
- set `latest_version_id`
- apply idempotent upsert rules for callback retries and repeated detection

## 10.3 Trigger Point

The first release should use one explicit trigger path only:

- executor manager forwards the completed callback with workspace export metadata
- backend updates the session with `workspace_manifest_key`,
  `workspace_files_prefix`, and related export fields
- backend then invokes deliverable detection for the terminal run associated
  with that callback

This keeps detection on the backend side, after workspace export is ready, and
avoids introducing executor-side deliverable state for phase 1.

At detection time, the backend must have:

- workspace manifest key
- file list
- completed run metadata
- tool execution records

Detection should run asynchronously from the user-facing callback response path,
but it must remain part of the same post-run completion pipeline.

If detection fails after the callback response has already completed:

- the session and run remain valid
- workspace artifacts remain available through the existing manifest/file flow
- the backend should record the detection failure for retry or operator
  inspection
- the frontend should fall back to the current artifacts behavior for that run

## 10.4 APIs

Suggested session-scoped endpoints:

- `GET /sessions/{session_id}/deliverables`
- `GET /sessions/{session_id}/deliverables/{deliverable_id}`
- `GET /sessions/{session_id}/deliverable-versions/{version_id}`
- `GET /sessions/{session_id}/deliverable-versions/{version_id}/tool-executions`

The first release should keep deliverables session-scoped and avoid introducing broader workspace libraries.

## 10.5 Legacy Sessions and Migration

Existing sessions without deliverable records should remain valid.

Phase 1 migration strategy:

- add the new tables through Alembic
- do not backfill all historical sessions
- only create deliverable records for new completed runs after rollout
- if a legacy session has no deliverable records, the frontend falls back to the
  current artifacts/file behavior

Optional future enhancement:

- add an administrative or on-demand backfill job for selected sessions

## 11. Frontend Design

## 11.1 Components To Reuse

Reuse:

- execution layout
- file preview and file tree
- terminal viewer
- generic tool viewer
- browser/process replay primitives where appropriate

## 11.2 New Frontend Concepts

Add:

- deliverable card group in assistant messages
- deliverables data hook and API layer
- deliverable-aware right-panel selection state
- process filter for selected deliverable version

## 11.3 Panel Behavior

### Deliverables Panel

Transform the current file-centric panel into a deliverable-centric panel by:

- defaulting to latest deliverables
- separating reference materials from formal outputs
- preserving access to the full file tree as a secondary view

### Process Panel

Transform the current computer panel into a deliverable-specific process explorer by:

- defaulting to tool executions associated with the selected deliverable version
- keeping an optional full-session mode
- presenting terminal commands, Python-related commands, read/write/edit steps, and browser evidence when relevant

## 11.4 Message Rendering

The chat layer should attach deliverable UI metadata to assistant turns after new versions are detected. This can be handled as UI enrichment on top of current message parsing rather than changing the raw message protocol immediately.

## 12. Error Handling and Fallbacks

If detection is ambiguous:

- select the most likely Office output as latest
- show a small note in the assistant response if multiple candidates exist
- avoid blocking the run with a hard confirmation step in the first release

If no deliverable is detected:

- keep the current artifacts fallback
- do not create deliverable records for that run

If process linkage is incomplete:

- fall back to full-session process view
- do not hide available tool execution data

If a newer run overwrites the same file path instead of creating a distinct file
name:

- create a new `deliverable_version` record anyway
- preserve the old version record with its prior stored path metadata
- treat the newer completed run as the latest version for that logical
  deliverable

If a user deletes a previously generated file from the workspace:

- keep historical `deliverable_version` records intact
- mark the missing file as unavailable for preview/download
- do not remove it from version history automatically

## 13. Testing Strategy

## 13.1 Backend Tests

- deliverable detection from manifest and file changes
- version grouping by normalized logical name
- linkage between deliverable versions and tool execution ids
- session-scoped deliverables API

## 13.2 Frontend Tests

- assistant message rendering with deliverable cards
- right panel state transitions between deliverables and process views
- latest-version selection behavior
- deliverable-specific process filtering

## 13.3 End-To-End Scenarios

- create `Word + Excel` deliverables from chat and attachments
- upload new reference material and generate `v2`
- preview and download latest version
- open process view for a selected version and inspect terminal and tool details
- create a PPT draft in a later turn and confirm it becomes a new deliverable

## 14. Rollout Plan

## Phase 1

- add backend deliverable models
- add rule-based detection
- expose session-scoped deliverables APIs
- show deliverable cards in chat
- filter process view by selected deliverable version

## Phase 2

- improve naming normalization and ambiguity handling
- add richer reference summaries
- improve all-files and reference-input navigation

## Phase 3

- add optional explicit user actions such as "mark as deliverable"
- improve ranking of relevant process steps
- add smarter continuation prompts based on current deliverables

## 15. Final Recommendation

Use a lightweight backend deliverable model instead of pure frontend inference.

This approach keeps the current Poco execution architecture intact while adding the missing office-assistant product semantics:

- what is a deliverable
- what is the latest version
- which process created it
- which references influenced it

That is the smallest credible path from the current open-source Poco product to an internal, chat-first office assistant experience.
