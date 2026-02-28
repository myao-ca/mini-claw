"""
Hook 系统

对应 OpenClaw：src/plugins/hooks.ts

在系统关键时间点自动触发注册的回调函数，
不需要修改核心代码就能扩展行为。

支持的事件：
  message_received  — 消息进来时        data: {chat_id, text}
  before_agent_run  — agent 开始处理前  data: {chat_id, text, mode}
  after_reply       — 回复发出后        data: {chat_id, text, reply}
"""

import logging

logger = logging.getLogger(__name__)

# 事件 → 回调函数列表
_hooks: dict[str, list] = {}


def register(event: str, callback) -> None:
    """注册一个 hook 回调"""
    if event not in _hooks:
        _hooks[event] = []
    _hooks[event].append(callback)
    logger.debug(f"hook 注册：{event} → {callback.__name__}")


def fire(event: str, data: dict) -> None:
    """触发某个事件，依次调用所有注册的回调"""
    for callback in _hooks.get(event, []):
        try:
            callback(data)
        except Exception as e:
            logger.error(f"hook 执行失败 [{event}] {callback.__name__}: {e}")
