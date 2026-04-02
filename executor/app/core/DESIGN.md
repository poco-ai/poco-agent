# Executor Core Design

> 设计决策与架构说明

## 架构原则

### 1. 单一职责

每个核心类只负责一个明确的功能：

| 类 | 职责 | 边界 |
|---|---|---|
| `AgentExecutor` | 代理生命周期 | 不处理 HTTP/API |
| `WorkspaceManager` | 文件系统与 Git | 不涉及执行逻辑 |
| `PermissionEngine` | 权限决策 | 不执行动作 |
| `*Client` | 外部通信 | 只做 HTTP 调用 |

### 2. 依赖注入

所有外部依赖通过构造函数注入：

```python
class AgentExecutor:
    def __init__(
        self,
        session_id: str,
        hooks: list,
        *,
        user_input_client: UserInputClient | None = None,
        memory_client: MemoryClient | None = None,
    ):
        ...
```

这允许测试时 mock 外部依赖。

### 3. Hook 扩展点

执行生命周期通过 Hook 注入扩展：

- `setup` - 执行前准备
- `pre_query` - 发送查询前
- `message` - 收到消息时
- `error` - 错误处理
- `teardown` - 清理

详见 [../hooks/README.md](../hooks/README.md)。

## 关键设计决策

### D1: PermissionEngine 作为独立模块

**背景**：Batch 2 引入优先级规则引擎，需要与主执行循环解耦。

**决策**：`PermissionEngine` 独立于 `AgentExecutor`，通过 `evaluate()` 方法返回 `PermissionDecision`。

**理由**：
- 测试隔离：权限规则测试不依赖 SDK
- 扩展性：未来可替换为远程策略服务
- 性能：规则编译可缓存

### D2: WorkspaceManager 使用 asyncio

**背景**：Git 操作可能是阻塞 I/O。

**决策**：`WorkspaceManager.prepare()` 和 `cleanup()` 声明为 `async`，内部使用 `asyncio.to_thread()` 包装阻塞调用。

**理由**：
- 与 `AgentExecutor.execute()` 保持一致
- 不阻塞事件循环
- 未来可替换为异步 Git 库

### D3: 回调客户端分离

**背景**：执行报告需要发送到 Manager，但不应耦合到执行逻辑。

**决策**：`CallbackClient` 只负责 HTTP POST，业务逻辑由 `CallbackHook` 处理。

**理由**：
- 单一职责
- 可替换传输层（如 WebSocket）
- 错误处理隔离

### D4: CDP 端点安全校验

**背景**：Batch 2 安全审计发现 `urllib.request.urlopen(url)` 的 SSRF 风险。

**决策**：添加 URL scheme 校验，只允许 `http/https`。

```python
parsed_endpoint = urlparse(cdp_endpoint)
if parsed_endpoint.scheme not in ("http", "https"):
    raise ValueError(f"Invalid CDP endpoint scheme: {parsed_endpoint.scheme}")
```

**理由**：
- 纵深防御：环境变量由可信 Manager 注入
- 防止配置错误
- 消除 SAST 扫描警告

## 未来规划

### Batch 3: Workspace 策略扩展

当前 `WorkspaceManager` 只支持 clone。计划支持：

- `worktree` - 共享 `.git` 的轻量工作区
- `sparse-clone` - 部分检出
- `sparse-worktree` - 组合策略

架构调整：

```
executor/app/core/workspace/
├── __init__.py
├── manager.py          # 当前 WorkspaceManager
├── strategies.py       # CheckoutStrategy 协议
├── cache.py            # Repo 缓存管理
└── fallback.py         # 策略降级逻辑
```

### PermissionEngine 远程策略

当前规则在本地评估。未来支持：

- 从 Backend 拉取租户策略
- 审计日志写入数据库
- A/B 测试不同规则集

## 参考

- [Claude Agent SDK](https://docs.anthropic.com/claude-agent-sdk)
- [Batch 2 Plan](../../../../.claude/plan/batch2-permission-mcp.md)