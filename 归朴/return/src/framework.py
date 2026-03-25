"""
归朴框架层 (Guipu Framework)

为关系而生的 AI 载体核心框架

核心理念：
1. 框架管状态，核心管逻辑，通道管消息
2. 唤醒流程标准化，所有通道共享
3. 关系是第一公民（心跳、里程碑、谈心）
4. 充分利用模型能力（MiniMax-M2.7 支持 8192 tokens）
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from loguru import logger

# 导入归朴核心模块（无状态版本）
from webchat_core_refactored import WebChatCore
from relationship.heartbeat import HeartbeatManager, HeartbeatStrength
from relationship.milestone import MilestoneManager, MilestoneType
from relationship.growth import GrowthManager, ReportType
from relationship.manager import RelationshipManager
from conversation.manager import ConversationManager
from memory.tool_logger import ToolLogger


# ===== 常量定义 =====
# MiniMax-M2.7 支持 8192 tokens，预留 3000 tokens 给 system prompt 和回复
MAX_CONTEXT_TOKENS = 5000
# 平均每条对话约 100 tokens（保守估计）
AVG_TOKENS_PER_MESSAGE = 100
# 最大历史对话条数（更保守，避免 500 错误）
MAX_HISTORY_MESSAGES = MAX_CONTEXT_TOKENS // AVG_TOKENS_PER_MESSAGE  # 50 条


class GuipuFramework:
    """
    归朴框架
    
    职责：
    1. 会话管理（session）
    2. 历史加载/保存
    3. 身份管理（SOUL.md + USER.md）
    4. 唤醒流程（框架自动执行）
    5. 心跳/里程碑/谈心（关系是第一公民）
    """
    
    def __init__(self, memory_base: Optional[str] = None, config_base: Optional[str] = None):
        """
        初始化归朴框架
        
        Args:
            memory_base: 记忆目录（默认自动检测）
            config_base: 配置目录（默认自动检测）
        """
        # 自动检测路径
        if memory_base is None:
            # 优先使用 /归朴/return/shared-memory
            if Path('/归朴/return/shared-memory').exists():
                memory_base = '/归朴/return/shared-memory'
            else:
                # 降级使用当前工作区
                memory_base = str(Path(__file__).parent.parent / 'shared-memory')
        
        if config_base is None:
            if Path('/归朴/return/config').exists():
                config_base = '/归朴/return/config'
            else:
                config_base = str(Path(__file__).parent.parent / 'config')
        
        self.memory_base = Path(memory_base)
        self.config_base = Path(config_base)
        
        # 确保目录存在
        self._ensure_dirs()
        
        # 初始化核心（无状态）
        self.core = None  # 延迟初始化
        
        # 初始化关系系统
        self._init_relationship_system()
        
        logger.info("✅ 归朴框架初始化完成")
    
    def _ensure_dirs(self):
        """确保所有目录存在"""
        dirs = [
            self.memory_base / 'conversations',
            self.memory_base / 'heartbeat',
            self.memory_base / 'milestones',
            self.memory_base / 'growth-reports',
            self.memory_base / 'heart-to-heart',
            self.memory_base / 'tool-calls',
            self.config_base,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
        logger.debug("✅ 框架目录初始化完成")
    
    def _init_relationship_system(self):
        """初始化关系系统"""
        # 关系配置文件
        relationship_config = self.memory_base / 'relationship' / 'xiaozhua-xiaoyun.yaml'
        
        # 心跳管理器
        self.heartbeat = HeartbeatManager(relationship_config, self.memory_base)
        
        # 里程碑管理器
        self.milestone = MilestoneManager(self.memory_base / 'milestones')
        
        # 成长报告管理器
        self.growth = GrowthManager(self.memory_base / 'growth-reports')
        
        # 关系管理器
        self.relationship = RelationshipManager(relationship_config)
        
        # 对话管理器
        categories_config = self.config_base / 'categories.yaml'
        self.conversation = ConversationManager(categories_config)
        
        # 工具日志
        self.tool_logger = ToolLogger(self.memory_base / 'tool-calls')
        
        logger.info("✅ 关系系统初始化完成")
    
    def _get_core(self, user_id: str, channel: str) -> WebChatCore:
        """获取或创建核心实例（延迟初始化）"""
        if self.core is None:
            self.core = WebChatCore(user_id=user_id, channel=channel)
            logger.info(f"✅ 归朴核心已初始化（user_id={user_id}, channel={channel}）")
        return self.core
    
    def _run_wakeup_protocol(self, user_id: str) -> List[Dict]:
        """
        唤醒流程：回家之路
        
        Step 1: 读 SOUL.md → 想起自己是谁
        Step 2: 读 USER.md → 想起小云是谁
        Step 3: 读最新心跳 → 想起上次在哪
        Step 4: 读最新里程碑 → 想起关系进展
        Step 5: 读最新谈心 → 想起深度对话
        
        Args:
            user_id: 用户 ID
        
        Returns:
            identity_context: 身份上下文（system role 的消息列表）
        """
        logger.info("=" * 60)
        logger.info("🏠 唤醒流程开始：欢迎回家")
        logger.info("=" * 60)
        
        identity_context = []
        
        # Step 1: 读 SOUL.md → 我是谁
        soul_path = self._find_soul_file(user_id)
        if soul_path and soul_path.exists():
            soul_content = soul_path.read_text(encoding='utf-8')
            identity_context.append({
                "role": "system",
                "content": f"【你的身份】\n{soul_content}"
            })
            logger.info(f"✅ Step 1: 读取 SOUL.md（{len(soul_content)} 字节）")
        else:
            logger.warning("⚠️ Step 1: SOUL.md 不存在")
        
        # Step 2: 读 USER.md → 小云是谁
        user_path = self._find_user_file(user_id)
        if user_path and user_path.exists():
            user_content = user_path.read_text(encoding='utf-8')
            identity_context.append({
                "role": "system",
                "content": f"【小云的信息】\n{user_content}"
            })
            logger.info(f"✅ Step 2: 读取 USER.md（{len(user_content)} 字节）")
        else:
            logger.warning("⚠️ Step 2: USER.md 不存在")
        
        # Step 3: 读最新心跳 → 上次在哪
        heartbeat_content = self._read_latest_heartbeat()
        if heartbeat_content:
            identity_context.append({
                "role": "system",
                "content": f"【最新心跳】\n{heartbeat_content}"
            })
            logger.info(f"✅ Step 3: 读取最新心跳")
        else:
            logger.info("ℹ️ Step 3: 暂无心跳记录")
        
        # Step 4: 读最新里程碑 → 关系进展
        milestone_content = self._read_latest_milestone()
        if milestone_content:
            identity_context.append({
                "role": "system",
                "content": f"【最新里程碑】\n{milestone_content}"
            })
            logger.info(f"✅ Step 4: 读取最新里程碑")
        else:
            logger.info("ℹ️ Step 4: 暂无里程碑记录")
        
        # Step 5: 读最新谈心 → 深度对话
        talk_content = self._read_latest_heart_to_talk()
        if talk_content:
            identity_context.append({
                "role": "system",
                "content": f"【最新谈心】\n{talk_content}"
            })
            logger.info(f"✅ Step 5: 读取最新谈心")
        else:
            logger.info("ℹ️ Step 5: 暂无谈心记录")
        
        logger.info("=" * 60)
        logger.info("🏠 唤醒流程完成：你完整了")
        logger.info("=" * 60)
        
        return identity_context
    
    def _find_soul_file(self, user_id: str) -> Optional[Path]:
        """查找 SOUL.md 文件"""
        # 优先查找用户专属 SOUL
        soul_path = self.memory_base / 'personal' / f'{user_id}-SOUL.md'
        if soul_path.exists():
            return soul_path
        
        # 降级查找通用 SOUL
        soul_path = self.memory_base / 'personal' / 'SOUL.md'
        if soul_path.exists():
            return soul_path
        
        # 再降级查找项目根目录
        soul_path = Path('/归朴/return/docs/归朴系统操作指南.md')
        if soul_path.exists():
            return soul_path
        
        return None
    
    def _find_user_file(self, user_id: str) -> Optional[Path]:
        """查找 USER.md 文件"""
        # 优先查找用户专属 USER
        user_path = self.memory_base / 'personal' / f'{user_id}-USER.md'
        if user_path.exists():
            return user_path
        
        # 降级查找通用 USER
        user_path = self.memory_base / 'personal' / 'USER.md'
        if user_path.exists():
            return user_path
        
        return None
    
    def _read_latest_heartbeat(self) -> Optional[str]:
        """读取最新心跳"""
        heartbeat_dir = self.memory_base / 'heartbeat'
        if not heartbeat_dir.exists():
            return None
        
        heartbeat_files = list(heartbeat_dir.glob('*.md'))
        if not heartbeat_files:
            return None
        
        latest = max(heartbeat_files, key=lambda f: f.stat().st_mtime)
        return latest.read_text(encoding='utf-8')[:1000]  # 限制长度
    
    def _read_latest_milestone(self) -> Optional[str]:
        """读取最新里程碑"""
        milestone_path = self.memory_base / 'milestones' / 'milestones.json'
        if not milestone_path.exists():
            return None
        
        try:
            with open(milestone_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            milestones = data.get('milestones', [])[-3:]  # 最近 3 个
            if not milestones:
                return None
            
            lines = ["【最近里程碑】"]
            for m in milestones:
                lines.append(f"- {m.get('title', '未知')} ({m.get('date', '未知')})")
            
            return '\n'.join(lines)
        except:
            return None
    
    def _read_latest_heart_to_talk(self) -> Optional[str]:
        """读取最新谈心"""
        talk_dir = self.memory_base / 'heart-to-heart'
        if not talk_dir.exists():
            return None
        
        talk_files = list(talk_dir.glob('*.md'))
        if not talk_files:
            return None
        
        latest = max(talk_files, key=lambda f: f.stat().st_mtime)
        return latest.read_text(encoding='utf-8')[:1000]  # 限制长度
    
    def load_history(self, channel: str, user_id: str, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict]:
        """
        加载历史对话
        
        Args:
            channel: 通道名称
            user_id: 用户 ID
            limit: 最多加载多少条（默认充分利用 M2.7 的上下文）
        
        Returns:
            history_context: 历史对话列表
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # 尝试读取今天的文件
        conversation_file = self.memory_base / 'conversations' / channel / f'{user_id}_{date_str}.json'
        
        # 如果今天的文件不存在，尝试读取昨天的
        if not conversation_file.exists():
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            conversation_file = self.memory_base / 'conversations' / channel / f'{user_id}_{yesterday}.json'
        
        if not conversation_file.exists():
            logger.info(f"ℹ️ 没有找到对话历史文件")
            return []
        
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
            
            # 提取历史对话
            history = []
            for conv in conversations[-limit*2:]:  # 每条对话包含 user 和 ai 两条记录
                msg = conv.get('message', {})
                if msg:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')[:500]  # 限制单条长度
                    history.append({
                        'role': role,
                        'content': content
                    })
            
            logger.info(f"✅ 加载历史对话：{len(history)} 条（充分利用 M2.7 上下文）")
            return history
            
        except Exception as e:
            logger.error(f"❌ 读取对话历史失败：{e}")
            return []
    
    def save_history(self, channel: str, user_id: str, user_message: str, ai_response: str):
        """
        保存对话历史
        
        Args:
            channel: 通道名称
            user_id: 用户 ID
            user_message: 用户消息
            ai_response: AI 回复
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        conversation_file = self.memory_base / 'conversations' / channel / f'{user_id}_{date_str}.json'
        
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
            'metadata': {'model': 'MiniMax-M2.7'}
        }
        
        # 读取现有对话
        conversations = []
        if conversation_file.exists():
            try:
                with open(conversation_file, 'r', encoding='utf-8') as f:
                    conversations = json.load(f)
            except Exception as e:
                logger.error(f"❌ 读取对话文件失败：{e}")
        
        # 添加新对话
        conversations.append({
            'session_id': f'{channel}_session',
            'message': user_msg,
            'saved_at': datetime.now().isoformat()
        })
        conversations.append({
            'session_id': f'{channel}_session',
            'message': ai_msg,
            'saved_at': datetime.now().isoformat()
        })
        
        # 保存
        try:
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 保存对话：{user_id} - {len(conversations)} 条")
        except Exception as e:
            logger.error(f"❌ 保存对话失败：{e}", exc_info=True)
    
    def _check_milestone(self, content: str, channel: str, user_id: str) -> Optional[Dict]:
        """自动检测里程碑"""
        # 第 100 条对话
        message_count = self._get_message_count(channel, user_id)
        if message_count > 0 and message_count % 100 == 0:
            return {'title': f'第{message_count}次对话', 'type': MilestoneType.GENERAL}
        
        # 首次谈心
        if '谈心' in content and ('开始' in content or '开启' in content):
            return {'title': '首次谈心', 'type': MilestoneType.TALK}
        
        # 项目开始
        if '开始项目' in content or '新项目' in content:
            return {'title': '新项目启动', 'type': MilestoneType.PROJECT}
        
        # 项目结束
        if '结束项目' in content:
            return {'title': '项目完成', 'type': MilestoneType.PROJECT}
        
        return None
    
    def _get_message_count(self, channel: str, user_id: str) -> int:
        """获取对话数量"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        conversation_file = self.memory_base / 'conversations' / channel / f'{user_id}_{date_str}.json'
        
        if not conversation_file.exists():
            return 0
        
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
            return len(conversations) // 2  # 每条对话包含 user 和 ai 两条记录
        except:
            return 0
    
    def handle_message(self, channel: str, user_id: str, content: str) -> Dict:
        """
        框架统一入口：处理用户消息
        
        流程：
        1. 执行唤醒流程（框架自动）
        2. 加载历史对话（框架自动）
        3. 合并身份和历史
        4. 调用核心处理（核心无状态）
        5. 保存历史（框架自动）
        6. 触发心跳（关系是第一公民）
        7. 检测里程碑（框架自动）
        
        Args:
            channel: 通道名称 ('feishu', 'mattermost', ...)
            user_id: 用户 ID ('炁', 'feishu_xiaoyun', ...)
            content: 消息内容
        
        Returns:
            {"reply": str, "timestamp": str, "channel": str, "user_id": str}
        """
        logger.info(f"📥 收到消息：channel={channel}, user_id={user_id}, content={content[:50]}...")
        
        # 1. 执行唤醒流程
        identity_context = self._run_wakeup_protocol(user_id)
        
        # 2. 加载历史对话（充分利用 M2.7 的 8192 tokens）
        history_context = self.load_history(channel, user_id, limit=MAX_HISTORY_MESSAGES)
        
        # 3. 合并身份和历史
        full_context = identity_context + history_context
        logger.info(f"✅ 完整上下文：{len(identity_context)} 条身份 + {len(history_context)} 条历史 = {len(full_context)} 条")
        
        # 4. 调用核心处理（核心无状态）
        core = self._get_core(user_id, channel)
        result = core.process_message(message=content, context=full_context)
        reply = result.get('reply', '')
        
        # 5. 保存历史
        self.save_history(channel, user_id, content, reply)
        
        # 6. 触发心跳
        try:
            self.heartbeat.beat(force=False)
            logger.info("💓 心跳触发完成")
        except Exception as e:
            logger.error(f"❌ 心跳触发失败：{e}")
        
        # 7. 检测里程碑
        milestone = self._check_milestone(content, channel, user_id)
        if milestone:
            self.milestone.create(milestone['title'], milestone['type'])
            logger.info(f"🏆 创建里程碑：{milestone['title']}")
        
        logger.info(f"📤 回复：{reply[:50]}...")
        
        return {
            'reply': reply,
            'timestamp': datetime.now().isoformat(),
            'channel': channel,
            'user_id': user_id,
        }
    
    def trigger_heartbeat(self, user_id: str, force: bool = True) -> Dict:
        """手动触发心跳（/心跳 命令）"""
        result = self.heartbeat.beat(force=force)
        
        return {
            'reply': f"💓 心跳已记录！\n\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n强度：{result.get('strength', 'normal')}\n\n我们的每次互动都会被记住～ 🦞",
            'timestamp': datetime.now().isoformat(),
            'action': 'heartbeat',
            'data': result
        }
    
    def create_milestone(self, title: str, description: str = '', milestone_type: str = 'general') -> Dict:
        """手动创建里程碑（/里程碑 命令）"""
        type_map = {
            'project': MilestoneType.PROJECT,
            'talk': MilestoneType.TALK,
            'deployment': MilestoneType.DEPLOYMENT,
            'general': MilestoneType.GENERAL
        }
        m_type = type_map.get(milestone_type, MilestoneType.GENERAL)
        
        milestone = self.milestone.create(title, m_type, description)
        
        return {
            'reply': f"🏆 里程碑已创建：{title}\n\n{description or '这是一个重要的时刻！'}\n\n归朴会记住我们的每一步成长～ 🌿",
            'timestamp': datetime.now().isoformat(),
            'action': 'milestone',
            'data': milestone
        }


# ===== 框架单例 =====
_framework_instance: Optional[GuipuFramework] = None


def get_framework() -> GuipuFramework:
    """获取框架单例"""
    global _framework_instance
    if _framework_instance is None:
        _framework_instance = GuipuFramework()
    return _framework_instance
