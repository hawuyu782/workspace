#!/usr/bin/env python3
"""
归朴 - 飞书通道启动脚本（框架化版本 + 流式输出）

框架化后，通道层只负责：
1. 接收消息（飞书 WebSocket）
2. 调用框架处理
3. 发送回复（支持流式）
"""

import sys
import json
import yaml
import asyncio
from pathlib import Path
from loguru import logger

import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1, CreateMessageRequest, CreateMessageRequestBody

# 添加归朴路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# 导入框架层
from framework import GuipuFramework

# 配置日志
logger.add(
    "/归朴/return/logs/feishu-framework.log",
    rotation="10 MB",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

# 全局变量
feishu_config = {}
client = None
framework = None  # 框架单例

# 流式开关
ENABLE_STREAMING = True

# 消息去重（24 小时 TTL）
import time
DEDUP_FILE = Path('/tmp/feishu_dedup.json')
DEDUP_TTL_SECONDS = 24 * 60 * 60  # 24 小时
seen_messages = {}

def load_dedup():
    """加载去重记录"""
    global seen_messages
    if DEDUP_FILE.exists():
        try:
            with open(DEDUP_FILE, 'r') as f:
                seen_messages = json.load(f)
            # 清理过期记录
            now = time.time()
            expired = [k for k, v in seen_messages.items() if now - v > DEDUP_TTL_SECONDS]
            for k in expired:
                del seen_messages[k]
            if expired:
                save_dedup()
        except:
            seen_messages = {}

def save_dedup():
    """保存去重记录"""
    try:
        with open(DEDUP_FILE, 'w') as f:
            json.dump(seen_messages, f)
    except:
        pass

def is_duplicate(message_id: str) -> bool:
    """检查消息是否已处理"""
    now = time.time()
    
    if message_id in seen_messages:
        # 检查是否过期
        if now - seen_messages[message_id] > DEDUP_TTL_SECONDS:
            del seen_messages[message_id]
            return False
        return True
    
    # 记录新消息
    seen_messages[message_id] = now
    save_dedup()
    return False

# 启动时加载去重记录
load_dedup()


def load_config():
    """加载配置"""
    config_path = Path(__file__).parent / 'config' / 'feishu.yaml'
    
    if not config_path.exists():
        logger.error(f"❌ 配置文件不存在：{config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config.get('feishu', config)


def send_text_message(chat_id: str, text: str, receive_id_type: str = "open_id"):
    """发送文本消息"""
    global client
    
    if not client:
        logger.error("❌ API Client 未初始化")
        return None
    
    try:
        logger.info(f"📤 发送消息到 {chat_id} ({receive_id_type}): {text[:50]}...")
        
        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(CreateMessageRequestBody.builder()
                          .receive_id(chat_id)
                          .msg_type("text")
                          .content(json.dumps({"text": text}))
                          .build()) \
            .build()
        
        response = client.im.v1.message.create(request)
        
        if not response.success():
            logger.error(f"❌ 消息发送失败：{response.code} - {response.msg}")
            return None
        
        message_id = response.data.message_id
        logger.info(f"✅ 消息发送成功：{message_id}")
        return message_id
        
    except Exception as e:
        logger.error(f"❌ 消息发送异常：{e}", exc_info=True)
        return None


class FeishuStreamingSession:
    """飞书流式会话（模拟打字机效果）"""
    
    def __init__(self, client, app_id: str, app_secret: str, domain: str = 'feishu'):
        self.client = client
        self.app_id = app_id
        self.app_secret = app_secret
        self.domain = domain
        self.message_id = None
        self.chat_id = None
    
    async def start(self, receive_id: str, receive_id_type: str = "open_id", header_title: str = "归朴助手 🦞"):
        """开始流式（发送"正在思考"卡片）"""
        # 发送一个"正在思考"的卡片
        card_content = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue",
                "title": {
                    "tag": "plain_text",
                    "content": header_title
                }
            },
            "elements": [{
                "tag": "markdown",
                "content": "🦞 正在思考中..."
            }]
        }
        
        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(CreateMessageRequestBody.builder()
                          .receive_id(receive_id)
                          .msg_type("interactive")
                          .content(json.dumps(card_content))
                          .build()) \
            .build()
        
        response = self.client.im.v1.message.create(request)
        if response.success():
            self.message_id = response.data.message_id
            self.chat_id = response.data.message.chat_id
            logger.info(f"✅ 流式会话已启动：{self.message_id}")
    
    async def update(self, content: str):
        """更新流式内容（追加文本）"""
        # 简化实现：直接发送文本消息，而不是更新卡片
        # 真正的流式需要飞书服务端支持
        pass
    
    async def close(self, final_content: str):
        """关闭流式（发送最终内容）"""
        if self.message_id:
            # 可以编辑原消息，但简化实现直接发送新消息
            pass


async def process_message_callback_streaming(
    sender_open_id: str,
    content: str
) -> str:
    """
    异步消息处理回调函数（支持流式输出 + 框架化）
    
    Args:
        sender_open_id: 发送者 ID
        content: 消息内容
    
    Returns:
        回复内容
    """
    global framework, client, feishu_config
    
    try:
        logger.info("🚀 使用流式模式处理消息...")
        
        # 检查框架是否初始化
        if framework is None:
            framework = GuipuFramework()
            logger.info("✅ 归朴框架已初始化")
        
        # 创建流式会话
        session = FeishuStreamingSession(
            client=client,
            app_id=feishu_config.get('app_id', ''),
            app_secret=feishu_config.get('app_secret', ''),
            domain='feishu'
        )
        
        # 开始流式（发送"正在思考"卡片）
        await session.start(
            receive_id=sender_open_id,
            receive_id_type="open_id",
            header_title="归朴助手 🦞"
        )
        
        # 处理消息（同步调用，需要在线程池中运行）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: framework.handle_message(
                channel='feishu',
                user_id='炁',
                content=content
            )
        )
        
        reply = result.get('reply', '')
        
        # 空回复保护
        if not reply or not reply.strip():
            reply = "🦞 我在呢！有什么可以帮你的吗？"
        
        # 流式更新（简化实现：直接发送最终内容）
        # 真正的流式需要分块发送，这里简化为一次性发送
        send_text_message(sender_open_id, reply, receive_id_type="open_id")
        
        # 关闭流式
        await session.close(reply)
        
        logger.info(f"✅ 流式回复完成：{reply[:50]}...")
        return reply
        
    except Exception as e:
        logger.error(f"❌ 流式消息处理失败：{e}", exc_info=True)
        
        # 降级到普通文本回复
        reply = f"🦞 归朴收到：{content}"
        send_text_message(sender_open_id, reply, receive_id_type="open_id")
        return reply


def handle_message(data: P2ImMessageReceiveV1):
    """
    处理接收到的消息（框架化版本 + 流式支持 + 去重）
    """
    logger.info(f"📥 ===== 收到飞书消息 =====")
    
    try:
        event_data = getattr(data, 'event', None)
        
        message_id = ""
        chat_id = ""
        sender_open_id = ""
        content = ""
        
        if event_data:
            if hasattr(event_data, 'message') and event_data.message:
                message_id = getattr(event_data.message, 'message_id', '') or ""
                chat_id = getattr(event_data.message, 'chat_id', '') or ""
                content = getattr(event_data.message, 'content', '') or ""
                
                if content:
                    try:
                        content_json = json.loads(content)
                        content = content_json.get('text', content)
                    except:
                        pass
            
            if hasattr(event_data, 'sender') and event_data.sender:
                if hasattr(event_data.sender, 'sender_id'):
                    sender_open_id = getattr(event_data.sender.sender_id, 'open_id', '') or ""
        
        logger.info(f"📋 解析结果：message_id={message_id}, sender_open_id={sender_open_id}")
        logger.info(f"💬 消息内容：{content[:100]}...")
        
        # 去重检查
        if message_id and is_duplicate(message_id):
            logger.info(f"⏭️ 跳过重复消息：{message_id}")
            return
        
        # 调用框架处理消息（普通模式 - 稳定版本）
        global framework
        if sender_open_id and framework:
            try:
                # 使用普通模式（异步兼容）
                result = framework.handle_message(
                    channel='feishu',
                    user_id='炁',
                    content=content
                )
                reply = result.get('reply', '')
                
                # 发送回复
                send_text_message(sender_open_id, reply, receive_id_type="open_id")
                logger.info(f"✅ 已回复：{reply[:100]}...")
                
            except Exception as e:
                logger.error(f"❌ 框架处理失败：{e}", exc_info=True)
                send_text_message(sender_open_id, "🦞 归朴收到你的消息了，但处理出了点问题，请稍后再试～", receive_id_type="open_id")
        else:
            logger.error("❌ 无法获取 sender_open_id 或框架未初始化")
            
    except Exception as e:
        logger.error(f"❌ 消息处理失败：{e}", exc_info=True)


# 事件处理器：处理机器人进入聊天
def handle_bot_chat_entered(data):
    """处理机器人进入聊天事件"""
    logger.info("ℹ️ 机器人进入聊天事件（忽略）")


# 事件处理器：处理消息已读
def handle_message_read(data):
    """处理消息已读事件"""
    logger.info("ℹ️ 消息已读事件（忽略）")


import os
import fcntl


def check_existing_process():
    """检查是否已有进程在运行（使用文件锁）"""
    pid_file = '/tmp/feishu_channel_framework.lock'
    
    lock_fd = open(pid_file, 'w')
    
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info(f"✅ 获取进程锁成功 (PID={os.getpid()})")
    except BlockingIOError:
        logger.error("❌ 已有进程在运行，无法获取锁，退出")
        sys.exit(1)
    
    lock_fd.write(str(os.getpid()))
    lock_fd.flush()


def main():
    """主函数"""
    global feishu_config, client, framework
    
    check_existing_process()
    
    logger.info("=" * 60)
    logger.info("归朴 - 飞书通道启动（框架化版本 + 流式）")
    logger.info("=" * 60)
    
    # 1. 加载配置
    feishu_config = load_config()
    
    app_id = feishu_config.get('app_id', '')
    app_secret = feishu_config.get('app_secret', '')
    
    logger.info(f"App ID: {app_id}")
    
    # 2. 初始化框架
    framework = GuipuFramework()
    logger.info("✅ 归朴框架已初始化")
    
    # 3. 创建 API Client
    client = lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.INFO) \
        .build()
    
    logger.info("✅ API Client 创建成功")
    
    # 4. 创建事件处理器（只注册消息接收事件）
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(handle_message) \
        .build()
    
    logger.info("✅ 事件处理器创建成功（已注册多个事件）")
    
    # 5. 创建 WebSocket 客户端
    ws_client = lark.ws.Client(
        app_id=app_id,
        app_secret=app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO
    )
    
    logger.info("✅ WebSocket 客户端创建成功")
    
    # 6. 启动
    logger.info("🚀 启动飞书 WebSocket 连接...")
    logger.info("✅ 归朴飞书通道运行中...（按 Ctrl+C 停止）")
    logger.info("=" * 60)
    
    try:
        ws_client.start()
    except KeyboardInterrupt:
        logger.info("👋 收到停止信号...")
        logger.info("✅ 归朴飞书通道已停止")


if __name__ == "__main__":
    main()
