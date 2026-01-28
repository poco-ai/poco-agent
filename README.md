<div align="center">
  <img src="assets/logo.JPG" alt="Poco Logo" width="150" height="150" style="border-radius: 25px;">

# Poco

**Manus-like autonomy, powered by cloud-based Claude Code**

An intelligent agent harnessing cloud-based Claude Code to realize a Manus-like autonomous experience.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)

[English](./README.md) | [中文](./README_zh.md)

</div>

---

## Positioning

Poco turns Claude Code into a cloud-native, autonomous coworker. Built on cloud-based Claude Code, it delivers a Manus-like autonomous experience while keeping humans in the loop, and it plugs into the MCP/Skills ecosystem for rich extensibility.

## Why Poco

- **Full Claude Code experience**: everything Claude Code can do, not just coding
- **General-purpose agents via Skills/MCP**: connect tools and data to handle docs, organization, and analysis
- **Cloud execution with human control**: queue tasks in parallel, confirm before key actions

## What you can do

- Give a goal, get an executable plan with live progress
- Let agents read, write, and organize real files safely
- Run multiple tasks in parallel across desktop and mobile

## Ecosystem

Poco embraces the **MCP/Skills** ecosystem so you can connect tools, data sources, and workflows as building blocks. Bring your own MCP servers or Skills to extend what agents can do without reinventing the platform.

## Product Gallery

Demo1: use three prompts to build a classic google game with doubao's head 😂

![Demo1](https://github.com/user-attachments/assets/0ef59c4c-8363-44a6-b9ed-7005ccfd71cb)

Demo2: AskUserTool and file operations

![Demo2](https://github.com/user-attachments/assets/98920a1f-fd41-46d4-803d-9c35aaa33b4c)

Demo3: poco can handle different types of files.

![Demo3](https://github.com/user-attachments/assets/8135dab4-6396-4af8-97af-6f665853fb56)

Demo4: works fine on mobile devices.

![Demo4](https://github.com/user-attachments/assets/ccf680bb-358c-4fc9-ad97-50f75b5ea3ac)

## Community

Join our WeChat group for updates and discussion:

<img src="assets/wx_group.jpg" alt="WeChat Group QR" width="180">

---

## Quickstart (Docker Compose)

Recommended for first-time setup (prepares `.env`, directories, permissions, pulls executor image, and creates the bucket):

```bash
./scripts/quickstart.sh
```

After running, edit `.env` and set required values (e.g. `ANTHROPIC_AUTH_TOKEN`), then start services if you used `--no-start`.

Manual start:

```bash
docker compose up -d
```

> **Note**: The Executor Manager dynamically creates executor containers. The bootstrap script pulls the executor image by default. If you skip the script, you can pull it manually:
>
> ```bash
> docker pull ghcr.io/poco-ai/poco-executor:latest
> ```

Default URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000` (`/docs`)
- Executor Manager: `http://localhost:8001` (`/docs`)

Docs:

- Docker Compose: `docs/en/docker-compose.md`
- Environment variables: `docs/en/configuration.md`
