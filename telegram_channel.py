"""
Telegram 频道适配器

对应 OpenClaw：extensions/telegram/

OpenClaw 里每个平台（Telegram/WhatsApp/Discord...）都有一个这样的适配器。
职责都相同：
  1. 连接平台 API
  2. 接收消息，做安全检查
  3. 把回复发回给用户

这一层叫做 "Channel Adapter"，它屏蔽了各平台的差异，
让上层的 Gateway 不需要关心消息从哪个平台来的。
"""

import os
import telebot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = int(os.environ.get("TELEGRAM_ALLOWED_CHAT_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN)


def is_authorized(message) -> bool:
    """
    安全检查：只处理授权用户的消息。

    对应 OpenClaw：账号绑定（binding）机制。
    OpenClaw 里可以给不同用户绑定不同的 Agent，
    mini-claw 简化成：只有一个授权用户（你自己）。
    """
    return message.chat.id == ALLOWED_CHAT_ID


def send_reply(chat_id: int, text: str):
    """
    把回复发回 Telegram。

    Telegram 单条消息上限 4096 字符，超出自动分段发送。
    """
    max_length = 4096
    for i in range(0, len(text), max_length):
        bot.send_message(chat_id, text[i:i + max_length])


def start_polling(on_message):
    """
    启动轮询，持续监听 Telegram 消息。

    on_message：回调函数，由 gateway.py 提供
                签名：(chat_id: int, text: str) -> str
                负责把消息路由到 Agent，返回回复

    对应 OpenClaw：Gateway 启动时注册各个 Channel 的监听器。
    OpenClaw 用 WebSocket 长连接，mini-claw 用轮询，效果一样。
    """
    @bot.message_handler(func=lambda m: True)
    def handle(message):
        # 拒绝未授权用户
        if not is_authorized(message):
            bot.send_message(message.chat.id, "⛔ 未授权")
            return

        text = message.text or ""

        # 告诉用户 bot 正在处理（Agent 跑起来要几秒）
        bot.send_chat_action(message.chat.id, "typing")

        # 交给 gateway 路由到 Agent，拿回回复
        response = on_message(message.chat.id, text)

        # 发回 Telegram
        send_reply(message.chat.id, response)

    print("📡 Telegram 监听已启动，等待消息...")
    bot.infinity_polling()
