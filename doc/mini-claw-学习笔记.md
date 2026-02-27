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
⬜ Step 7-8    记忆与状态（续）
⬜ Step 9-11   架构升级
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

| 编号 | 核心竞争力 | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Step 6 |
|------|-----------|--------|--------|--------|--------|--------|--------|
| ① | Trigger Layer | | | | 重点 | 验证 | |
| ② | Channel Adapter Pattern | | | | 重点 | 验证 | |
| ③ | Gateway / Message Routing | | | | 重点 | 验证 | |
| ④ | Session Management | | | | 简陋 | | 持久化 |
| ⑤ | Security & Permissions | | 重点 | | | | |
| ⑥ | Config Management | 重点 | 扩展 | | | | |
| ⑦ | Always-On Service | | | | 重点 | 验证 | |
| ⑧ | Callback / Decoupling | | | | 重点 | | |

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

## 待实现 / 深入方向

- [x] 持久化会话历史（目前内存存储，重启丢失）→ 对应 coding-agent Step 4 后的自然延伸
- [ ] 消息处理中显示"typing..."状态（已有 `send_chat_action`，但 Agent 跑完才回复，中间无反馈）
- [ ] Webhook 替代 Polling（需要公网地址，更适合生产）
- [ ] 多 Channel 支持（加一个 `discord_channel.py` 验证 Adapter 模式的可扩展性）
- [ ] 定时任务（`/remind 明天早上8点 提醒我开会`）→ Always-On 的典型场景
