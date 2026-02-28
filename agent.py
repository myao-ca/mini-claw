"""
Agent 核心循环

Plan-and-Execute 模式：
  Phase 1: 规划阶段 — 不带工具的纯推理，生成执行计划
  Phase 2: 执行阶段 — 带工具的 Agentic Loop，遵循计划执行

mini-claw 版本改动：
  - run() 返回字符串结果，而不是直接 print
  - 去掉交互式 input() 确认（因为用户不在终端旁边）
  - 保留流式调用和重试逻辑
"""

import os
import json
import time
import anthropic as anthropic_lib
from anthropic import Anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from tools import get_all_tools, execute_tool

load_dotenv()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

logger = __import__("logging").getLogger(__name__)


MAX_HISTORY = 30   # 超过这个消息数触发压缩
KEEP_RECENT = 10   # 压缩时保留最近几条不动


class Agent:
    def __init__(self, session_id: str, max_turns: int = 10):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"
        self.max_turns = max_turns

        # 持久化：每个会话对应一个 .jsonl 文件
        # 对应 OpenClaw：.jsonl 会话存储
        self.session_file = Path("sessions") / f"{session_id}.jsonl"

        self.workspace = os.environ.get("WORKSPACE_PATH", "未配置")

        # 对话模式：code（编程助手）或 chat（轻松聊天）
        # 对应 OpenClaw：动态 system prompt 构建
        self.mode = "code"

        # 启动时从文件加载历史，恢复上次的对话上下文
        self.conversation_history = self._load_history()

    def run(self, user_message: str) -> str:
        """
        运行 Agent，返回最终回复字符串。

        和 coding-agent 版本的关键区别：
          - 不直接 print，而是收集结果返回
          - 因为调用方（gateway）需要拿到结果再发给用户
        """
        # 超过阈值则先压缩历史，对应 OpenClaw：compaction.ts
        if len(self.conversation_history) > MAX_HISTORY:
            self._compact_history()

        logger.info(f"mode={self.mode}  开始处理")
        # chat 模式跳过规划阶段，直接对话
        if self.mode == "chat":
            msg_user = {"role": "user", "content": user_message}
            self.conversation_history.append(msg_user)
            self._save_message(msg_user)
        else:
            # --- Phase 1: 规划 ---
            logger.info("Phase 1: 规划中...")
            plan = self._create_plan(user_message)

            msg_user = {"role": "user", "content": user_message}
            msg_plan = {"role": "assistant", "content": f"我的执行计划：\n\n{plan}"}
            msg_go = {"role": "user", "content": "好，请严格按照计划执行，完成后汇报最终结果。"}
            self.conversation_history.append(msg_user)
            self._save_message(msg_user)
            self.conversation_history.append(msg_plan)
            self._save_message(msg_plan)
            self.conversation_history.append(msg_go)
            self._save_message(msg_go)

        # --- Phase 2: 执行 ---
        turn = 0
        while turn < self.max_turns:
            turn += 1
            logger.info(f"Turn {turn}: 调用 LLM...")

            try:
                response, response_text = self._call_llm(self.conversation_history)
            except Exception as e:
                logger.error(f"LLM 调用失败: {e}")
                return f"[错误] LLM 调用失败：{str(e)}"

            if response.stop_reason == "end_turn":
                logger.info(f"Turn {turn}: end_turn，完成")
                msg_final = {"role": "assistant", "content": response.content}
                self.conversation_history.append(msg_final)
                self._save_message(msg_final)
                return response_text

            elif response.stop_reason == "tool_use":
                tool_names = [b.name for b in response.content if b.type == "tool_use"]
                logger.info(f"Turn {turn}: tool_use → {tool_names}")
                self._process_tool_calls(self.conversation_history, response)

            else:
                return f"[错误] 意外的 stop_reason: {response.stop_reason}"

        return f"[警告] 达到最大轮次 {self.max_turns}，任务可能未完成。"

    def _build_system_prompt(self) -> str:
        """
        动态构建 system prompt。

        每次调用 LLM 前现拼，注入当前时间、模式、记忆文件。
        对应 OpenClaw：每条消息处理前动态构建 system prompt。
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M %A")

        if self.mode == "chat":
            base = f"""你是用户的私人助手，当前时间：{now}。
正在进行轻松的对话，可以讨论任何话题：项目想法、头脑风暴、日常聊天。
不需要刻意使用工具，直接对话即可。"""
        else:
            base = f"""你是一个只读的编程助手，当前时间：{now}。你可以帮助用户：
- 阅读和分析代码文件
- 查看项目目录结构
- 回答编程问题

【重要限制】
- 你只能读取文件，不能修改、删除或创建任何文件
- 你只能访问工作目录内的文件：{self.workspace}
- 如果用户要求超出以上范围的操作，礼貌拒绝并说明原因

使用 read_file 读取文件，list_files 查看目录。"""

        # 加载记忆文件（如果存在）
        memory_file = Path("MEMORY.md")
        if memory_file.exists():
            memory = memory_file.read_text(encoding="utf-8").strip()
            if memory:
                base += f"\n\n## 记忆\n{memory}"

        return base

    def reset(self):
        """清空对话历史，同时删除持久化文件"""
        self.conversation_history = []
        if self.session_file.exists():
            self.session_file.unlink()

    def _compact_history(self):
        """
        压缩对话历史：把旧消息概括成摘要，只保留最近 KEEP_RECENT 条。

        对应 OpenClaw：compaction.ts
        压缩后重写整个 session 文件（不再是 append）。
        """
        old_messages = self.conversation_history[:-KEEP_RECENT]
        recent_messages = self.conversation_history[-KEEP_RECENT:]

        logger.info(f"压缩历史：{len(old_messages)} 条 → 摘要，保留最近 {len(recent_messages)} 条")

        # 让 LLM 概括旧消息
        summary_text = ""
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=1024,
                system="你是一个对话摘要助手。请将以下对话历史概括成简洁的摘要，保留关键信息和结论。",
                messages=[{
                    "role": "user",
                    "content": f"请概括以下对话：\n\n{json.dumps([self._serialize_message(m) for m in old_messages], ensure_ascii=False, indent=2)}"
                }]
            ) as stream:
                for text in stream.text_stream:
                    summary_text += text
        except Exception as e:
            logger.error(f"压缩失败，保持原历史：{e}")
            return

        # 用摘要替换旧消息，保留近期消息
        summary_msg = {
            "role": "user",
            "content": f"【以下是之前对话的摘要，请基于此继续】\n\n{summary_text}"
        }
        ack_msg = {
            "role": "assistant",
            "content": "明白，我已了解之前的对话背景，请继续。"
        }
        self.conversation_history = [summary_msg, ack_msg] + recent_messages

        # 重写整个 session 文件
        self.session_file.parent.mkdir(exist_ok=True)
        with open(self.session_file, "w", encoding="utf-8") as f:
            for msg in self.conversation_history:
                f.write(json.dumps(self._serialize_message(msg), ensure_ascii=False) + "\n")

        logger.info(f"压缩完成，history 从 {len(old_messages) + len(recent_messages)} 条压缩至 {len(self.conversation_history)} 条")

    def _load_history(self) -> list:
        """从 .jsonl 文件加载历史对话，加载时顺便清理多余字段"""
        if not self.session_file.exists():
            return []
        history = []
        with open(self.session_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    history.append(self._clean_content_blocks(json.loads(line)))
        return history

    def _clean_content_blocks(self, message: dict) -> dict:
        """
        清理消息 content 中多余的字段，只保留 API 协议字段。

        加载旧版 .jsonl 时修复因 SDK 升级引入的额外字段
        （如 citations、parsed_output、caller 等）。
        """
        content = message.get("content")
        if not isinstance(content, list):
            return message
        cleaned = []
        for block in content:
            if not isinstance(block, dict):
                cleaned.append(block)
                continue
            t = block.get("type")
            if t == "text":
                cleaned.append({"type": "text", "text": block["text"]})
            elif t == "tool_use":
                cleaned.append({"type": "tool_use", "id": block["id"],
                                 "name": block["name"], "input": block["input"]})
            else:
                cleaned.append(block)  # tool_result 等保持原样
        return {**message, "content": cleaned}

    def _serialize_message(self, message: dict) -> dict:
        """
        将消息序列化为 JSON 可存储格式。

        只保留 API 协议规定的核心字段，丢弃 SDK 版本特有的内部字段
        （不同版本 SDK 会在 TextBlock/ToolUseBlock 里加入不同字段，
        如 citations、parsed_output、caller 等，这些字段 API 不接受）。
        """
        content = message.get("content")
        if not isinstance(content, list):
            return message
        serialized = []
        for block in content:
            t = getattr(block, "type", None)
            if t == "text":
                serialized.append({"type": "text", "text": block.text})
            elif t == "tool_use":
                serialized.append({"type": "tool_use", "id": block.id,
                                   "name": block.name, "input": dict(block.input)})
            else:
                serialized.append(block)
        return {**message, "content": serialized}

    def _save_message(self, message: dict):
        """将单条消息追加写入 .jsonl 文件"""
        self.session_file.parent.mkdir(exist_ok=True)
        serializable = self._serialize_message(message)
        with open(self.session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(serializable, ensure_ascii=False) + "\n")

    def _create_plan(self, user_message: str) -> str:
        """规划阶段：不带工具的纯推理"""
        planning_messages = [{
            "role": "user",
            "content": f"请为以下任务制定简洁的执行计划（编号列表，不要执行，只列步骤）：\n\n{user_message}"
        }]

        plan_text = ""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=512,
            system=self._build_system_prompt() + "\n\n请将任务分解为清晰的执行步骤。只输出步骤列表，简洁明了，不执行任何操作。",
            messages=planning_messages
        ) as stream:
            for text in stream.text_stream:
                plan_text += text
        return plan_text

    def _call_llm(self, messages: list):
        """调用 LLM（流式），返回 (response, 文字内容)"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response_text = ""
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=4096,
                    system=self._build_system_prompt(),
                    tools=get_all_tools(),
                    messages=messages
                ) as stream:
                    for text in stream.text_stream:
                        response_text += text
                    response = stream.get_final_message()

                return response, response_text

            except anthropic_lib.RateLimitError:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

            except anthropic_lib.APIConnectionError:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

            except (anthropic_lib.AuthenticationError, anthropic_lib.BadRequestError):
                raise

    def _process_tool_calls(self, messages: list, response) -> None:
        """处理工具调用（并行执行）"""
        msg_assistant = {"role": "assistant", "content": response.content}
        messages.append(msg_assistant)
        self._save_message(msg_assistant)

        tool_blocks = [b for b in response.content if b.type == "tool_use"]

        results = {}

        def run_tool(block):
            return block.id, execute_tool(block.name, block.input)

        with ThreadPoolExecutor(max_workers=len(tool_blocks)) as executor:
            futures = {executor.submit(run_tool, block): block for block in tool_blocks}
            for future in as_completed(futures):
                tool_use_id, result = future.result()
                results[tool_use_id] = result

        tool_results = [
            {"type": "tool_result", "tool_use_id": block.id, "content": results[block.id]}
            for block in tool_blocks
        ]

        msg_results = {"role": "user", "content": tool_results}
        messages.append(msg_results)
        self._save_message(msg_results)
