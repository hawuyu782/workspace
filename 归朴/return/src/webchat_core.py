"""
归朴 WebChat 核心集成 - 修复版

直接调用归朴原生核心模块，实现完全融合
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# 添加归朴路径 - 支持两种路径
GUIPU_BASE = Path(__file__).parent.parent  # 自动检测：/home/shangguanyun/.openclaw/workspace/归朴/return
if not GUIPU_BASE.exists():
    GUIPU_BASE = Path('/归朴/return')  # 降级路径
sys.path.insert(0, str(GUIPU_BASE / 'src'))

from relationship.heartbeat import HeartbeatManager, HeartbeatStrength
from relationship.milestone import MilestoneManager, MilestoneType
from relationship.growth import GrowthManager, ReportType
from relationship.manager import RelationshipManager
from conversation.manager import ConversationManager
from loguru import logger

# 导入工具模块
from tools.registry import list_tools, check_tool_access, get_tool
from tools.execute_code import execute_code


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
    """归朴核心（支持多通道）"""
    
    def __init__(self, user_id: str = 'default_user', channel: str = 'webchat'):
        """
        初始化归朴核心
        
        Args:
            user_id: 用户 ID
            channel: 通道名称（'webchat', 'feishu', 'mattermost' 等）
        """
        self.user_id = user_id
        self.channel = channel  # ✅ 支持传入 channel
        self.memory_base = GUIPU_BASE / 'shared-memory'
        self.config_base = GUIPU_BASE / 'config'
        
        # 确保所有目录存在（使用 Path 对象）
        (self.memory_base / 'relationship').mkdir(parents=True, exist_ok=True)
        (self.memory_base / 'heartbeat').mkdir(parents=True, exist_ok=True)
        (self.memory_base / 'milestones').mkdir(parents=True, exist_ok=True)
        (self.memory_base / 'growth-reports').mkdir(parents=True, exist_ok=True)
        (self.memory_base / 'conversations').mkdir(parents=True, exist_ok=True)
        (self.memory_base / 'tool-calls').mkdir(parents=True, exist_ok=True)  # 新增：工具调用日志目录
        
        # 导入工具日志模块
        from memory.tool_logger import ToolLogger
        self.tool_logger = ToolLogger(self.memory_base / 'tool-calls')
        
        # 配置文件路径
        relationship_config = self.memory_base / 'relationship' / 'xiaozhua-xiaoyun.yaml'
        categories_config = self.config_base / 'categories.yaml'
        
        logger.info(f"初始化 WebChat 核心，用户：{user_id}")
        logger.info(f"memory_base 类型：{type(self.memory_base)}, 值：{self.memory_base}")
        
        # HeartbeatManager 需要 Path 对象作为 memory_dir
        logger.info(f"HeartbeatManager 参数：relationship_config={type(relationship_config)}, memory_base={type(self.memory_base)}")
        self.heartbeat = HeartbeatManager(relationship_config, self.memory_base)
        logger.info(f"HeartbeatManager 初始化完成，heartbeat_log_dir 类型：{type(self.heartbeat.heartbeat_log_dir)}")
        
        # RelationshipManager 需要 Path 对象
        self.relationship = RelationshipManager(relationship_config)
        
        # ConversationManager 需要 Path 对象
        self.conversation = ConversationManager(categories_config)
        
        # MilestoneManager 需要 Path 对象
        self.milestone = MilestoneManager(self.memory_base / 'milestones')
        
        # GrowthManager 需要 Path 对象
        self.growth = GrowthManager(self.memory_base / 'growth-reports')
        
        logger.info("WebChat 核心初始化完成")
    
    def process_message(self, message: str, context: List[Dict] = None) -> Dict:
        """
        处理用户消息（使用 MiniMax 原生 Function Calling）
        
        流程：
        1. 触发心跳
        2. 加载历史上下文（如果没有传入）
        3. 第一次调用模型（可能返回工具调用）
        4. 如果需要工具，执行并再次调用
        5. 感知工具调用（记录 + 更新关系）
        6. 记录对话
        
        Args:
            message: 用户消息
            context: 对话上下文（可选，如果不传则自动加载历史）
        
        Returns:
            {"reply": str, "tool_call": Optional[Dict]}
        """
        logger.info(f"处理消息：{message[:50]}...")
        
        # 1. 触发心跳
        try:
            logger.info("触发心跳...")
            self.heartbeat.beat(force=False)
            logger.info("心跳触发完成")
        except Exception as e:
            logger.error(f"心跳触发失败：{e}", exc_info=True)
        
        # 2. 如果没有传入上下文，自动加载历史对话
        if context is None:
            context = self.get_history(limit=300)  # 加载最近 300 条对话（充分利用模型上下文）
            logger.info(f"自动加载历史对话：{len(context)} 条")
        
        # 3. 第一次调用模型（可能返回工具调用）
        from model_caller import call_minimax_with_tools
        reply, tool_call_meta, tool_result_meta = call_minimax_with_tools(
            message=message,
            context=context,  # 传递历史上下文
            tool_result=None,
            channel=self.channel  # ✅ 传入通道名称
        )
        
        tool_result = None
        if tool_call_meta:
            # 模型决定调用工具
            logger.info(f"模型决定调用工具：{tool_call_meta['tool_name']}")
            
            # 执行工具
            tool_result = self._execute_tool(
                tool_call_meta['tool_name'],
                tool_call_meta['tool_args']['code']
            )
            
            # 4. 第二次调用模型（带工具结果）
            reply, _, tool_result_meta = call_minimax_with_tools(
                message=message,
                context=context,
                tool_result=tool_result,
                tool_call=tool_call_meta,
                channel=self.channel  # ✅ 传入通道名称
            )
            
            # 5. 感知工具调用（核心层记录）
            self._log_tool_call(message, tool_call_meta, tool_result, reply)
            self._update_relationship(tool_result)
        
        logger.info(f"模型响应：{reply[:50] if reply else '...' }...")
        
        # 6. 保存对话
        self._save_conversation(message, reply)
        
        # 过滤 reply，确保所有通道收到纯文本
        if reply:
            reply = extract_pure_text(reply)
        
        return {
            'reply': reply,
            'timestamp': datetime.now().isoformat(),
            'user_id': self.user_id,
            'channel': self.channel,  # ✅ 使用实例的 channel 属性
            'tool_used': tool_call_meta['tool_name'] if tool_call_meta else None,
            'tool_result': tool_result
        }
    
    def _execute_tool(self, tool_name: str, tool_input: str) -> Optional[Dict]:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            tool_input: 工具输入（代码或命令）
        
        Returns:
            工具执行结果
        """
        from tools.registry import get_tool
        
        tool_func = get_tool(tool_name)
        if not tool_func:
            logger.error(f"工具不存在：{tool_name}")
            return {'error': f'工具不存在：{tool_name}'}
        
        try:
            # 执行工具
            result = tool_func(tool_input)
            
            logger.info(f"工具执行完成：{tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"工具执行失败：{e}", exc_info=True)
            return {'error': str(e)}
    
    def _extract_code_from_message(self, message: str) -> Optional[str]:
        """
        从消息中提取代码或命令
        
        支持格式：
        ```python
        code here
        ```
        
        ```bash
        command here
        ```
        
        或直接是代码/命令
        """
        import re
        
        # 去除"执行："前缀
        message = re.sub(r'^执行 [:：]\s*', '', message.strip())
        
        # 尝试匹配 ```python 代码块
        match = re.search(r'```(?:python)?\s*(.*?)\s*```', message, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 尝试匹配 ```bash 命令块
        match = re.search(r'```(?:bash|shell|cmd)?\s*(.*?)\s*```', message, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 检查是否包含常见的命令关键词
        command_keywords = ['ipconfig', 'ifconfig', 'ip addr', 'ping', 'curl', 'wget', '查看 IP', '查看 ip', '本机 IP', '本机 ip', 'echo ', 'ls ', 'cd ', 'pwd']
        if any(kw in message.lower() for kw in command_keywords):
            # 直接返回整个消息作为命令
            return message.strip()
        
        # 检查是否包含 Python 代码特征
        python_keywords = ['print', 'def ', 'import ', '=', '+', '-', '*', '/', 'for ', 'if ', 'while ']
        if any(kw in message for kw in python_keywords):
            # 尝试提取代码部分（去除自然语言）
            # 如果消息很短，直接返回
            if len(message) < 100:
                return message.strip()
        
        # 如果没有识别到代码，返回整个消息（让工具自己判断）
        return message.strip() if message.strip() else None
    
    def _save_tool_result(self, tool_name: str, result: Dict):
        """
        保存工具执行结果到记忆
        
        Args:
            tool_name: 工具名称
            result: 执行结果
        """
        import json
        from pathlib import Path
        
        # 保存到工具执行日志
        tools_log_dir = self.memory_base / 'tools'
        tools_log_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_file = tools_log_dir / f"tools_{date_str}.json"
        
        # 读取现有日志
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                pass
        
        # 添加新日志
        logs.append({
            'timestamp': datetime.now().isoformat(),
            'tool_name': tool_name,
            'user_id': self.user_id,
            'result': result
        })
        
        # 保存
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            logger.info(f"工具执行日志已保存：{log_file}")
        except Exception as e:
            logger.error(f"保存工具日志失败：{e}")
    
    def _save_conversation(self, user_message: str, ai_response: str):
        """
        保存对话到 shared-memory
        """
        import json
        from pathlib import Path
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        # ✅ 使用 self.channel 代替硬编码 'webchat'
        conversation_file = self.memory_base / 'conversations' / self.channel / f"{self.user_id}_{date_str}.json"
        
        # 确保目录存在
        conversation_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建对话记录
        user_msg = {
            'id': f"msg_{datetime.now().timestamp()}_user",
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat(),
            'metadata': {}
        }
        
        ai_msg = {
            'id': f"msg_{datetime.now().timestamp()}_ai",
            'role': 'assistant',
            'content': ai_response,
            'timestamp': datetime.now().isoformat(),
            'metadata': {'model': 'MiniMax-M2.5'}
        }
        
        # 读取现有对话
        conversations = []
        if conversation_file.exists():
            try:
                with open(conversation_file, 'r', encoding='utf-8') as f:
                    conversations = json.load(f)
            except Exception as e:
                logger.error(f"读取对话文件失败：{e}")
        
        # 添加新对话
        conversations.append({
            'session_id': 'webchat_session',
            'message': user_msg,
            'saved_at': datetime.now().isoformat()
        })
        conversations.append({
            'session_id': 'webchat_session',
            'message': ai_msg,
            'saved_at': datetime.now().isoformat()
        })
        
        # 保存
        try:
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, ensure_ascii=False, indent=2)
            logger.info(f"保存对话：{self.user_id} - {len(conversations)} 条")
        except Exception as e:
            logger.error(f"保存对话失败：{e}", exc_info=True)
    
    def trigger_heartbeat(self, intensity: str = 'normal') -> Dict:
        """
        手动触发心跳（/心跳 命令）
        """
        # 使用归朴心跳 beat 方法
        result = self.heartbeat.beat(force=True)
        
        return {
            'reply': f"💓 心跳已记录！\n\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n强度：{intensity}\n通道：webchat\n\n我们的每次互动都会被记住～ 🦞",
            'timestamp': datetime.now().isoformat(),
            'action': 'heartbeat',
            'intensity': intensity,
            'data': result
        }
    
    def create_milestone(self, title: str, description: str = '', milestone_type: str = 'general') -> Dict:
        """
        创建里程碑（/里程碑 命令）
        """
        # 映射类型
        type_map = {
            'project': MilestoneType.PROJECT,
            'talk': MilestoneType.TALK,
            'deployment': MilestoneType.DEPLOYMENT,
            'general': MilestoneType.GENERAL
        }
        m_type = type_map.get(milestone_type, MilestoneType.GENERAL)
        
        # 创建里程碑
        milestone_id = self.milestone.create(
            user_id=self.user_id,
            title=title,
            description=description,
            milestone_type=m_type,
            channel='webchat'
        )
        
        return {
            'reply': f"🎯 里程碑已创建！\n\n标题：{title}\n描述：{description or '无'}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n这是我们的第 {milestone_id} 个里程碑！🦞",
            'timestamp': datetime.now().isoformat(),
            'action': 'milestone',
            'milestone_id': milestone_id
        }
    
    def generate_report(self, report_type: str = 'weekly') -> Dict:
        """
        生成成长报告（/报告 命令）
        """
        # 生成报告
        if report_type == 'monthly':
            report = self.growth.generate_monthly_report()
        else:
            report = self.growth.generate_weekly_report()
        
        # 转换为字典
        report_dict = report.to_dict() if hasattr(report, 'to_dict') else {}
        
        # 格式化报告
        reply = f"📊 {report_type.title()} 成长报告\n\n"
        reply += f"周期：{report_dict.get('period', '未知')}\n\n"
        reply += f"💓 心跳次数：{report_dict.get('heartbeat_count', 0)}\n"
        reply += f"💬 对话次数：{report_dict.get('conversation_count', 0)}\n"
        reply += f"🎯 里程碑：{report_dict.get('milestone_count', 0)}\n\n"
        reply += f"💛 信任度：{report_dict.get('trust_level', 0)}\n"
        reply += f"🤝 默契度：{report_dict.get('rapport_level', 0)}\n\n"
        
        insights = report_dict.get('insights', [])
        if insights:
            reply += "💡 成长洞察:\n"
            for insight in insights[:3]:
                reply += f"- {insight}\n"
        
        return {
            'reply': reply,
            'timestamp': datetime.now().isoformat(),
            'action': 'report',
            'report_type': report_type,
            'report_data': report_dict
        }
    
    def get_history(self, limit: int = 300) -> List[Dict]:
        """
        获取对话历史（从 shared-memory 读取）
        
        Args:
            limit: 最多返回多少条对话（默认 300 条，充分利用模型上下文）
        
        Returns:
            对话历史列表，格式：[{"role": "user", "content": "..."}, ...]
        """
        import json
        from pathlib import Path
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        # ✅ 使用 self.channel 代替硬编码 'webchat'
        conversation_file = self.memory_base / 'conversations' / self.channel / f"{self.user_id}_{date_str}.json"
        
        # 如果今天的文件不存在，尝试读取昨天的
        if not conversation_file.exists():
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            # ✅ 使用 self.channel 代替硬编码 'webchat'
            conversation_file = self.memory_base / 'conversations' / self.channel / f"{self.user_id}_{yesterday}.json"
        
        if not conversation_file.exists():
            logger.info(f"没有找到对话历史文件")
            return []
        
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
            
            # 提取最近的对话
            history = []
            for conv in conversations[-limit*2:]:  # 每条对话包含 user 和 ai 两条记录
                msg = conv.get('message', {})
                if msg:
                    role = 'user' if msg.get('role') == 'user' else 'assistant'
                    history.append({
                        'role': role,
                        'content': msg.get('content', '')[:500]  # 限制长度
                    })
            
            logger.info(f"加载历史对话：{len(history)} 条")
            return history
            
        except Exception as e:
            logger.error(f"读取对话历史失败：{e}")
            return []
    
    def _log_tool_call(self, message: str, tool_call: Dict, 
                       tool_result: Dict, reply: str):
        """记录工具调用到共同记忆"""
        self.tool_logger.log({
            'time': datetime.now().isoformat(),
            'user_message': message,
            'tool_call': tool_call,
            'tool_result': tool_result,
            'reply': reply[:500]  # 限制长度
        })
        logger.info("工具调用已记录")
    
    def _update_relationship(self, tool_result: Dict):
        """更新关系档案（工具调用反映信任度）"""
        if tool_result.get('success'):
            self.relationship.update_trust(delta=+1)
            logger.info("工具执行成功，信任度 +1")
        else:
            self.relationship.update_trust(delta=-1)
            logger.warning("工具执行失败，信任度 -1")
