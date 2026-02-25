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

import time
import anthropic as anthropic_lib
from anthropic import Anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed
from tools import get_all_tools, execute_tool
from config import ANTHROPIC_API_KEY


class Agent:
    def __init__(self, max_turns: int = 10):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"
        self.max_turns = max_turns

        self.system_prompt = """你是一个编程助手。你可以帮助用户：
- 阅读和分析代码文件
- 查看项目目录结构
- 回答编程问题

使用 read_file 读取文件，list_files 查看目录。
如果需要多个操作，可以多次使用工具。
回答要简洁、准确。"""

        self.conversation_history = []

    def run(self, user_message: str) -> str:
        """
        运行 Agent，返回最终回复字符串。

        和 coding-agent 版本的关键区别：
          - 不直接 print，而是收集结果返回
          - 因为调用方（gateway）需要拿到结果再发给用户
        """
        # --- Phase 1: 规划 ---
        plan = self._create_plan(user_message)

        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": f"我的执行计划：\n\n{plan}"})
        self.conversation_history.append({"role": "user", "content": "好，请严格按照计划执行，完成后汇报最终结果。"})

        # --- Phase 2: 执行 ---
        turn = 0
        while turn < self.max_turns:
            turn += 1

            try:
                response, response_text = self._call_llm(self.conversation_history)
            except Exception as e:
                return f"[错误] LLM 调用失败：{str(e)}"

            if response.stop_reason == "end_turn":
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                return response_text

            elif response.stop_reason == "tool_use":
                self._process_tool_calls(self.conversation_history, response)

            else:
                return f"[错误] 意外的 stop_reason: {response.stop_reason}"

        return f"[警告] 达到最大轮次 {self.max_turns}，任务可能未完成。"

    def reset(self):
        """清空对话历史"""
        self.conversation_history = []

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
            system="你是一个任务规划助手。将用户任务分解为清晰的执行步骤。只输出步骤列表，简洁明了，不执行任何操作。",
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
                    system=self.system_prompt,
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
        messages.append({
            "role": "assistant",
            "content": response.content
        })

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

        messages.append({
            "role": "user",
            "content": tool_results
        })
