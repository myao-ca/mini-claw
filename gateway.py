"""
Gateway — 主循环

对应 OpenClaw：src/gateway/server.ts + boot.ts

职责：
  1. 启动时初始化所有组件
  2. 把消息从 Channel 路由到 Agent
  3. 把 Agent 的回复路由回 Channel
  4. 管理 Agent 会话的生命周期

这是整个系统的"控制中枢"，Channel 和 Agent 都不互相认识，
只认识 Gateway。
"""

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

from queue import Queue
from threading import Thread

from agent import Agent
from telegram_channel import start_polling
import hooks

# ============================================================
# 会话管理
#
# 对应 OpenClaw：session 机制
#
# 每个 chat_id 对应一个独立的 Agent 实例，
# Agent 实例持有自己的 conversation_history，
# 所以不同用户的对话完全隔离。
#
# OpenClaw 用 session key（如 agent:main:direct:telegram:123456）
# mini-claw 直接用 chat_id 做 key，效果一样。
# ============================================================

sessions: dict[int, Agent] = {}

# ============================================================
# 串行任务队列
#
# 对应 OpenClaw：Task Channel Queue
#
# 每个 session 一个队列 + 一个后台 worker 线程。
# 消息进来先入队，worker 串行取出处理，消除竞态。
# 不同用户之间互不影响，仍然并行。
# ============================================================

task_queues: dict[int, Queue] = {}


def get_or_create_session(chat_id: int) -> Agent:
    """获取或创建该 chat_id 的 Agent 会话"""
    if chat_id not in sessions:
        sessions[chat_id] = Agent(str(chat_id))
    return sessions[chat_id]


def _worker(chat_id: int, q: Queue):
    """每个 session 的串行 worker 线程"""
    while True:
        text, response_q = q.get()
        try:
            agent = get_or_create_session(chat_id)
            hooks.fire("before_agent_run", {"chat_id": chat_id, "text": text, "mode": agent.mode})
            result = agent.run(text)
            logger.info(f"[{chat_id}] <<< {result[:80]!r}{'...' if len(result) > 80 else ''}")
            hooks.fire("after_reply", {"chat_id": chat_id, "text": text, "reply": result})
        except Exception as e:
            result = f"[错误] {e}"
            logger.error(f"[{chat_id}] worker 异常: {e}")
        finally:
            response_q.put(result)
            q.task_done()


def get_or_create_queue(chat_id: int) -> Queue:
    """获取或创建该 chat_id 的任务队列，首次创建时启动 worker 线程"""
    if chat_id not in task_queues:
        q = Queue()
        task_queues[chat_id] = q
        t = Thread(target=_worker, args=(chat_id, q), daemon=True)
        t.start()
        logger.info(f"[{chat_id}] 新建 session worker")
    return task_queues[chat_id]


# ============================================================
# 消息路由
#
# 对应 OpenClaw：dispatchReplyFromConfig → getReplyFromConfig
# ============================================================

def handle_message(chat_id: int, text: str) -> str:
    """
    消息路由核心：收到消息 → 找到对应 Agent → 返回回复

    内置命令直接返回，不走队列。
    普通消息入队，等 worker 串行处理完再返回。
    """
    text = text.strip()
    logger.info(f"[{chat_id}] >>> {text!r}")
    hooks.fire("message_received", {"chat_id": chat_id, "text": text})

    if text == "/start":
        return (
            "👋 Mini-Claw 已启动！\n\n"
            "我是一个只读的编程助手，可以帮你：\n"
            "• 读取和分析代码文件\n"
            "• 查看目录结构\n"
            "• 回答编程问题\n\n"
            "/chat  — 切换到轻松聊天模式\n"
            "/code  — 切换回编程助手模式\n"
            "/reset — 清空对话历史，重新开始"
        )

    if text == "/reset":
        if chat_id in sessions:
            sessions[chat_id].reset()
        return "✅ 对话已重置"

    if text == "/chat":
        agent = get_or_create_session(chat_id)
        agent.mode = "chat"
        return "💬 已切换到聊天模式，随便聊吧"

    if text == "/code":
        agent = get_or_create_session(chat_id)
        agent.mode = "code"
        return "💻 已切换到编程助手模式"

    # 普通消息入队，等 worker 处理完返回
    response_q: Queue = Queue()
    get_or_create_queue(chat_id).put((text, response_q))
    return response_q.get()  # 阻塞等待，直到 worker 处理完


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    # 注册 hook（测试用）
    hooks.register("after_reply", lambda d: print(f"HOOK: {d['chat_id']} 收到了回复"))
    
    print("🚀 Mini-Claw Gateway 启动中...")
    start_polling(handle_message)
