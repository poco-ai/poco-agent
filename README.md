<div align="center">
  <img src="assets/logo.JPG" alt="Poco Logo" width="150" height="150" style="border-radius: 25px;">

# Poco: Your Pocket Coworker

基于云端 Claude Code，打造 Manus 般的 Agent 体验

你也可以把它看作是 **OpenClaw** 的**更安全**（沙盒隔离）、**更漂亮**（现代 UI）、**配置更简单**（开箱即用）的替代方案。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue)](https://www.docker.com/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/poco-ai/poco-agent)

[English](./README_EN.md) | [中文](./README.md)

</div>

---

## 核心功能

- **安全沙盒**：任务在隔离容器中运行，随意安装依赖或修改文件，绝不破坏宿主机环境。
- **高颜值 UI & 移动端适配**：提供美观的 Web 界面和产物预览，手机上也能随时指挥 Agent。
- **零配置开箱即用**：无需繁琐的本地环境配置，通过 Docker 一键启动，包含完整运行环境。
- **全面能力 & MCP/skills 扩展**：完整复刻 Claude Code 原生功能（Slash Command、Plan Mode、AskQuestion），并支持 MCP 协议或自定义 Skills，能力无上限。
- **异步与定时任务**：支持后台挂机运行和定时触发，关掉网页 Agent 依然在云端自动干活。
- **更多功能**：内置**浏览器**可自主上网查资料，支持**GitHub 仓库连接**……更多强大功能等你发掘！

![home](assets/home.png)

<details>
<summary><strong>点击查看更多功能演示</strong></summary>
<br>

1. 产物渲染，支持浏览器与终端回看
   ![output](assets/output.png)
   ![output-computer](assets/output-computer.png)
   <video src="https://github.com/user-attachments/assets/3d732f0b-3f32-4aca-ab61-ec28c5fd274e" controls="controls"></video>
   ![HTML](https://github.com/user-attachments/assets/0ef59c4c-8363-44a6-b9ed-7005ccfd71cb)
   ![Multiple-file](https://github.com/user-attachments/assets/8135dab4-6396-4af8-97af-6f665853fb56)
2. Plugin/MCP/Skills/Subagent/Slash Commands 全面支持，配置容易
   ![mcp](assets/mcp.png)
   ![skills](assets/skills.png)
   <video src="https://github.com/user-attachments/assets/60df5a0f-c338-44ad-af03-e1ebb98d5743" controls="controls"></video>
3. 定时任务
   ![schedule](assets/schedule.png)
4. 移动端优化，口袋里的 AI Coworker
   <video src="https://github.com/user-attachments/assets/a8364763-8edf-4bb1-b873-5c27755a5712" controls="controls"></video>

</details>

## 快速开始

运行一键启动脚本，按提示输入 API Key，自动生成配置文件并启动服务：

```bash
./scripts/quickstart.sh
```

启动完成后访问：`http://localhost:3000`

(可选) 如需使用外部 S3/R2 存储，请使用 `docker-compose.r2.yml` 启动。

详细的部署指南与可能遇到的问题，请参考[部署文档](./docs/zh/README.md)。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=poco-ai/poco-agent&type=date&legend=top-left)](https://www.star-history.com/#poco-ai/poco-agent&type=date&legend=top-left)

## 致谢

本项目灵感来源于[wegent](https://github.com/wecode-ai/Wegent)，并参考了其架构设计。感谢原作者的辛勤工作！


## 安装

### 使用pip安装
```bash
pip install package-name
```

### 使用conda安装
```bash
conda install -c conda-forge package-name
```

### 从源码安装
```bash
git clone https://github.com/username/repo-name.git
cd repo-name
pip install -e .
```

## 使用示例

### 基本用法
```python
import package_name

# 初始化
client = package_name.Client()

# 调用功能
result = client.process()
print(f"结果: {result}")
```

### 高级用法
```python
# 配置参数
config = {
    'setting': 'value',
    'timeout': 30
}

client = package_name.Client(**config)
```

## 贡献指南

欢迎贡献！请查看[CONTRIBUTING.md](CONTRIBUTING.md)了解详细指南。

### 开发流程
1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### 代码规范
- 遵循PEP 8 (Python)或相应语言规范
- 添加适当的注释
- 编写测试用例
- 更新相关文档