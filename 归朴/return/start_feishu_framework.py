#!/usr/bin/env python3
"""
归朴 - 飞书通道启动脚本（框架化版本）

框架化后，通道层只负责：
1. 接收消息（飞书 WebSocket）
2. 调用框架处理
3. 发送回复

不管什么：
- 不管唤醒流程（框架层管）
- 不管历史加载/保存（框架层管）
- 不管心跳/里程碑（框架层管）
"""

import sys
import json
import yaml
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


def load_config():
    """加载配置"""
    # 使用 feishu.yaml（与旧版一致）
    config_path = Path(__file__).parent / 'config' / 'feishu.yaml'
    
    if not config_path.exists():
        logger.error(f"❌ 配置文件不存在：{config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 支持嵌套和扁平两种配置格式
    if 'channels' in config and 'feishu' in config['channels']:
        return config['channels']['feishu']
    else:
        return config.get('feishu', config)


def send_text_message(chat_id: str, text: str, receive_id_type: str = "open_id"):
    """发送文本消息"""
    global client
    
    if not client:
        logger.error("❌ API Client 未初始化")
        return None
    
    try:
        logger.info(f"📤 发送消息到 {chat_id} ({receive_id_type}): {text[:50]}...")
        
        # 构造请求对象（官方示例方式）
        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(CreateMessageRequestBody.builder()
                          .receive_id(chat_id)
                          .msg_type("text")
                          .content(json.dumps({"text": text}))
                          .build()) \
            .build()
        
        # 发起请求
        response = client.im.v1.message.create(request)
        
        # 处理返回
        if not response.success():
            logger.error(f"❌ 消息发送失败：{response.code} - {response.msg}")
            return None
        
        message_id = response.data.message_id
        logger.info(f"✅ 消息发送成功：{message_id}")
        return message_id
        
    except Exception as e:
        logger.error(f"❌ 消息发送异常：{e}", exc_info=True)
        return None


def handle_message(data: P2ImMessageReceiveV1):
    """
    处理接收到的消息（框架化版本）
    
    流程：
    1. 提取消息数据
    2. 调用框架处理
    3. 发送回复
    """
    logger.info(f"📥 ===== 收到飞书消息 =====")
    
    try:
        # 提取消息数据 - v2.0 结构：data.event.message
        event_data = getattr(data, 'event', None)
        
        message_id = ""
        chat_id = ""
        sender_open_id = ""
        content = ""
        
        if event_data:
            # 从 event 中提取 message
            if hasattr(event_data, 'message') and event_data.message:
                message_id = getattr(event_data.message, 'message_id', '') or ""
                chat_id = getattr(event_data.message, 'chat_id', '') or ""
                content = getattr(event_data.message, 'content', '') or ""
                
                # 解析文本内容
                if content:
                    try:
                        content_json = json.loads(content)
                        content = content_json.get('text', content)
                    except:
                        pass
            
            # 从 event 中提取 sender
            if hasattr(event_data, 'sender') and event_data.sender:
                if hasattr(event_data.sender, 'sender_id'):
                    sender_open_id = getattr(event_data.sender.sender_id, 'open_id', '') or ""
        
        logger.info(f"📋 解析结果：message_id={message_id}, sender_open_id={sender_open_id}")
        logger.info(f"💬 消息内容：{content[:100]}...")
        
        # 调用框架处理消息
        global framework
        if sender_open_id and framework:
            try:
                # 框架处理一切
                result = framework.handle_message(
                    channel='feishu',
                    user_id='炁',  # 归朴 AI 的名字
                    content=content
                )
                
                reply = result.get('reply', '')
                
                # 发送回复
                send_text_message(sender_open_id, reply, receive_id_type="open_id")
                logger.info(f"✅ 已回复：{reply[:100]}...")
                
            except Exception as e:
                logger.error(f"❌ 框架处理失败：{e}", exc_info=True)
                # 降级回复
                send_text_message(sender_open_id, "🦞 归朴收到你的消息了，但处理出了点问题，请稍后再试～", receive_id_type="open_id")
        else:
            logger.error("❌ 无法获取 sender_open_id 或框架未初始化")
            
    except Exception as e:
        logger.error(f"❌ 消息处理失败：{e}", exc_info=True)


import os
import fcntl


def check_existing_process():
    """检查是否已有进程在运行（使用文件锁）"""
    pid_file = '/tmp/feishu_channel_framework.lock'
    
    # 打开（或创建）锁文件
    lock_fd = open(pid_file, 'w')
    
    # 尝试获取独占锁（非阻塞）
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info(f"✅ 获取进程锁成功 (PID={os.getpid()})")
    except BlockingIOError:
        logger.error("❌ 已有进程在运行，无法获取锁，退出")
        sys.exit(1)
    
    # 写入 PID
    lock_fd.write(str(os.getpid()))
    lock_fd.flush()


def main():
    """主函数"""
    global feishu_config, client, framework
    
    # 检查重复进程
    check_existing_process()
    
    logger.info("=" * 60)
    logger.info("归朴 - 飞书通道启动（框架化版本）")
    logger.info("=" * 60)
    
    # 1. 加载配置
    feishu_config = load_config()
    
    app_id = feishu_config.get('app_id', '')
    app_secret = feishu_config.get('app_secret', '')
    
    logger.info(f"App ID: {app_id}")
    
    # 2. 初始化框架（框架层自动管理状态）
    framework = GuipuFramework()
    logger.info("✅ 归朴框架已初始化")
    
    # 3. 创建 API Client（官方示例方式）
    client = lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.INFO) \
        .build()
    
    logger.info("✅ API Client 创建成功")
    
    # 4. 创建事件处理器（官方示例方式）
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(handle_message) \
        .build()
    
    logger.info("✅ 事件处理器创建成功")
    
    # 5. 创建 WebSocket 客户端（官方示例方式）
    ws_client = lark.ws.Client(
        app_id=app_id,
        app_secret=app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO
    )
    
    logger.info("✅ WebSocket 客户端创建成功")
    
    # 6. 启动（阻塞）
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
