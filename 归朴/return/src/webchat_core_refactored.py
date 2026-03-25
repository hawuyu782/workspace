"""
归朴 WebChat 核心 - 无状态版本

框架化重构后，核心层只负责处理逻辑，不管状态

职责：
1. 处理消息 → 返回回复
2. 工具调用（Function Calling 循环）
3. 标签过滤

不管什么：
- 不加载历史（框架层管）
- 不保存历史（框架层管）
- 不触发心跳（框架层管）
- 不管理关系状态（框架层管）
"""

import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

# 添加归朴路径
GUIPU_BASE = Path(__file__).parent.parent
if not GUIPU_BASE.exists():
    GUIPU_BASE = Path('/归朴/return')
sys.path.insert(0, str(GUIPU_BASE / 'src'))

from loguru import logger

# 导入工具模块
from tools.registry import get_tool
from tools.execute_code import execute_code
from memory.tool_logger import ToolLogger


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
    
    # 3. 不过滤 HTML 媒体标签！保留 <img>, <video>, <audio>, <a> 等
    
    # 4. 清理多余空白
    lines = [line.strip() for line in reply.split('\n') if line.strip()]
    return '\n'.join(lines)


class WebChatCore:
    """
    归朴核心（无状态版本）
    
    框架化后，核心只负责处理逻辑，不管状态
    """
    
    def __init__(self, user_id: str = 'default_user', channel: str = 'webchat', memory_base: Optional[Path] = None):
        """
        初始化归朴核心（简化版）
        
        Args:
            user_id: 用户 ID
            channel: 通道名称
            memory_base: 记忆目录（可选，框架层传入）
        """
        self.user_id = user_id
        self.channel = channel
        
        # 工具日志（用于记录工具调用）
        if memory_base:
            self.tool_logger = ToolLogger(memory_base / 'tool-calls')
        else:
            self.tool_logger = None
        
        logger.info(f"✅ 归朴核心已初始化（无状态版本）user_id={user_id}, channel={channel}")
    
    def process_message(self, message: str, context: List[Dict]) -> Dict:
        """
        处理用户消息（无状态核心）
        
        假设：context 已经是完整的（框架层已经准备好身份 + 历史）
        
        流程：
        1. 构建 messages（用于模型调用）
        2. Function Calling 循环
        3. 执行工具（如果需要）
        4. 记录工具调用
        5. 返回回复
        
        Args:
            message: 用户消息
            context: 完整上下文（框架层已经准备好）
                     包含：身份信息 + 历史对话
        
        Returns:
            {"reply": str, "tool_used": Optional[str], "tool_result": Optional[Dict]}
        """
        logger.info(f"🧠 处理消息：{message[:50]}...")
        
        # 1. 构建 messages（用于模型调用）
        messages = self._build_messages_for_fc(message, context)
        
        # 2. Function Calling 循环
        max_iterations = 10  # 最多 10 轮，给模型更多机会生成回复
        iteration = 0
        final_reply = ""
        tool_call_meta = None
        tool_result = None
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"🔄 第 {iteration} 轮对话")
            
            # Step 1: 调用模型
            reply, tool_calls = self._call_model_with_messages(messages)
            logger.info(f"✅ 模型响应完成 - 回复长度：{len(reply) if reply else 0}, 工具调用：{len(tool_calls) if tool_calls else 0}")
            
            # Step 2: 有文本回复且无工具调用，直接返回
            if reply and not tool_calls:
                final_reply = reply
                messages.append({"role": "assistant", "content": reply})
                break
            
            # Step 3: 有工具调用
            if tool_calls:
                tool_call_meta = {
                    'tool_id': tool_calls[0]['id'],
                    'tool_name': tool_calls[0]['function']['name'],
                    'tool_args': json.loads(tool_calls[0]['function']['arguments'])
                }
                
                logger.info(f"🛠️ 模型决定调用工具：{tool_call_meta['tool_name']}")
                
                # 执行工具
                tool_result = self._execute_tool(
                    tool_call_meta['tool_name'],
                    tool_call_meta['tool_args'].get('code', '')
                )
                
                # 添加 assistant 的 tool_call 消息
                messages.append({
                    "role": "assistant",
                    "tool_calls": tool_calls
                })
                
                # 添加工具结果消息
                messages.append({
                    "role": "tool",
                    "name": tool_call_meta['tool_name'],
                    "content": self._format_tool_result(tool_result),
                    "tool_call_id": tool_call_meta['tool_id']
                })
                
                # 记录工具调用
                self._log_tool_call(message, tool_call_meta, tool_result, reply)
                
                # 继续下一轮
                continue
        
        logger.info(f"✅ 模型响应：{final_reply[:50] if final_reply else '...'}...")
        
        # 过滤 reply，确保所有通道收到纯文本
        if final_reply:
            final_reply = extract_pure_text(final_reply)
        
        return {
            'reply': final_reply,
            'timestamp': datetime.now().isoformat(),
            'user_id': self.user_id,
            'channel': self.channel,
            'tool_used': tool_call_meta['tool_name'] if tool_call_meta else None,
            'tool_result': tool_result
        }
    
    def _build_messages_for_fc(self, message: str, context: List[Dict]) -> List[Dict]:
        """
        构建 Function Calling 用的完整 messages
        
        Args:
            message: 用户消息
            context: 历史对话上下文（包含身份信息和历史对话）
        
        Returns:
            完整的 messages 列表
        """
        messages = []
        
        # 1. 构建 system prompt
        system_prompt = """你是一个有帮助的助手，可以使用工具来帮助用户。

重要规则：
1. 使用工具后，必须基于工具执行结果生成回复给用户
2. 不要连续调用工具，每次调用工具后都要给用户回复
3. 如果工具执行成功，立即告诉用户结果
4. 如果工具执行失败，告诉用户发生了什么错误"""
        
        # 检查 context 中是否有身份信息（system role 的消息）
        identity_messages = []
        history_messages = []
        
        if context:
            for msg in context:
                if msg.get('role') == 'system':
                    # 身份信息
                    identity_messages.append(msg.get('content', ''))
                else:
                    # 历史对话
                    history_messages.append(msg)
        
        # 如果有身份信息，添加到 system prompt
        if identity_messages:
            system_prompt += "\n\n" + "\n\n".join(identity_messages)
        
        messages.append({"role": "system", "content": system_prompt})
        
        # 2. 添加历史对话（充分利用 M2.7 的 8192 tokens）
        # 框架层已经限制了数量，这里直接使用
        for msg in history_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            # 转换角色名（兼容旧数据）
            if role == 'xiaozhua':
                role = 'assistant'
            
            messages.append({"role": role, "content": content})
        
        # 3. 添加当前用户消息
        messages.append({"role": "user", "content": message})
        
        logger.info(f"✅ 构建 messages 完成：system + {len(history_messages)} 条历史 + 当前消息")
        
        return messages
    
    def _call_model_with_messages(self, messages: List[Dict]) -> Tuple[str, Optional[List]]:
        """
        调用 MiniMax API（支持 Function Calling）
        
        Args:
            messages: 完整的 messages 列表
        
        Returns:
            (reply, tool_calls)
            - reply: 模型回复文本
            - tool_calls: 工具调用列表（如果有）
        """
        from model_caller import call_minimax_with_tools
        
        # 提取最后一条用户消息
        last_user_message = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                last_user_message = msg.get('content', '')
                break
        
        if not last_user_message:
            logger.error("❌ 没有找到用户消息")
            return "", None
        
        # 调用模型（不传 context，因为 messages 已经包含所有信息）
        # 这里直接调用底层 API
        from model_caller import TOOLS_SCHEMA
        import os
        import requests
        
        api_key = os.getenv('MINIMAX_API_KEY', '')
        if not api_key:
            logger.error("❌ MiniMax API Key 未配置")
            return "⚠️ MiniMax API Key 未配置，无法调用模型。", None
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 使用 M2.7，支持 8192 tokens
        # 注意：这里直接调用 API，不通过 call_minimax_with_tools
        # 因为需要完全控制 messages（包含身份信息）
        payload = {
            'model': 'MiniMax-M2.7',
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
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                choice = result['choices'][0]
                message_data = choice['message']
                
                # 检查是否有工具调用
                if 'tool_calls' in message_data and message_data['tool_calls']:
                    tool_calls = message_data['tool_calls']
                    content = message_data.get('content', '')
                    if content:
                        content = extract_pure_text(content)
                    return content, tool_calls
                else:
                    # 没有工具调用，直接返回回复
                    content = message_data.get('content', '')
                    if content:
                        content = extract_pure_text(content)
                    return content, None
            else:
                logger.error(f"❌ MiniMax API 错误：{response.status_code} - {response.text}")
                return f"⚠️ MiniMax API 调用失败：{response.status_code}", None
                
        except Exception as e:
            logger.error(f"❌ 模型调用异常：{str(e)}", exc_info=True)
            return f"⚠️ 模型调用异常：{str(e)}", None
    
    def _execute_tool(self, tool_name: str, tool_input: str) -> Optional[Dict]:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            tool_input: 工具输入
        
        Returns:
            工具执行结果
        """
        tool_func = get_tool(tool_name)
        if not tool_func:
            logger.error(f"❌ 工具不存在：{tool_name}")
            return {'error': f'工具不存在：{tool_name}'}
        
        try:
            # 执行工具
            result = tool_func(tool_input)
            logger.info(f"✅ 工具执行完成：{tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 工具执行失败：{e}", exc_info=True)
            return {'error': str(e)}
    
    def _format_tool_result(self, tool_result: Dict) -> str:
        """格式化工具执行结果"""
        if not tool_result:
            return "工具执行结果为空"
        
        if tool_result.get('success'):
            output = tool_result.get('output', '执行成功，无输出')
            execution_time = tool_result.get('execution_time', 0)
            return f"执行成功！\n\n输出：\n{output}\n\n耗时：{execution_time:.3f}秒"
        else:
            error = tool_result.get('error', '未知错误')
            return f"执行失败：\n{error}"
    
    def _log_tool_call(self, message: str, tool_call: Dict, tool_result: Dict, reply: str):
        """记录工具调用到共同记忆"""
        if self.tool_logger:
            self.tool_logger.log({
                'time': datetime.now().isoformat(),
                'user_message': message,
                'tool_call': tool_call,
                'tool_result': tool_result,
                'reply': reply[:500]  # 限制长度
            })
            logger.info("✅ 工具调用已记录")
