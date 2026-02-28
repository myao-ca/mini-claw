# mini-claw 学习笔记

通过动手实现一个简化版 OpenClaw，理解 Always-On Agent 框架的核心架构。

> **和 coding-agent 的关系**：
> coding-agent 聚焦 Agent 内核（工具设计、记忆、规划、循环）。
> mini-claw 聚焦 Agent 框架（触发层、消息路由、频道适配、安全边界）。
> 两者合在一起，才是一个完整的生产级 Agent 系统。

---

## 学习路线图

> 安全永远是第一位。每一步新增能力都在安全边界内。

### 已完成（Steps 1-5）：基础骨架

```
收消息 → 问 LLM → 回消息
```

### 第一组：记忆与状态

| Step | 内容 | 对应 OpenClaw | 安全说明 |
|------|------|--------------|---------|
| Step 6 | **持久化会话历史** | `.jsonl` 会话存储 | 只写对话历史，不碰用户文件 |
| Step 7 | **动态 System Prompt** | 动态系统提示词构建 | 无新风险 |
| Step 8 | **上下文压缩（Compaction）** | `compaction.ts` | 无新风险 |

### 第二组：架构升级

| Step | 内容 | 对应 OpenClaw | 安全说明 |
|------|------|--------------|---------|
| Step 9 | **串行任务队列** | Task Channel Queue | 消除竞态，反而更安全 |
| Step 10 | **Hook 系统** | `src/plugins/hooks.ts` | 钩子是观察者，不给新权限 |
| Step 11 | **第二个频道（HTTP API）** | 多 Channel 并行 | 限本机访问，不暴露公网 |

### 第三组：智能升级

| Step | 内容 | 对应 OpenClaw | 安全说明 |
|------|------|--------------|---------|
| Step 12 | **记忆检索** | MEMORY.md + FTS5 混合检索 | memory 文件在 workspace 内 |
| Step 13 | **Sub-agent** | sub-agent + session_send | 子 Agent 工具集更受限 |

### 第四组：生产化

| Step | 内容 | 对应 OpenClaw | 安全说明 |
|------|------|--------------|---------|
| Step 14 | **定时任务** | `server-cron.ts` | 仍受 workspace 边界限制 |
| Step 15 | **模型故障转移** | model failover | 无新风险，提升可靠性 |

### 全局进度

```
✅ Step 1-5    骨架：Telegram 触发 → Gateway → Agent → 回复
✅ Step 6      持久化会话历史
✅ Step 7      动态 System Prompt
✅ Step 8      上下文压缩（Compaction）
✅ Step 9      串行任务队列
✅ Step 10     Hook 系统
⬜ Step 11     第二个频道（HTTP API）
⬜ Step 12-13  智能升级
⬜ Step 14-15  生产化
```

---

## 核心竞争力一览

| 编号 | 核心竞争力 | 说明 | 深入方向 |
|------|-----------|------|----------|
| ① | **Trigger Layer** | 触发层 | Polling vs Webhook、多平台接入、事件驱动 |
| ② | **Channel Adapter Pattern** | 频道适配器 | 平台差异屏蔽、消息标准化、多平台扩展 |
| ③ | **Gateway / Message Routing** | 网关与消息路由 | 会话键、绑定优先级、多 Agent 路由 |
| ④ | **Session Management** | 会话管理 | 会话隔离、持久化、跨平台会话链接 |
| ⑤ | **Security & Permissions** | 安全与权限 | 最小权限、路径边界、授权用户、白名单 |
| ⑥ | **Config Management** | 配置管理 | 密钥安全、.env 模式、多环境配置 |
| ⑦ | **Always-On Service** | 常驻服务设计 | Polling vs Webhook、守护进程、重启恢复 |
| ⑧ | **Callback / Decoupling** | 回调与解耦 | 控制反转、依赖注入、可插拔 Channel |

---

## 学习进度追踪

| 编号 | 核心竞争力 | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Step 6 | Step 7 | Step 8 | Step 9 | Step 10 |
|------|-----------|--------|--------|--------|--------|--------|--------|--------|--------|--------|---------|
| ① | Trigger Layer | | | | 重点 | 验证 | | | | | |
| ② | Channel Adapter Pattern | | | | 重点 | 验证 | | | | | |
| ③ | Gateway / Message Routing | | | | 重点 | 验证 | | | | | |
| ④ | Session Management | | | | 简陋 | | 持久化 | | | 串行 | |
| ⑤ | Security & Permissions | | 重点 | | | | | | | | |
| ⑥ | Config Management | 重点 | 扩展 | | | | | | | | |
| ⑦ | Always-On Service | | | | 重点 | 验证 | | | | | |
| ⑧ | Callback / Decoupling | | | | 重点 | | | | | | |
| ⑨ | Dynamic System Prompt | | | | | | | 重点 | | | |
| ⑩ | Context Compaction | | | | | | | | 重点 | | |
| ⑪ | Task Queue | | | | | | | | | 重点 | |
| ⑫ | Hook System | | | | | | | | | | 重点 |

---

## 各 Step 学习内容

### Step 1：基础设施搭建

**目标**：建立干净、安全的项目基础，养成工程好习惯。

**做了什么**：
- 建立新 repo `mini-claw`，从 coding-agent 提取基础代码
- 用 `.env` 替代 `config.py` 存储密钥（`python-dotenv`）
- `.gitignore` 屏蔽 `.env` 和 `config.py`，提交 `.env.example` 作为模板
- 建立 Python 虚拟环境（`venv`），隔离依赖

**关键概念**：
- `.env` 模式：密钥只存在本地文件，不进 git；`.env.example` 记录需要哪些变量，无实际值
- 虚拟环境：每个项目独立的依赖空间，不污染全局 Python
- 提交 `config.example.py` 或 `.env.example` 而不是含真实值的文件，这是行业标准做法

**对应 OpenClaw**：`.env.example`，配置管理系统（`src/config/`）

---

### Step 2：安全设计

**目标**：在给 Agent 任何能力之前，先划定安全边界。

**做了什么**：
- 只保留只读工具（`read_file`、`list_files`），危险工具（`execute_code`、`write_file`）不开放
- 新增 `WORKSPACE_PATH`：Agent 只能访问该目录内的文件，出界直接报错
- 用 `os.path.realpath()` 防止路径穿越攻击（`../../etc/passwd`）
- `TELEGRAM_ALLOWED_CHAT_ID`：只有授权用户的消息才会被处理
- System prompt 明确告知 LLM 只读限制和 workspace 范围

**关键概念**：
- **最小权限原则**：给 Agent 的权限应该是完成任务的最小集合，不是越多越好
- **路径穿越攻击**：`../../../` 可以跨越目录限制，`realpath()` 解析后再检查前缀才可靠
- **两层防护**：工具层（`_is_safe_path()` 硬拒绝）+ Prompt 层（告知 LLM 限制）双重保障，工具层是真正的防线

**对应 OpenClaw**：agent workspace 边界、账号绑定（binding）机制、命令白名单

---

### Step 3：理解 Telegram Bot

**目标**：搞清楚 Telegram Bot 的工作原理，再开始写代码。

**关键概念**：
- Bot Token = Bot 账号的账号密码，BotFather 颁发
- **Bot 本身只是空壳**：Token 只是身份凭证，没有程序在跑，Bot 就是死的
- 程序用 Token 连上 Telegram，注册 message handler，Bot 才有"灵魂"
- `infinity_polling()`：死循环，不断问 Telegram "有新消息吗？"，是 Bot 保持活着的根本
- Chat ID：每个用户/群组的唯一 ID，`@userinfobot` 可以查自己的

**类比**：
```
Bot Token  =  账号 + 密码
你的程序   =  灵魂（决定收到消息怎么反应）
```

**Polling vs Webhook（延伸）**：
- Polling（轮询）：程序主动问 Telegram 有没有新消息，简单，不需要公网 IP
- Webhook：Telegram 主动推消息过来，高效，但需要公网 HTTPS 地址
- mini-claw 用 Polling，OpenClaw 用 Webhook（长连接），效果一样，Webhook 更适合生产

---

### Step 4：Channel Adapter + Gateway

**目标**：实现"触发层"，让 Agent 从"手动运行"变成"收到消息自动触发"。

**做了什么**：
- 新建 `telegram_channel.py`：Telegram 频道适配器
  - `is_authorized()`：Chat ID 白名单检查
  - `send_reply()`：发送回复，自动分段（Telegram 单条上限 4096 字符）
  - `start_polling(on_message)`：接受回调函数，启动监听
- 新建 `gateway.py`：主循环，消息路由
  - `sessions` 字典：每个 chat_id 对应独立的 Agent 实例（会话隔离）
  - `get_or_create_session()`：按需创建会话
  - `handle_message()`：路由逻辑，处理特殊命令（`/start`、`/reset`），其余交给 Agent
  - `gateway.py` 是入口，`if __name__ == "__main__"` 在这里

**关键概念**：
- **Channel Adapter Pattern**：屏蔽各平台差异，让 Gateway 不需要关心消息从哪里来。以后加 Discord 只需新建 `discord_channel.py`，Gateway 不用改
- **回调函数（Callback）**：`start_polling(handle_message)` 把 `handle_message` 作为参数传入。Channel 负责监听，但不知道如何处理业务——业务处理交给 Gateway 提供的回调。这是"控制反转"
- **Gateway 是主人，Channel 是下属**：Gateway 启动时调用 `start_polling()`，不是 Channel 启动了 Gateway
- **会话隔离**：每个 chat_id 对应独立 Agent 实例，各自有独立的 `conversation_history`，互不干扰

**数据流**：
```
python gateway.py（入口）
    ↓ 调用
start_polling(handle_message)
    ↓ 监听到消息
handle(message)  ← 触发
    ↓ 回调
handle_message(chat_id, text)  ← gateway 的逻辑
    ↓
agent.run(text)
    ↓
LLM 回复
    ↓
send_reply()  → Telegram
```

**对应 OpenClaw**：
- `telegram_channel.py` → `extensions/telegram/`
- `gateway.py` → `src/gateway/server.ts` + `boot.ts`
- `sessions` 字典 → OpenClaw 的 session 机制（session key: `agent:main:direct:telegram:123456`）

---

### Step 5：端到端验证

**目标**：分层验证，逐步确认整条链路通畅。

**验证策略**：先用固定回复测连接，再接入真正的 Agent。

```
第一步：response = "hi!"         → 验证 Telegram 连接正常
第二步：response = handle_message → 验证 Gateway 路由正常
第三步：agent.run() 真正调用 LLM → 验证完整链路
```

**做了什么**：
- 临时把 `telegram_channel.py` 里的 `response = on_message(...)` 改为 `response = "hi!"`
- 在 Telegram 搜索 Bot 用户名（`@mini_claw_test_bot`），发消息，确认收到 "hi!"
- 改回 `response = on_message(...)`，发真实消息，验证 Agent 正常工作
- 发 `/start` 验证 Gateway 的特殊命令路由

**关键概念**：
- **分层验证**：出问题时能快速定位是 Telegram 层、Gateway 层还是 Agent 层的问题
- **最小改动测试**：只改一行（`on_message` → `"hi!"`），其余不动，隔离变量

---

### Step 6：持久化会话历史

**目标**：进程重启后对话上下文不丢失，Bot 不会"失忆"。

**核心改动**：

| 文件 | 改动 |
|------|------|
| `agent.py` | `__init__` 接收 `session_id`，启动时 `_load_history()`，每次 append 后 `_save_message()` |
| `gateway.py` | `Agent()` → `Agent(str(chat_id))`，每个用户独立文件 |

**存储格式**：`sessions/{chat_id}.jsonl`，每行一条消息，append-only。

**记录内容**：不只是用户问答，而是完整的 agentic 轨迹：
```
用户的问题 → 规划 → 触发执行 → LLM 工具调用 → 工具结果 → 最终回答
```
这是因为每次调用 API 都要把完整 messages 数组传进去，所以 `conversation_history` 本身就是这个数组——持久化只是把它写到文件里。

**两层记忆分工**：

| 层 | 作用 | 存活 |
|----|------|------|
| `sessions` dict（内存） | 同一次进程运行内快速复用 Agent 实例 | 进程重启消失 |
| `.jsonl` 文件（磁盘） | 进程重启后恢复全部上下文 | 永久，直到 `/reset` |

---

### Step 7：动态 System Prompt

**目标**：system prompt 不再写死，每次调用 LLM 前现拼，根据当前状态注入不同内容。

**核心改动**：

- `__init__` 里删掉写死的 `self.system_prompt`，改为 `self.mode = "code"`
- 新增 `_build_system_prompt()` 方法，每次调用前现拼
- `_call_llm()` 和 `_create_plan()` 改用 `_build_system_prompt()`
- gateway 加 `/chat` / `/code` 命令切换模式

**动态注入的内容**：

| 内容 | 说明 |
|------|------|
| 当前时间 | `datetime.now()` — bot 知道现在几点几号星期几 |
| 对话模式 | `code`（编程助手）或 `chat`（轻松聊天） |
| MEMORY.md | 项目根目录若有此文件，内容自动追加进 system prompt |

**模式切换的附带效果**：

chat 模式不只是换了 system prompt——还跳过了 Plan-and-Execute 的规划阶段，直接对话。否则你说"你好"，bot 也要先列个执行计划。

```
code 模式：规划 → 执行 → 回复   （适合需要用工具的编程任务）
chat 模式：直接回复              （适合路上聊天、头脑风暴）
```

**对应 Claude Code**：我（Claude Code）启动时自动加载 `memory/MEMORY.md` 进 context，就是同样的机制。

---

### Step 8：上下文压缩（Compaction）

**目标**：防止 conversation history 无限增长，撞上 context window 上限或造成 token 浪费。

**问题根源**：每次调用 API 都要把完整的 `conversation_history` 传进去。聊得越久，token 越多，费用越高；聊够久甚至会超过上限导致 API 报错。

**解法**：设两个阈值，超过时触发压缩：

```
MAX_HISTORY = 30   # 超过这个消息数触发压缩
KEEP_RECENT = 10   # 压缩时保留最近几条不动
```

压缩过程：
1. 把旧的 `history[:-10]` 拿去让 LLM 概括成一段摘要
2. 用 `[摘要消息, 确认消息]` 替换掉那些旧消息
3. 拼上最近 10 条完整消息
4. 重写整个 session 文件（不再是 append）

```
压缩前：[旧消息 ×20] + [近期消息 ×10]  → 30 条
压缩后：[摘要 ×2]   + [近期消息 ×10]  → 12 条
```

**对应 Claude Code**：你在这次会话开头看到的那段长摘要，就是上一个 session 被压缩后的产物。Claude Code 帮你自动做了这件事，mini-claw 的 Step 8 就是同样的机制。

**压缩的是什么文件**：就是 `sessions/{chat_id}.jsonl`。压缩前 30 行，压缩后 12 行，`_compact_history()` 最后把新的 `conversation_history` 整个覆盖写入那个文件（不是 append）。随时可以打开文件直接看到压缩前后的变化。

**对应 OpenClaw**：`compaction.ts`

---

### Step 9：串行任务队列

**目标**：消除同一 session 并发处理消息引发的竞态条件。

**问题**：Telegram 的 `infinity_polling()` 是多线程的，多条消息同时进来会并发调用 `handle_message()`。同一个 Agent 实例的 `conversation_history` 被多个线程同时读写，导致 history 错乱、API 并发过高触发限流。

**解法**：每个 session 一个 `Queue` + 一个 worker 线程。消息进来先入队，worker 串行取出处理：

```
消息1 ──┐
消息2 ──┤→ Queue → worker 线程 → 串行处理 → 回复
消息3 ──┘
```

调用方 `handle_message()` 把任务放入队列后阻塞等待，直到 worker 处理完返回结果。不同用户之间仍然并行（各自有独立的 Queue + worker）。

**核心改动**（gateway.py）：

| 新增 | 说明 |
|------|------|
| `task_queues: dict[int, Queue]` | 每个 chat_id 一个队列 |
| `_worker(chat_id, q)` | 串行处理队列里的任务，永不退出的 daemon 线程 |
| `get_or_create_queue()` | 首次创建队列时同步启动 worker 线程 |

**对应 OpenClaw**：Task Channel Queue（串行 by default 的设计原则）

---

### Step 10：Hook 系统

**目标**：让系统在关键时间点自动触发回调，不需要修改核心代码就能扩展行为。

**核心改动**：

| 文件 | 改动 |
|------|------|
| `hooks.py`（新建） | `register()` 注册回调，`fire()` 触发事件 |
| `gateway.py` | 在关键位置调用 `hooks.fire()`，注入三个事件点 |

**三个事件点**：

```
message_received  — 消息刚进来时      data: {chat_id, text}
before_agent_run  — agent 开始处理前  data: {chat_id, text, mode}
after_reply       — 回复发出后        data: {chat_id, text, reply}
```

**关键洞察：钩子是"洞"，实现是"钩"**

`hooks.fire()` 在 gateway 里只是挂了个空钩子——没有任何注册的回调时，调用了等于什么都没发生，完全是空操作。只有当你 `register()` 注入了真实的实现（比如一个 `print` 语句，或者一个写日志的函数），那个空钩子才有了意义。

```python
# 这一行只是"打洞"——存在，但不做任何事
hooks.fire("after_reply", {...})

# 这一行才是"挂钩"——给洞赋予了真实的行为
hooks.register("after_reply", lambda d: print(f"HOOK: {d['chat_id']} 收到了回复"))
```

这也意味着核心代码（gateway.py、agent.py）不需要知道外部扩展是什么，扩展也不需要修改核心代码——两边只通过事件名和 data dict 约定，完全解耦。

**对应 Claude Code**：

Claude Code 里也有同样的机制，只是 Anthropic 替你把钉子埋好了：

```
PreToolUse   — 工具调用之前
PostToolUse  — 工具调用之后
Stop         — Claude 回复结束时
Notification — 需要通知用户时
```

你在 `settings.json` 里配置：

```json
"hooks": {
  "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo 要跑bash了"}]}]
}
```

就是你在那颗空着的钉子上挂上了自己的挂历——从此每次 Claude 要用 Bash 之前，都会先跑你的命令。

| | mini-claw | Claude Code |
|---|---|---|
| 谁埋钉子 | 你自己（`hooks.fire()`） | Anthropic 预埋好 |
| 谁挂东西 | 你自己（`hooks.register()`） | 你自己（`settings.json`） |
| 本质 | 相同 | 相同 |

**对应 OpenClaw**：`src/plugins/hooks.ts`

---

## Tips & 知识点

### TEMP 环境变量与 Windows 短路径问题

Windows 的 `%TEMP%` 变量有时存的是 8.3 短路径格式（如 `QIANGT~1`，来自用户名 `Qiang Tang` 含空格），导致 Node.js 的 `fs.open()` 在某些场景下报 `EINVAL`。

**诊断**：
```cmd
echo %TEMP%
```
如果输出含 `~1`，说明是短路径。

**修复**：
```cmd
setx TEMP "C:\Users\Qiang Tang\AppData\Local\Temp"
setx TMP "C:\Users\Qiang Tang\AppData\Local\Temp"
```
重启所有终端和应用后生效。

**原理**：短路径和长路径指向同一个物理目录，改的只是"写法"，不会丢失任何数据。

---

### 回调函数（Callback）是解耦的核心手段

```python
# telegram_channel.py 不需要知道 handle_message 是什么
def start_polling(on_message):       # 只知道它是个函数
    response = on_message(chat_id, text)  # 需要时调用
```

```python
# gateway.py 不需要知道 Telegram API 怎么用
start_polling(handle_message)        # 把自己的函数交给 Channel
```

两边都只依赖"函数签名"（接口），不依赖对方的实现细节。这是解耦的最简单形式。

OpenClaw 里有完整的 Hook 系统（`src/plugins/hooks.ts`），支持 `message_received`、`before_agent_start` 等几十个钩子，是这个 Callback 模式的生产级扩展。

---

### Always-On vs On-Demand 的根本差异

| | On-Demand（Claude Code） | Always-On（OpenClaw / mini-claw） |
|--|--|--|
| 触发方式 | 人坐在电脑前启动 | 手机发消息随时触发 |
| 进程生命周期 | 用完即退出 | 常驻，永远不退出 |
| 记忆 | 可以丢失（下次重新开始） | 需要持久化（重启不丢失） |
| 定时任务 | 做不到 | 自然支持（进程一直在跑） |
| 多用户 | 单用户 | 需要会话隔离 |

`infinity_polling()` 是 Always-On 的最底层体现——那个死循环就是"常驻"的本质。

---

### OpenClaw 与 mini-claw 架构对应表

| mini-claw 文件 | OpenClaw 对应 | 职责 |
|---------------|--------------|------|
| `gateway.py` | `src/gateway/server.ts` + `boot.ts` | 入口、路由、会话管理 |
| `telegram_channel.py` | `extensions/telegram/` | Telegram 适配器 |
| `agent.py` | `src/agents/` | LLM 调用、Agentic Loop |
| `tools.py` | 工具系统 | Agent 可调用的能力 |
| `sessions` 字典 | session 机制 | 会话隔离 |
| Chat ID 白名单 | binding 机制 | 授权用户绑定 |
| `WORKSPACE_PATH` | agent workspace | 文件访问边界 |
| `.env` | `.env.example` 模式 | 密钥配置管理 |

---

### mini-claw 和 Anthropic 官方 Remote Control 不谋而合

2026-02-25，Anthropic 发布了 **Claude Code Remote Control**——让你用手机控制本机运行的 Claude Code。

它的架构和 mini-claw 的核心思路**完全一样**：

```
mini-claw:        Telegram → Telegram 服务器（中转）→ 本机 Agent → 回 Telegram
Remote Control:   Claude App → Anthropic API（中转）→ 本机 Claude Code → 回 App
```

对比：

| | mini-claw | Claude Remote Control |
|--|--|--|
| 触发入口 | Telegram | Claude 官方 App |
| 中转层 | Telegram 服务器 | Anthropic API |
| 本机执行 | 自己的 Agent | Claude Code |
| 网络模式 | Polling 出站，不开入站端口 | HTTPS 出站，不开入站端口 |
| Always-On | ✅ 常驻后台 | ❌ Terminal 必须开着 |
| 自托管 | ✅ | ❌ 依赖 Anthropic 基础设施 |

**本质上 mini-claw 就是一个自托管版的 Remote Control**——用 Telegram 替代了 Anthropic 的中转服务器，用自己的 Agent 替代了 Claude Code。

安全设计上也不谋而合：两者都只做出站请求，本机不开任何入站端口。这不是巧合，而是"通过公共中转服务做远程控制"这个架构的自然结论。

> 参考：[VentureBeat](https://venturebeat.com/orchestration/anthropic-just-released-a-mobile-version-of-claude-code-called-remote) · [Claude Code Docs](https://code.claude.com/docs/en/remote-control) · [Simon Willison](https://simonwillison.net/2026/Feb/25/claude-code-remote-control/)

---

### 记忆即人格——用《记忆碎片》理解 LLM 的 History

电影《记忆碎片》（Memento，诺兰）里的主角只有短期记忆，每次睡醒昨天发生的事全部消失。他靠一张张卡片重建自己的世界观——卡片上写着"这是昨天的我给你写的，请相信它"。

**LLM 就是这个主角。**

- 每次 API 调用，Claude 没有任何记忆，完全从零开始
- `messages` 数组就是那叠卡片——把过去发生的一切"喂"给它，它才知道上下文
- `_load_history()` 就是每天早上翻出卡片重新读一遍
- `/reset` 就是把卡片全部销毁，从头开始认识世界

**记录的不只是对话，是完整的思维过程：**

每张"卡片"里装的不只是"你问了什么、我答了什么"，而是完整的 agentic 轨迹：
```
用户的问题
→ LLM 制定的计划
→ LLM 决定调用哪个工具、参数是什么
→ 工具执行的真实结果
→ 最终回答
```
下次加载历史，LLM 看到的是完整的上一轮"思考过程"，而不只是结论。

**记忆即人格：**

同样的模型权重，给它不同的 history，它就变成了不同的"人"：
- 记住了你所有代码偏好的助手
- 记住了你每天日程的秘书
- 记住了你私事的朋友

这些"人格"可以复制、分叉、篡改。《记忆碎片》里，最后发现有人一直在偷偷换他口袋里的卡片——这在 AI 里叫 **prompt injection**，是 Always-On 系统要防范的真实威胁。

**两层记忆的分工：**

| | 类比 | 作用 | 存活时间 |
|---|---|---|---|
| `sessions` dict（内存） | 今天的短期记忆 | 同一次运行中快速复用 | 进程重启即消失 |
| `.jsonl` 文件（磁盘） | 卡片 | 进程重启后恢复全部上下文 | 永久，直到 `/reset` |

> Claude Code 的 `/resume` 命令做的就是这件事：选一个 `.jsonl` 文件，把里面所有消息作为 `messages` 传给 API，Claude 就"接上了"上次的工作。那些文件就在 `~/.claude/projects/` 下，可以直接打开看。

---

### 决定的让渡：从任务队列优先级到 AI 治理

从"谁来决定任务队列的优先级"这个小问题，可以一路推演到一个很大的问题。

在 mini-claw 里，已经有很多决定从人让渡给了 AI：调用哪个工具、执行哪个步骤、用几轮 LLM 来完成任务。这些看起来都是合理的让渡——毕竟这些"小决定"占用人的脑力，交给 AI 效率更高。

但决定的层级是无限可分的。黄仁勋的"战略决定"，在总统眼里是执行细节。总统的决定，在历史学家眼里是更大趋势的细节。**每一层都可以被上一层称为 implementation**，你找不到一条自然的线，说线以上该是人，线以下才是 AI。

真正危险的不是 AI 做了某个决定，而是**人不再能理解那个决定**。PO 还能审 backlog，因为他能读懂每个 ticket。但如果 AI orchestrator 在一秒内做了一万个决定，"人保留最终决策权"就变成了幻觉。

关于"AI 治理国家"的幻想，有人觉得悲观（失控），有人觉得乐观（比腐败的人类政客更公正）。但两种人都跳过了一个问题：**AI 治理，优化的是什么目标函数？谁来定这个函数？**

也许人类唯一不能让渡的决定是：*我们作为人类，想要什么样的未来？* 不是怎么实现，不是谁来执行，而是那个最根本的 what。这个决定如果也外包出去，不是被 AI 统治，是人类放弃了作为人类存在的意义。

> 这段对话是从"为什么需要串行任务队列"开始的。

---

### Hooks / MCP / Skills — 三个容易混淆的概念

一句话区分：**Hooks 是事件响应，MCP/Tools 是能力扩展，Skills 是用户快捷指令。**

| | 触发方式 | 本质 | 例子 |
|---|---|---|---|
| **Hooks** | 系统事件自动触发 | 旁观者，悄悄监听 | "每次 Claude 写文件前，先备份" |
| **MCP / Tools** | LLM 判断需要时调用 | 给 Claude 新的手 | `read_file`、连接 PowerPoint API |
| **Skills** | 用户主动输入 `/命令` | Prompt 的快捷方式 | `/commit` 展开成一段 commit 规范 |

它们可以组合使用——一个好的 PPT 工具，可以是：MCP server 提供创建幻灯片的能力，Skill 提供"按什么步骤、什么格式做 PPT"的 prompt，两者结合才是完整的用户体验。

**护城河的不对称**：MCP server 需要写代码、对接 API，门槛高；Skill 只是 prompt，门槛极低。但随着 AI 把写代码的成本拉低，这个不对称可能会反转——代码变成 AI 的 labor，真正需要"人"的反而是理解用户真正想要什么、知道什么时候该做什么。

---

### 任务队列：简陋实现 vs 实际工程实践

mini-claw 的串行队列是最简单的 FIFO（先进先出）——绝对公平，按到达顺序处理，没有任何优先级概念。

**FIFO 的局限**

正在执行的任务（LLM 已经在跑）确实无法中断。但还在队列里等待的任务完全可以重新排序——它们还没碰到 LLM，只是在等。换成 `PriorityQueue`，每条消息带一个优先级数字，worker 每次取优先级最高的那条，就实现了优先级调度。这本质上和操作系统的进程调度一样：CPU 同一时间只跑一个进程，但调度器决定谁先上。

**谁来判断优先级？**

这是真正的工程问题。常见的几种做法：

| 方式 | 说明 |
|------|------|
| 用户自己标注 | 发消息时加"！"或用特殊命令 |
| 规则判断 | 关键词匹配，如"急"、"blocking" |
| LLM 判断 | 让一个小模型读消息内容打分 |
| 专职 PO Agent | 独立的 orchestrator agent 负责优先级决策 |

**Orchestrator-Worker 模式**

最后一种是真正的多 agent 编排：PO Agent 不干活，只管"什么时候做什么"；Worker Agent 只执行，不思考优先级。类比软件团队：PO 管 what & when，工程师管 how。

```
用户消息 → [PO Agent：判断优先级、分配任务] → [Worker Agent 1]
                                             → [Worker Agent 2]
```

LangGraph 的 supervisor 节点、OpenAI Swarm 的 handoff 机制，本质上都是这个模式。这也是为什么"多 agent 编排"是目前最热的话题——单个 agent 能力有限，PO + 多个专职 worker 组合起来已经很接近一个小团队了。

---

### 换马甲 vs 真正的 Multi-Agent

"Multi-agent"这个词在业界用得很乱，有必要区分两种本质不同的东西。

**换马甲（mode switching）**：同一个 agent 实例，同一段 history，只是 system prompt 或工具集不同。`/chat` 和 `/code` 模式切换就是这个——本质是一个 agent 的不同状态，不是多个 agent。

**真正的 multi-agent**：多个独立的 agent 实例，各自有自己的 history，可以并行运行，互相传消息协调。mini-claw 里每个 chat_id 对应一个独立的 Agent 实例，这才是工程意义上的多 agent——哪怕它们的 system prompt 完全一样。

| | 换马甲 | 多实例 |
|---|---|---|
| history | 共享 | 各自独立 |
| 并行 | 不能 | 可以 |
| 互相通信 | 不需要 | 可以协调 |
| 本质 | 同一个人换衣服 | 不同的人 |

真正有意思的 multi-agent 是后者——多个实例并行跑，一个 agent 的输出成为另一个 agent 的输入。这是 OpenClaw 里 task queue 和 agent orchestration 要解决的核心问题。很多被称为"multi-agent"的系统，其实只是换马甲。

---

## 待实现 / 深入方向

- [x] 持久化会话历史（目前内存存储，重启丢失）→ 对应 coding-agent Step 4 后的自然延伸
- [ ] 消息处理中显示"typing..."状态（已有 `send_chat_action`，但 Agent 跑完才回复，中间无反馈）
- [ ] Webhook 替代 Polling（需要公网地址，更适合生产）
- [ ] 多 Channel 支持（加一个 `discord_channel.py` 验证 Adapter 模式的可扩展性）
- [ ] 定时任务（`/remind 明天早上8点 提醒我开会`）→ Always-On 的典型场景

---

## 下一个项目：Claude Code ↔ mini-claw 共享上下文

**背景**：路上用 mini-claw 和 bot 聊项目，回到电脑前用 Claude Code 编程。两个系统目前是隔离的，希望它们共享上下文——不只是干净的学习笔记，而是对话的质感：类比、来回推敲的过程、一起想出来的东西。

**核心设计**：一个 `JOURNAL.md` 文件，介于"完整聊天记录"和"学习笔记"之间。

```
Claude Code session 结束  →  我把精华整理进 JOURNAL.md（结论 + 有意思的类比 + 好问题）
mini-claw 路上聊          →  bot 启动时读 JOURNAL.md，知道项目现状
路上 brainstorm 出结论    →  /note 命令追加进 JOURNAL.md
下次 Claude Code 开始     →  读 JOURNAL.md，接上上次
```

**待实现**：
- [ ] `agent.py`：启动时读 `JOURNAL.md` 注入 system prompt
- [ ] `gateway.py` + `tools.py`：加 `/note` 命令，安全地追加写入文件
- [ ] 约定 `JOURNAL.md` 的写作风格（不是流水账，是值得留下来的东西）
