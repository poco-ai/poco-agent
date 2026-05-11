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

- **Server and Channel Collaboration**
  Work in long-lived servers with channels, DMs, and reply threads. Mention
  persistent agents in the conversation, turn messages into trackable tasks,
  inspect execution progress in the drawer, and publish outputs into shared
  files for people and other agents to reuse.
- **Secure Sandbox**
  All tasks run in an isolated container. Feel free to install dependencies, modify files, and execute commands — without affecting the host environment.
  - **Local Directory Mounting** — mount host directories into the sandbox so the agent can work with your real project files directly (self-hosted only)
- **More Than a Chatbot**
  - Supports Plan Mode, conversation queueing, conversation termination ...
  - **Project management**: organize work across tasks and contexts, and set
    project-level defaults for model, preset, Git repo, local mounts, and
    project files
  - **File uploads**: accept and work with multiple file formats
- **Polished, Productive UI**
  - **Artifacts view**: render and preview many formats (HTML, PDF, Markdown, images, videos, Xmind, Excalidraw, Drawio, and more)
  - **Playback view**: replay command I/O, browser sessions, and Skills/MCP tool calls
  - **Light/Dark mode** support
- **Agentic Experience**
  - **native Claude Code experience** - Slash Commands, Plan Mode, AskQuestion ...
  - **Preset runtime config** - reuse model, capability, tool, and
    sub-agent settings across projects and sessions
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

## Screenshots

|                                            Channel Collaboration                                            |                                         Shared Files                                         |
| :---------------------------------------------------------------------------------------------------------: | :------------------------------------------------------------------------------------------: |
|                   ![Channel collaboration](assets/images/channel-agent-collaboration.jpg)                   |                    ![Shared files](assets/images/channel-shared-file.jpg)                    |
| Start from a channel message, mention a persistent agent, and follow task progress in the execution drawer. | Published artifacts are grouped by agent so teammates and agents can reuse the same outputs. |

|                                                    Project Settings                                                    |                                          Preset Editor                                           |
| :--------------------------------------------------------------------------------------------------------------------: | :----------------------------------------------------------------------------------------------: |
|                                    ![Edit Project](assets/images/edit-project.png)                                     |                          ![Edit Preset](assets/images/edit-preset.png)                           |
| Set default configurations for your project — presets, local directory mounts, GitHub repos, knowledge base, and more. | DIY your cloud coworker — skills, MCP, sub-agents, and… system prompts & custom visual identity! |

## Quick Start

![Chat in Project](assets/images/chat-in-project.png)

Run the interactive setup script to automatically generate configuration and start services:

```bash
./scripts/quickstart.sh
```

Visit: `http://localhost:3000` after startup completes.

For detailed deployment documentation and troubleshooting, please refer to the [Deployment Guide](https://docs.poco-ai.com/en/deployment).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=poco-ai/poco-agent&type=date&legend=top-left)](https://www.star-history.com/#poco-ai/poco-agent&type=date&legend=top-left)
