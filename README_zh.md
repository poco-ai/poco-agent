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

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md)

</div>

## 核心功能

- **安全沙箱（Secure Sandbox）**
  所有任务运行在隔离容器中，可自由安装依赖、修改文件与执行命令，**不影响宿主环境**。
- **不仅是 ChatBot**
  - 支持**计划模式（Plan Mode）**、对话排队、对话终止等能力
  - **项目管理**：更好地组织与切换不同任务/上下文
  - **文件上传**：支持多种文件格式输入与处理
- **精美而高效的界面**
  - **产物界面**：支持多种格式渲染与预览（HTML、PDF、Markdown、图片、视频、Xmind、Excalidraw、Drawio 等）
  - **回放界面**：可回看命令输入输出、浏览器操作与 Skills/MCP 调用记录
  - 支持**明暗模式**
- **Agentic 体验**
  - 完整复刻 **Claude Code** 原生体验：Slash Commands、Plan Mode、AskQuestion
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

## 快速开始

运行交互式安装脚本，自动生成配置并启动服务：

```bash
./scripts/quickstart.sh
```

启动完成后访问：`http://localhost:3000`

详细的部署文档和问题排查，请参考 [部署指南](https://docs.poco-ai.com/zh/deployment)。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=poco-ai/poco-agent&type=date&legend=top-left)](https://www.star-history.com/#poco-ai/poco-agent&type=date&legend=top-left)
