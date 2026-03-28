<div align="center">

![Poco Hero](assets/hero.png)

# Poco: Your Pocket Coworker

A safer, more beautiful, and easier-to-use OpenClaw alternative

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue)](https://www.docker.com/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Docs](https://img.shields.io/badge/poco-docs-blueviolet)](https://docs.poco-ai.com/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/poco-ai/poco-agent)

[English](README.md) | [简体中文](README_zh.md)

</div>

## Core Features

- **Secure Sandbox**
  All tasks run in an isolated container. Feel free to install dependencies, modify files, and execute commands — without affecting the host environment.
- **More Than a Chatbot**
  - Supports Plan Mode, conversation queueing, conversation termination ...
  - **Project management**: organize and switch between tasks and contexts more effectively
  - **File uploads**: accept and work with multiple file formats
- **Polished, Productive UI**
  - **Artifacts view**: render and preview many formats (HTML, PDF, Markdown, images, videos, Xmind, Excalidraw, Drawio, and more)
  - **Playback view**: replay command I/O, browser sessions, and Skills/MCP tool calls
  - **Light/Dark mode** support
- **Agentic Experience**
  - **native Claude Code experience** - Slash Commands, Plan Mode, AskQuestion ...
  - **MCP & Skills** - easy to import and infinitely extensible
  - **Browser** - Built-in browser for autonomous web research
  - **GitHub repo integration** for code search and editing
  - **Background execution & scheduled triggers** — your agent can keep running in the cloud even after you close the browser
- **Interaction**
  - **Mobile support**: control your agent anytime, anywhere
  - **IM integration**: embedded backend messaging via DingTalk, Feishu, and Telegram, with push notifications and event subscriptions
  - **Self-hosting**: one-click Docker deployment with a full runtime environment
  - **Cloud subscription**: coming soon
  - **Multilingual** support
- **Smart Memory**
  Powered by **mem0**: the agent remembers your preferences, project context, and past interactions to deliver increasingly personalized help.
- Many more powerful features waiting for you to discover!

## Quick Start

Run the interactive setup script to automatically generate configuration and start services:

```bash
./scripts/quickstart.sh
```

Visit: `http://localhost:3000` after startup completes.

For detailed deployment documentation and troubleshooting, please refer to the [Deployment Guide](https://docs.poco-ai.com/en/deployment).

## Repository Docs

- [Contribution Guide](CONTRIBUTING.md)
- [Repository Governance Draft](docs/repository-governance.md)
- [AI Agent Guide](AGENTS.md)

## Dispatch Model

Poco now uses a queue-driven execution model:

- Backend is the source of truth for dispatchable work and run/session state
- `executor_manager` claims queued runs through `RunPullService`
- `executor_manager` stages runtime assets, allocates or reuses containers, and calls executor
- APScheduler in `executor_manager` is used for polling and maintenance jobs, not as the primary execution state for user-created tasks

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=poco-ai/poco-agent&type=date&legend=top-left)](https://www.star-history.com/#poco-ai/poco-agent&type=date&legend=top-left)
