# 当前分支多租户 / 鉴权改造调研

这份调研基于当前 `dev` 分支代码、相关提交链，以及和“支持用户部署，
开启鉴权时显示对应登录；未开启时继续本地无鉴权模式”这个目标的对照。
结论先说：当前实现已经把系统从“默认单用户 `default`”切到了“真实用户 +
OAuth 会话”模式，但没有保留 `auth disabled` 的本地兼容路径，所以和预期
有明显差距。

## 结论先行

- 当前分支已经完成了“按 `user_id` 隔离数据 + OAuth 登录 + 持久化会话”的
  主体骨架。
- 这套改造不是纯前端登录页，而是把后端绝大多数用户 API 都改成了
  “必须先拿到当前用户”。
- 当前实现没有保留“未开启鉴权时继续走本地开发模式”的分支；匿名访问会
  被前端重定向到登录页，后端也会直接返回 `401`。
- 登录页现在始终展示 `Google` 和 `GitHub` 两个按钮，即使服务端并没有
  配置对应 provider，只会在点击后跳回错误提示。
- 最近的 `ca91d09` 还移除了用户级 BYOK（模型供应商 API Key / Base URL）
  配置。这个改动对“管理员统一托管”的部署是简化，但对真正多用户 / 多租户
  场景是收缩。

## 基线怎么理解

这次改动实际上跨了两段历史：

1. `018a54b`（2026-01-15）先把系统改成了“逻辑上按 `user_id` 隔离”，但
   仍然保留单用户兼容：没有传 `X-User-Id` 时，后端默认回落到 `default`。
2. `e3610d2` 到 `35a0f24`（2026-04-08）再把真正的 OAuth 登录、用户表、
   会话表、前端登录守卫补齐。

所以，如果你的“之前版本”指的是 auth 改造之前，那么最关键的差异是：

- 之前：单用户默认可用，本地开发不需要登录。
- 现在：用户态页面默认要求已登录，匿名用户会被挡在外面。

## 这次到底做了什么

### 1. 更早的铺垫：把业务数据先改成按 `user_id` 隔离

`018a54b feat: Implement user-based session and task authorization...`

这个提交把大量 API 和 service 都改成接收 `user_id`，但当时的
`backend/app/core/deps.py` 仍然是：

- 允许请求头传 `X-User-Id`
- 如果没有，就回退到 `DEFAULT_USER_ID = "default"`

也就是说，这一步更像“为未来多用户做铺垫”，而不是强制接入登录系统。

### 2. 2026-04-08 这一串提交引入了完整 auth 骨架

核心提交链如下：

| 提交 | 作用 | 备注 |
| --- | --- | --- |
| `e3610d2` | 新增 `users`、`auth_identities`、`user_sessions` | 建了真实用户和登录会话表 |
| `3217bff` | 新增 `AuthService`、`/auth/*`、`/internal/sessions` | OAuth 登录、回调、登出、当前用户接口 |
| `4e029fd` | 新增前端 `auth` feature、登录页、用户账户 provider | 浏览器侧开始有用户概念 |
| `d90f22d` | 把 shell、用户菜单、设置页接到 auth | 前台主界面开始依赖登录态 |
| `724f3d1` | 为登录文案补全 i18n | 配套文案 |
| `778c0f1` | docker / env / executor_manager 适配 auth | 内部服务开始显式传 user_id |
| `f3a8c59` | 增加服务端 auth 状态判断、登出路由、session recovery | SSR 路由守卫成型 |
| `e8d0193` | 页面统一改成基于服务端 auth 状态跳转 | 重定向逻辑收口 |
| `26782ba` | 登出支持 Bearer token | 兼容 API 触发登出 |
| `e21e747` | 只把已验证邮箱写入 `primary_email` | 修正用户主邮箱语义 |
| `35a0f24` | 为邮箱验证逻辑补测试 | 补最关键的 auth 单测 |

从提交说明和代码调用关系看，这一串改动的目标主要有三件事：

1. 把用户身份从“字符串 user_id”升级成真实用户和登录会话。
2. 让前端基于 Cookie / Bearer token 自动携带登录态。
3. 让 Executor Manager 这种内部服务继续通过
   `X-Internal-Token + X-User-Id` 执行用户级任务。

### 3. 当前代码里的真实行为

后端现在的 `get_current_user_id` 已经从“默认 `default`”切到了“严格鉴权”：

- 优先读 session cookie 或 `Authorization: Bearer ...`
- 没有用户会话时，只接受受信任的
  `X-Internal-Token + X-User-Id`
- 其余情况一律 `401`

也就是说，浏览器用户态 API 不再存在“匿名但默认归到 `default` 用户”的路径。

前端现在则在服务端页面直接做守卫：

- `frontend/app/[lng]/(shell)/layout.tsx` 中，匿名用户会被重定向到登录页。
- `frontend/app/[lng]/page.tsx` 中，未登录用户也会跳到登录页。
- `frontend/features/user/model/user-account-provider.tsx` 中，一旦
  `/auth/me` 返回 `401`，会走 session recovery。

这意味着：当前实现不是“可选登录”，而是“前台默认必须登录”。

## 和我们预期的差异

我们的预期是：

1. 用户部署时，如果开启鉴权，就显示已经配置好的登录方式。
2. 如果没开启鉴权，就继续沿用原来的本地开发模式，不强制用户系统。

当前实现和这个预期的差异如下。

### 差异 1：没有保留 auth disabled 的本地模式

这是当前最大的问题。

现在的行为是：

- 前端匿名访问直接跳登录页。
- 后端用户 API 没有默认 `default` 回退。
- `backend/app/api/v1` 下有大量接口都依赖 `Depends(get_current_user_id)`；
  当前代码里一共能搜到 `142` 处依赖。

所以，只要不配 OAuth，不是“继续本地模式”，而是“前台不可用”。

### 差异 2：登录页没有按 provider 配置动态显示

`AuthService.get_oauth_registry()` 只有在配置了：

- `GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET`
- `GITHUB_CLIENT_ID + GITHUB_CLIENT_SECRET`

时才注册对应 provider。

但前端登录页 `frontend/features/auth/components/login-page-client.tsx`
始终渲染：

- Continue with Google
- Continue with GitHub

如果某个 provider 没配，点击后才会被服务端重定向回来，并显示
`provider_not_configured`。这和“显示对应的登录方式”不一致，用户体验也偏差。

### 差异 3：auth 能力没有显式配置层

当前代码里并没有一个清晰的 auth 开关，例如：

- `AUTH_ENABLED`
- `AUTH_MODE=disabled|optional|required`
- `AUTH_PROVIDERS=google,github`

现在实际上是靠“有没有 cookie”和“provider 有没有配置”隐式决定行为。
现有的 `DEPLOYMENT_MODE` 只用于本地文件系统能力探测，并没有参与 auth
逻辑。

结果就是：

- 本地 / 云端模式和鉴权模式耦合不清。
- 前端无法在 SSR 阶段知道“现在到底是无鉴权模式，还是鉴权开启但未登录”。
- 登录页也无法准确知道应该显示哪些 provider。

### 差异 4：现在更像 user-scoped，不是真正 tenant-scoped

如果严格讲“多租户”，当前实现其实只做到按 `user_id` 隔离，还没有真正的
`tenant / organization / membership / role` 模型。

目前业务表大量仍然是：

- `AgentSession.user_id`
- `Project.user_id`
- `Preset.user_id`

这些字段大多是普通字符串列，并没有统一外键到 `users`，更没有
`tenant_id`。所以它更接近“用户级隔离”，不是完整的多租户域模型。

### 差异 5：用户级模型凭证被移除了

`ca91d09 refactor: remove per-user model provider BYOK settings`
把用户级模型供应商配置删掉了，`backend/app/services/model_config_service.py`
里甚至直接 `del user_id`，模型配置完全从系统级 env / settings 读取。

这个改动有两面性：

- 对单租户、管理员统一托管的部署：合理，简化了配置面。
- 对真正多用户 / 多租户部署：不理想，因为不同用户无法隔离自己的模型凭证。

## 这些修改为什么会做，是否合理

### 合理的部分

下面这些改动本身是合理的：

- 增加 `users` / `auth_identities` / `user_sessions` 三张表，方向正确。
- 用 Cookie + Bearer token 双通路支持会话，服务端渲染也能拿到登录态。
- 内部服务继续通过 `X-Internal-Token + X-User-Id` 跑任务，这让执行链路
  没有被前台登录态绑死。
- `e21e747` 把未验证邮箱从 `primary_email` 里清掉，也是对的。

如果产品目标已经明确变成“云端登录后使用”，那么这套实现整体是顺的。

### 不合理的部分

和我们现在的目标对照，下面这些地方不够合理：

1. 把“接入 OAuth”直接等同于“前台必须登录”，没有留后门。
2. provider 是否可用没有透给前端，导致登录页始终显示两个按钮。
3. `DEPLOYMENT_MODE` 没有接进 auth 判定，部署模式和鉴权模式没有统一抽象。
4. 多租户语义还停留在 `user_id`，但最近又把用户级 BYOK 删掉，产品定位
   有点摇摆。

换句话说，现在的实现更像：

- 已经为“有鉴权的用户部署”走了一大步；
- 但把“无鉴权的本地兼容模式”一起丢掉了。

## 我建议的完善方向

### P0：先恢复“鉴权可选”

这是最应该优先补的。

建议增加一层明确配置，例如：

- `AUTH_MODE=disabled|oauth_required`
- 或者 `AUTH_ENABLED=false/true` + `AUTH_PROVIDERS=google,github`

然后把行为拆开：

1. **后端 `get_current_user_id`**
   - `AUTH_MODE=disabled` 时：回退到本地默认用户，例如 `default`
   - `AUTH_MODE=oauth_required` 时：保留当前严格鉴权逻辑
2. **前端路由守卫**
   - auth disabled：不要跳登录页，直接进应用
   - auth enabled：匿名用户才跳登录页
3. **用户信息**
   - auth disabled：给前端一个“本地模式用户”的稳定展示数据
   - auth enabled：走 `/auth/me`

如果不先补这层，当前实现没法满足“用户部署但不开鉴权”的目标。

### P0：增加 auth 配置探测接口

建议新增一个轻量接口，例如 `/api/v1/auth/config`，返回：

- 当前 auth mode
- 启用的 providers
- 是否允许匿名模式

这样前端就能：

- 只显示已经配置的 provider 按钮
- 在 auth disabled 时直接跳过登录页
- 在 auth enabled 但 provider 为空时，给出明确的管理员配置提示

### P1：把“显示哪些登录方式”做正确

有了 auth config 之后，登录页应该改成：

- 只展示已启用 provider
- 一个都没启用时，不展示空按钮列表
- 在 `oauth_required` 但 provider 为空时，给出明确错误页或启动期告警

这会比现在“点一下再报 provider_not_configured”好得多。

### P1：明确产品到底是“用户隔离”还是“真正多租户”

从代码看，当前更接近 user-scoped，不是真 tenant-scoped。

建议尽快定下来：

- 如果目标只是“自托管 + 可选 OAuth + 每个登录用户隔离自己的数据”，
  现在的数据模型可以继续演进。
- 如果目标真的是“组织 / 团队 / SaaS 多租户”，那后面就需要补：
  - `tenant / organization`
  - `membership / role`
  - `tenant_id` 级别的数据边界
  - 管理员和普通成员权限模型

否则“多租户”这个词会和当前实现不匹配。

### P1：重新判断 BYOK 是否要回归

`ca91d09` 移除了用户级模型凭证配置，这件事需要尽快定策略。

我建议按部署目标来分：

- **单租户 / 自托管用户部署**：系统级 env 即可，当前方向没问题。
- **共享部署 / 多用户实例**：至少要恢复“按用户或按租户隔离模型凭证”
  的能力，不然所有用户只能共用管理员配置。

这不是纯体验问题，而是权限边界和成本边界问题。

### P2：补兼容迁移和验证

后面如果继续推进，建议一起补上：

1. `auth disabled` / `google only` / `github only` / `google+github`
   四组端到端验证
2. 迁移说明：旧版本从单用户默认模式升级后会发生什么
3. 启动期配置校验：例如启用了 OAuth 但一个 provider 都没配时直接告警

## 我对后续工作的建议顺序

按优先级，我建议这样推进：

1. 先补 auth mode 和 auth config 探测接口
2. 再改前端登录页与 shell 守卫，恢复无鉴权本地模式
3. 再决定 BYOK 是保持系统级，还是恢复用户 / 租户级能力
4. 最后再讨论是否真的要上 tenant / organization 域模型

## 最后一句判断

如果目标是“云端托管、所有用户都登录后使用”，当前改造方向基本成立。

如果目标是“支持用户部署，并且鉴权是可选项”，那当前实现还不能算完成；
它已经做完了“有鉴权”这半边，但“无鉴权继续本地模式”这半边还没补回来。
