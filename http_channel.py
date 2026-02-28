"""
HTTP 频道适配器

对应 OpenClaw：多 Channel 并行

职责与 telegram_channel.py 完全相同：
  1. 监听外部输入（这里是 HTTP POST 请求）
  2. 调用 gateway 提供的回调拿到回复
  3. 把回复返回给调用方

安全设计：只绑定 127.0.0.1，不对公网暴露端口。
适合本机调试、脚本自动化、与其他本机程序集成。
"""

import logging
from threading import Thread
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.logger.setLevel(logging.WARNING)   # 静默 Flask 自己的请求日志
app.json.ensure_ascii = False          # 回复中文直接显示，不转义成 \uXXXX

_on_message = None   # gateway 启动时注入


@app.route("/message", methods=["POST"])
def receive_message():
    """
    接收消息，路由到 gateway，返回回复。

    请求格式（JSON）：
        {"chat_id": 0, "text": "你好"}

    chat_id 可选，默认 0（HTTP 用户）。
    """
    data = request.get_json(silent=True) or {}
    chat_id = int(data.get("chat_id", 0))
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "text 不能为空"}), 400

    logger.info(f"[HTTP] chat_id={chat_id} text={text!r}")
    reply = _on_message(chat_id, text)
    return jsonify({"reply": reply})


@app.route("/health", methods=["GET"])
def health():
    """简单的健康检查接口"""
    return jsonify({"status": "ok"})


def start_http(on_message, host="127.0.0.1", port=5000):
    """
    启动 HTTP 服务器（后台线程），持续监听 HTTP 消息。

    on_message：回调函数，由 gateway.py 提供
                签名：(chat_id: int, text: str) -> str
    """
    global _on_message
    _on_message = on_message

    def run():
        app.run(host=host, port=port, use_reloader=False)

    t = Thread(target=run, daemon=True)
    t.start()
    print(f"🌐 HTTP 频道已启动：http://{host}:{port}/message")
