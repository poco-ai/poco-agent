<div align="center">

![Poco Hero](assets/hero.png)

# Poco: Your Pocket Coworker

更安全、更漂亮、更易用的 OpenClaw 替代方案

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue)](https://www.docker.com/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Docs](https://img.shields.io/badge/poco-docs-blueviolet)](https://docs.poco-ai.com/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/poco-ai/poco-agent)

[English](README.md) | [简体中文](README_zh.md)

</div>

## 核心功能

- **Server / Channel 频道协作**
  在长期存在的 server 中使用 channel、DM 和 reply thread 协作。你可以在对话中
  `@agent` 触发持久化 Agent，把消息转成可追踪 task，在 execution drawer 中查看
  执行进度，并把产物发布到 shared files，供团队成员和其他 Agent 复用。
- **安全沙箱（Secure Sandbox）**
  所有任务运行在隔离容器中，可自由安装依赖、修改文件与执行命令，**不影响宿主环境**。
  - **本地目录挂载** — 将宿主机目录挂载到沙箱中，让 agent 直接操作你的项目文件（仅自托管模式）
- **不仅是 ChatBot**
  - 支持**计划模式（Plan Mode）**、对话排队、对话终止等能力
  - **项目管理**：在不同任务和上下文之间组织工作，并为模型、
    Preset、Git 仓库、本地挂载和项目文件设置项目级默认值
  - **文件上传**：支持多种文件格式输入与处理
- **精美而高效的界面**
  - **产物界面**：支持多种格式渲染与预览（HTML、PDF、Markdown、图片、视频、Xmind、Excalidraw、Drawio 等）
  - **回放界面**：可回看命令输入输出、浏览器操作与 Skills/MCP 调用记录
  - 支持**明暗模式**
- **Agentic 体验**
  - 完整复刻 **Claude Code** 原生体验：Slash Commands、Plan Mode、AskQuestion
  - **Preset 运行配置**：在项目和会话之间复用模型、能力、
    工具和子 Agent 配置
  - 支持 **MCP 协议** 与自定义 Skills：易导入、可无限扩展
  - 内置**浏览器**：支持自主网络研究与信息整合
  - 支持 **GitHub 仓库连接**：代码检索、阅读与编辑
  - 支持**后台执行与定时任务**：即使关闭浏览器，Agent 也能在云端持续运行
- **交互重构（多端与消息驱动）**
  - **移动端支持**：随时随地操控你的 Agent
  - **IM 支持**：后端内嵌的钉钉 / 飞书 / Telegram 消息传递，支持推送与事件订阅
  - **个人部署**：一键 Docker 启动，获得完整运行环境
  - **云端订阅**：敬请期待
  - **多语言支持**
- **智能记忆（Smart Memory）**
  Powered by **mem0**：Agent 能记住你的偏好、项目上下文与历史交互，让协作越来越顺手。
- **更多能力等你发现！**

## 界面预览

|                                   频道协作                                   |                                  共享文件                                   |
| :--------------------------------------------------------------------------: | :-------------------------------------------------------------------------: |
|          ![频道协作](assets/images/channel-agent-collaboration.jpg)          |           ![Shared files](assets/images/channel-shared-file.jpg)            |
| 从频道消息出发，提及持久化 Agent，并在 execution drawer 中查看任务执行进度。 | 已发布 artifacts 会按 Agent 分组，方便团队成员和其他 Agent 复用同一批成果。 |

|                               项目设置                                |                               Preset 编辑                               |
| :-------------------------------------------------------------------: | :---------------------------------------------------------------------: |
|              ![项目设置](assets/images/edit-project.png)              |              ![Preset 编辑](assets/images/edit-preset.png)              |
| 为项目设置默认配置——preset、本地目录挂载路径、GitHub 仓库、知识库等。 | DIY 设计你的云端同事——skills、MCP、sub-agent 以及……提示词和同事的形象！ |

## 快速开始

![项目内对话](assets/images/chat-in-project.png)

运行交互式安装脚本，自动生成配置并启动服务：

```bash
./scripts/quickstart.sh
```

启动完成后访问：`http://localhost:3000`

详细的部署文档和问题排查，请参考 [部署指南](https://docs.poco-ai.com/zh/deployment)。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=poco-ai/poco-agent&type=date&legend=top-left)](https://www.star-history.com/#poco-ai/poco-agent&type=date&legend=top-left)
