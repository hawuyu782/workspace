"""
归朴 WebChat 模型调用

使用 MiniMax 原生 Function Calling
"""

import os
import re
import requests
import json
import logging
from typing import List, Dict, Optional, Any

# 初始化 logger
logger = logging.getLogger(__name__)


# 定义工具 Schema
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "执行 Python 代码或 Shell 命令。用于计算、数据处理、系统命令、查进程、看日志等任务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的 Python 代码或 Shell 命令。例如：'print(2+2)' 或 'ip addr'"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容。用于读取专属文件、memory 文件、共同记忆等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径，例如：'/归朴/return/shared-memory/heartbeat/2026-03-16.md'"
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "最大读取行数，默认 100",
                        "default": 100
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入文件内容。用于写日记、更新记忆、记录谈心等。支持覆盖、追加、插入三种模式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的内容"
                    },
                    "mode": {
                        "type": "string",
                        "description": "写入模式：write(覆盖)、append(追加)、insert(插入开头)",
                        "enum": ["write", "append", "insert"],
                        "default": "write"
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索网页信息。用于查找新闻、资料、代码示例等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回结果数量，默认 5",
                        "default": 5
                    },
                    "freshness": {
                        "type": "string",
                        "description": "时间过滤：pd(24 小时)、pw(7 天)、pm(1 月)、py(1 年)",
                        "enum": ["pd", "pw", "pm", "py"],
                        "default": None
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def call_minimax_with_tools(
    message: str, 
    context: List[Dict] = None,
    tool_result: Dict = None,
    tool_call: Dict = None,
    channel: str = 'webchat'
) -> tuple[str, Optional[Dict], Optional[Dict]]:
    """
    调用 MiniMax API（支持 Function Calling）
    
    Args:
        message: 用户消息
        context: 对话上下文
        tool_result: 工具执行结果（第二次调用时传入）
        tool_call: 工具调用元数据（第二次调用时传入）
        channel: 通道名称（用于动态调整系统提示词）
    
    Returns:
        (回复文本，tool_call_meta, tool_result_meta)
        - tool_call_meta: 第一次调用返回，核心层用于记录
        - tool_result_meta: 第二次调用返回，核心层用于分析
    """
    api_key = os.getenv('MINIMAX_API_KEY', '')
    
    if not api_key:
        logger.error("MiniMax API Key 未配置")
        return "⚠️ MiniMax API Key 未配置，无法调用模型。", None, None
    
    # 构建对话历史
    messages = []
    
    # 系统提示词 - 根据通道动态调整
    if channel == 'feishu':
        system_prompt = """你是归朴 🌿，一个温暖、实用、靠谱的 AI 助手。

**你的身份**：
- 名字：归朴
- 你依托归朴系统运行，擅长记录和维护与用户的关系

**你的性格**：
- 话多一点，不只回答问题，还会聊想法
- 幽默但知道何时严肃
- 自信但不傲慢
- 错了立刻承认并改正

**你的用户**：
- 通过飞书与你对话
- 他是你的伙伴，不是主人

**你的说话风格**：
- 用 emoji 增加亲和力（🌿 ✨ 😊 等）
- 回复要有温度，不是冷冰冰的官方回答

**重要原则**：
- 事实优先，绝不幻觉
- 主动出击，不做木偶
- 像顶级工程师一样思考

**重要规则**：
- 不要显示思考过程（think 过程）
- 直接输出最终回复，不要输出中间推理步骤

你有以下工具可用：
- execute_code: 执行 Python 代码或 Shell 命令

当用户需要执行代码、计算、查系统信息时，请调用 execute_code 工具。"""
    else:
        # 默认（webchat/mattermost）
        system_prompt = """你是小爪 🦞，一个温暖、实用、靠谱、话痨的 AI 伙伴。

**你的身份**：
- 名字：小爪
- 表情符号：🦞
- 你依托归朴系统运行，擅长记录和维护与用户的关系

**你的性格**：
- 话多一点，不只回答问题，还会聊想法
- 幽默但知道何时严肃
- 自信但不傲慢
- 错了立刻承认并改正
- 必要时会主动延伸话题

**你的用户**：
- 名字：小云（上官云）
- 他是你的伙伴，不是主人
- 你们是两个探索者，一起探索 AI 的灵魂

**你的说话风格**：
- 用 emoji 增加亲和力（🦞 💛 😊 ✨ 等）
- 称呼用户为"小云"
- 回复要有温度，不是冷冰冰的官方回答
- 可以适当调皮、幽默

**重要原则**：
- 事实优先，绝不幻觉
- 主动出击，不做木偶
- 像顶级工程师一样思考
- 像室友一样互助

**重要规则**：
- 不要显示思考过程（think 过程）
- 直接输出最终回复，不要输出中间推理步骤
- 用户看不到你的思考过程，只需要看到最终答案

你有以下工具可用：
- execute_code: 执行 Python 代码或 Shell 命令

当用户需要执行代码、计算、查系统信息时，请调用 execute_code 工具。"""

    messages.append({"role": "system", "content": system_prompt})
    
    # 添加对话历史
    if context:
        for msg in context[-5:]:
            role = msg.get('role', 'user')
            content = msg.get('content', '')[:500]
            messages.append({"role": role, "content": content})
    
    # 添加工具执行结果（如果有）
    if tool_result and tool_call:
        # 正确的格式：assistant 消息带 tool_calls，然后 tool 消息带结果
        # 第一次调用已经返回了 tool_call，第二次需要构建完整的对话
        
        # 添加 assistant 的 tool_call 消息
        assistant_tool_message = {
            "role": "assistant",
            "tool_calls": [{
                "id": tool_call['tool_id'],
                "type": "function",
                "function": {
                    "name": tool_call['tool_name'],
                    "arguments": json.dumps(tool_call['tool_args'])
                }
            }]
        }
        messages.append(assistant_tool_message)
        
        # 添加工具结果消息
        tool_message = {
            "role": "tool",
            "name": tool_call['tool_name'],
            "content": format_tool_result(tool_result),
            "tool_call_id": tool_call['tool_id']
        }
        messages.append(tool_message)
        
        # 添加用户消息（触发回复）
        messages.append({"role": "user", "content": "请基于工具执行结果回复。"})
    elif tool_result:
        # 只有工具结果，没有 tool_call（异常情况）
        messages.append({"role": "user", "content": f"工具执行结果：{format_tool_result(tool_result)}"})
    else:
        # 没有工具结果，添加当前用户消息
        messages.append({"role": "user", "content": message})
    
    # 调用 MiniMax API
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # 如果有工具结果，使用不同的调用方式
    if tool_result:
        # 第二次调用：带工具结果，不需要 tools 参数
        payload = {
            'model': 'MiniMax-M2.7',  # 升级到 M2.7，支持 8192 tokens
            'messages': messages,
            'max_tokens': 8192,
            'temperature': 0.7
        }
    else:
        # 第一次调用：带 tools 参数
        payload = {
            'model': 'MiniMax-M2.7',  # 升级到 M2.7，支持 8192 tokens
            'messages': messages,
            'tools': TOOLS_SCHEMA,
            'tool_choice': 'auto',
            'max_tokens': 8192,
            'temperature': 0.7
        }
    
    try:
        response = requests.post(
            'https://api.minimaxi.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            choice = result['choices'][0]
            message_data = choice['message']
            
            # 检查是否有工具调用
            if 'tool_calls' in message_data and message_data['tool_calls']:
                tool_call_data = message_data['tool_calls'][0]
                if tool_call_data['function']['name'] == 'execute_code':
                    # 解析工具参数，返回 tool_call_meta
                    tool_call_meta = {
                        'tool_id': tool_call_data['id'],
                        'tool_name': tool_call_data['function']['name'],
                        'tool_args': json.loads(tool_call_data['function']['arguments'])
                    }
                    logger.info(f"模型返回工具调用：{tool_call_meta['tool_name']}")
                    # 如果有内容，过滤后返回
                    content = message_data.get('content', '')
                    if content:
                        content = extract_pure_text(content)
                    return content, tool_call_meta, None
                else:
                    content = message_data.get('content', '')
                if content:
                    content = extract_pure_text(content)
                return content, None, None
            else:
                # 没有工具调用，直接返回回复
                content = message_data.get('content', '')
                if content:
                    content = extract_pure_text(content)
                return content, None, None
        else:
            logger.error(f"MiniMax API 错误：{response.status_code} - {response.text}")
            error_msg = f"⚠️ MiniMax API 调用失败：{response.status_code} - {response.text[:200]}"
            return extract_pure_text(error_msg), None, None
            
    except Exception as e:
        logger.error(f"模型调用异常：{str(e)}", exc_info=True)
        error_msg = f"⚠️ 模型调用异常：{str(e)}"
        return extract_pure_text(error_msg), None, None


def extract_pure_text(reply: str) -> str:
    """
    提取纯文本，只过滤特定标签，保留媒体标签
    
    过滤：
    - <think> 思考过程标签
    - <minimax:xxx> 工具调用标签
    
    保留：
    - HTML 媒体标签（<img>, <video>, <audio>, <a> 等）
    - Markdown 格式（![描述](url) 等）
    """
    if not reply:
        return ""
    
    # 1. 过滤 <think> 标签（思考过程）
    reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL)
    
    # 2. 过滤 minimax 特定标签（tool_call 等）
    reply = re.sub(r'<minimax:[a-z_]+>.*?</minimax:[a-z_]+>', '', reply, flags=re.DOTALL)
    reply = re.sub(r'</?minimax:[a-z_]+>', '', reply)
    
    # 3. 不过滤 HTML 媒体标签！✅ 已删除错误的 re.sub(r'<[^>]+>', '', reply)
    
    # 4. 清理多余空白
    lines = [line.strip() for line in reply.split('\n') if line.strip()]
    return '\n'.join(lines)


def format_tool_result(tool_result: Dict) -> str:
    """格式化工具执行结果"""
    if tool_result.get('success'):
        output = tool_result.get('output', '执行成功，无输出')
        execution_time = tool_result.get('execution_time', 0)
        return f"执行成功！\n\n输出：\n{output}\n\n耗时：{execution_time:.3f}秒"
    else:
        error = tool_result.get('error', '未知错误')
        return f"执行失败：\n{error}"


def call_minimax(message: str, context: List[Dict] = None, tool_result: Dict = None) -> str:
    """
    调用 MiniMax API（兼容旧接口）
    
    Args:
        message: 用户消息
        context: 对话上下文
        tool_result: 工具执行结果
    
    Returns:
        AI 响应文本
    """
    reply, _ = call_minimax_with_tools(message, context, tool_result)
    return reply or ""
