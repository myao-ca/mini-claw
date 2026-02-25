"""
工具系统

⭐ 核心竞争力 ② Tool Design
   - 装饰器模式让工具注册更简洁
   - 每个工具的 schema 描述要清晰（影响 LLM 能否正确使用）
   - 工具粒度要合适

mini-claw 版本：只保留只读工具（safe by default）
   - read_file：读文件
   - list_files：列目录
   危险工具（execute_code、write_file）暂不开放
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 安全边界
# ============================================================

_WORKSPACE = os.path.realpath(os.environ.get("WORKSPACE_PATH", ""))

def _is_safe_path(path: str) -> bool:
    """
    检查路径是否在 WORKSPACE_PATH 内。

    用 realpath() 先解析掉 ../../../ 等路径穿越攻击，
    再检查是否以 WORKSPACE 开头。

    对应 OpenClaw：agent 的 workspace 边界限制。
    """
    if not _WORKSPACE:
        return False  # 未配置 WORKSPACE_PATH，一律拒绝
    resolved = os.path.realpath(path)
    return resolved.startswith(_WORKSPACE)


# ============================================================
# 工具注册表
# ============================================================

_tool_registry = {}


def tool(name: str, description: str, params: dict):
    """
    工具注册装饰器

    用法：
        @tool(
            name="read_file",
            description="读取文件内容",
            params={
                "path": {"type": "string", "description": "文件路径"}
            }
        )
        def read_file(path: str) -> str:
            ...
    """
    def decorator(func):
        schema = {
            "name": name,
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": {
                    k: {sk: sv for sk, sv in v.items() if sk != "optional"}
                    for k, v in params.items()
                },
                "required": [k for k, v in params.items() if not v.get("optional", False)]
            }
        }
        _tool_registry[name] = {
            "schema": schema,
            "function": func
        }
        return func
    return decorator


# ============================================================
# 工具定义
# ============================================================

@tool(
    name="read_file",
    description="读取指定路径的文件内容。当你需要查看文件代码或内容时使用此工具。",
    params={
        "path": {
            "type": "string",
            "description": "要读取的文件路径"
        }
    }
)
def read_file(path: str) -> str:
    try:
        if not _is_safe_path(path):
            return f"错误：路径超出允许的工作目录范围 - {path}"
        if not os.path.exists(path):
            return f"错误：文件不存在 - {path}"
        if not os.path.isfile(path):
            return f"错误：路径不是文件 - {path}"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取文件失败：{str(e)}"


@tool(
    name="list_files",
    description="列出指定目录下的文件和子目录。当你需要了解项目结构时使用此工具。",
    params={
        "path": {
            "type": "string",
            "description": "要列出内容的目录路径，默认为当前目录",
            "optional": True
        }
    }
)
def list_files(path: str = ".") -> str:
    try:
        if not _is_safe_path(path):
            return f"错误：路径超出允许的工作目录范围 - {path}"
        if not os.path.exists(path):
            return f"错误：目录不存在 - {path}"
        if not os.path.isdir(path):
            return f"错误：路径不是目录 - {path}"
        entries = os.listdir(path)
        result = []
        for entry in sorted(entries):
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                result.append(f"  [目录] {entry}/")
            else:
                size = os.path.getsize(full_path)
                result.append(f"  [文件] {entry} ({size} bytes)")
        return f"目录 {path} 的内容：\n" + "\n".join(result)
    except Exception as e:
        return f"列出目录失败：{str(e)}"


# ============================================================
# 对外接口
# ============================================================

def get_all_tools() -> list:
    """获取所有工具的 schema 列表（传给 LLM）"""
    return [entry["schema"] for entry in _tool_registry.values()]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """执行指定工具"""
    if tool_name not in _tool_registry:
        return f"错误：未知工具 - {tool_name}"
    func = _tool_registry[tool_name]["function"]
    return func(**tool_input)
