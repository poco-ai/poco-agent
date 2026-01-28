<div align="center">
  <img src="assets/logo.JPG" alt="Poco Logo" width="150" height="150" style="border-radius: 25px;">

# Poco

**基于云端 Claude Code 的智能体，打造 Manus 式自主体验**

一个基于云端 Claude Code 的智能体平台，旨在实现类似 Manus 的自主执行体验。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)

[English](./README.md) | [中文](./README_zh.md)

</div>

---

## 定位

Poco 将 Claude Code 变成云端的“自主协作同事”。基于云端 Claude Code，它提供类似 Manus 的自主体验，同时保留人类控制权，并天然接入 MCP/Skills 生态，能力可按需扩展。

## 为什么是 Poco

- **完整 Claude Code 体验**：不仅是写代码，Claude Code 能做的都能用
- **通用智能体能力**：通过 Skills/MCP 接入工具与数据，拓展到文档、资料整理与分析
- **云端执行 + 人在环**：任务可排队并行，关键操作先确认

## 你可以用它做什么

- 一句话给目标，系统自动拆解并持续更新进度
- 让智能体在真实文件上读、写、整理（有权限控制）
- 桌面与手机都能跟进，多任务同时跑

## 生态

Poco 原生支持 **MCP/Skills** 生态，可直接接入工具与数据源。你可以复用现有 MCP 服务器与 Skills，也可自定义能力模块，快速扩展智能体能力边界。

## 产品展示

Demo1：用三句话做一个带豆包头像的经典 Google 小游戏 😂

![demo](https://github.com/user-attachments/assets/0ef59c4c-8363-44a6-b9ed-7005ccfd71cb)

Demo2：Poco 可以处理多种类型文件。

![demo2-2](https://github.com/user-attachments/assets/8135dab4-6396-4af8-97af-6f665853fb56)

Demo3：移动端也能流畅使用。

![mobile-1](https://github.com/user-attachments/assets/ccf680bb-358c-4fc9-ad97-50f75b5ea3ac)

## 社区

扫码加入微信群交流：

<img src="assets/wx_group.jpg" alt="微信群二维码" width="180">

---

## 快速开始（Docker Compose）

一条命令启动 **backend / executor-manager / frontend**，并带上 **postgres + rustfs(S3)**：

> **注意**：Executor Manager 会动态创建 executor 容器来执行任务。建议先拉取 executor 镜像以加快首次任务执行：
>
> ```bash
> docker pull ghcr.io/poco-ai/poco-executor:latest
> ```

```bash
docker compose up -d
```

默认访问地址：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`（`/docs`）
- Executor Manager：`http://localhost:8001`（`/docs`）

更多说明：

- Docker Compose：`docs/docker-compose.md`
- 环境变量配置：`docs/configuration.md`
- 镜像发布（GitHub Actions）：`docs/image-publishing.md`
