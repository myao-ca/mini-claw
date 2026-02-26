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

from agent import Agent
from telegram_channel import start_polling

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


def get_or_create_session(chat_id: int) -> Agent:
    """获取或创建该 chat_id 的 Agent 会话"""
    if chat_id not in sessions:
        sessions[chat_id] = Agent()
    return sessions[chat_id]


# ============================================================
# 消息路由
#
# 对应 OpenClaw：dispatchReplyFromConfig → getReplyFromConfig
# ============================================================

def handle_message(chat_id: int, text: str) -> str:
    """
    消息路由核心：收到消息 → 找到对应 Agent → 返回回复

    内置两个特殊命令：
      /start  — 欢迎语
      /reset  — 清空当前会话的对话历史
    """
    text = text.strip()

    if text == "/start":
        return (
            "👋 Mini-Claw 已启动！\n\n"
            "我是一个只读的编程助手，可以帮你：\n"
            "• 读取和分析代码文件\n"
            "• 查看目录结构\n"
            "• 回答编程问题\n\n"
            "/reset — 清空对话历史，重新开始"
        )

    if text == "/reset":
        if chat_id in sessions:
            sessions[chat_id].reset()
        return "✅ 对话已重置"

    # 路由到 Agent
    agent = get_or_create_session(chat_id)
    return agent.run(text)

    # 临时测试用（验证 Telegram 连接正常后删掉）
    # return "hi!"


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    print("🚀 Mini-Claw Gateway 启动中...")
    start_polling(handle_message)
