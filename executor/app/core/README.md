# Executor Core

> Claude Agent 执行引擎核心模块，负责 AI 代理的生命周期管理。

## 模块结构

```
executor/app/core/
├── engine.py           # AgentExecutor - 主执行引擎
├── workspace.py        # WorkspaceManager - 工作区与 Git 仓库管理
├── permission_engine.py # PermissionEngine - 权限规则评估引擎
├── memory.py           # MemoryClient - 长期记忆存储客户端
├── callback.py         # CallbackClient - 执行回调报告客户端
├── user_input.py       # UserInputClient - 用户交互请求客户端
├── computer.py         # ComputerClient - 浏览器截图上传客户端
├── middleware/         # 请求中间件（上下文、日志）
└── observability/      # 可观测性（日志、追踪）
```

## 核心组件

### AgentExecutor (`engine.py`)

主执行引擎，封装 Claude Agent SDK：

- **生命周期管理**：初始化、执行、清理
- **Hook 集成**：通过 `HookManager` 注入扩展点
- **工具权限**：集成 `PermissionEngine` 进行工具调用决策
- **Memory MCP**：可选的长期记忆存储
- **浏览器自动化**：CDP 端点健康检查与 viewport 配置

### WorkspaceManager (`workspace.py`)

工作区准备与清理：

- **Git 仓库准备**：clone、checkout、fetch
- **会话持久化**：`.claude_data/` 目录隔离
- **Git excludes**：自动排除 VCS/构建产物

### PermissionEngine (`permission_engine.py`)

优先级规则评估引擎：

- **规则匹配**：工具名、类别、输入条件
- **Preset 编译**：plan 模式预编译限制规则
- **决策输出**：allow/deny + rule_id + reason

## 数据流

```
TaskConfig → WorkspaceManager.prepare()
          → AgentExecutor.execute()
          → PermissionEngine.evaluate(tool_call)
          → HookManager.trigger(phase)
          → CallbackClient.send(report)
```

## 测试

测试位于 `executor/tests/`：

```bash
pytest executor/tests/ -v
```

## 相关文档

- [DESIGN.md](./DESIGN.md) - 设计决策与架构
- [../hooks/README.md](../hooks/README.md) - Hook 系统
- [../schemas/README.md](../schemas/README.md) - 请求/响应 Schema