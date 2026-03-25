#!/usr/bin/env python3
"""
归朴 - 飞书流式卡片管理器（官方版本）

参考飞书官方文档实现：
- https://open.feishu.cn/document/ukTMukTMukTM/uYjNwUjLxYDM14SM2ATN
"""

import json
import time
import requests
from typing import Optional, Tuple
from loguru import logger


class FeishuStreamingSession:
    """
    飞书流式卡片会话（官方实现）
    
    使用飞书官方的流式卡片 API：
    1. 发送卡片时设置 streaming_mode: True
    2. 使用 PATCH API 更新卡片内容
    """
    
    def __init__(
        self, 
        client: Optional[any] = None,
        app_id: str = "", 
        app_secret: str = "",
        domain: str = "feishu"
    ):
        """
        初始化流式会话
        
        Args:
            client: Lark API Client（可选，兼容旧版）
            app_id: 飞书应用 App ID
            app_secret: 飞书应用 App Secret
            domain: API 域名（feishu 或 lark）
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.domain = domain
        self.access_token: Optional[str] = None
        self.message_id: Optional[str] = None
        self.current_text = ""
        self.closed = False
        
        # 流式配置
        self.frequency_ms = 1000  # 更新频率（毫秒）- 1 秒
        self.step_size = 10  # 每次更新的字符数 - 10 个字符
        
        logger.info(f"飞书流式会话初始化完成：{self.app_id}")
    
    def _get_access_token(self) -> Tuple[str, Optional[Exception]]:
        """获取 tenant_access_token"""
        if self.access_token:
            return self.access_token, None
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.debug(f"POST: {url}")
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code", 0) != 0:
                error = Exception(f"failed to get tenant_access_token: {result.get('msg', 'unknown error')}")
                logger.error(f"❌ 获取 access_token 失败：{error}")
                return "", error
            
            self.access_token = result["tenant_access_token"]
            logger.debug(f"✅ 获取 access_token 成功")
            return self.access_token, None
            
        except Exception as e:
            logger.error(f"❌ 获取 access_token 异常：{e}")
            return "", e
    
    def start(
        self,
        receive_id: str,
        receive_id_type: str = "open_id",
        header_title: Optional[str] = None,
        initial_content: str = "🦞 正在思考中..."
    ) -> Tuple[bool, Optional[Exception]]:
        """
        开始流式会话（发送初始卡片）
        
        Args:
            receive_id: 接收者 ID
            receive_id_type: ID 类型（open_id/union_id/user_id/email/chat_id）
            header_title: 卡片标题（可选）
            initial_content: 初始卡片内容
        
        Returns:
            Tuple[bool, Optional[Exception]]: (success, error)
        """
        if self.message_id:
            logger.warning("流式会话已启动，跳过")
            return True, None
        
        logger.info("开始创建流式卡片...")
        
        # 获取 access_token
        access_token, err = self._get_access_token()
        if err:
            return False, err
        
        # 构建流式卡片内容（JSON 2.0 格式）
        card_content = {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True,
                "streaming_mode": True,  # ⭐ 关键：启用流式模式
                "streaming_config": {
                    "print_frequency_ms": {"default": self.frequency_ms},  # 更新频率（毫秒）
                    "print_step": {"default": self.step_size}  # 每次更新的内容步长
                }
            },
            "body": {
                "elements": [{
                    "tag": "markdown",  # ⭐ 使用 markdown 标签，支持流式更新
                    "content": initial_content,
                    "element_id": "markdown_1"  # ⭐ 必须设置 element_id，用于后续更新
                }]
            }
        }
        
        # 步骤 1：先调用 CardKit API 创建卡片实体
        create_card_url = "https://open.feishu.cn/open-apis/cardkit/v1/cards"
        create_card_payload = {
            "type": "card_json",
            "data": json.dumps(card_content, ensure_ascii=False)
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.debug(f"POST: {create_card_url}")
            logger.debug(f"Request body: {json.dumps(create_card_payload, ensure_ascii=False)[:300]}...")
            response = requests.post(create_card_url, json=create_card_payload, headers=headers)
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response body: {response.text[:500]}")
            response.raise_for_status()
            result = response.json()
            
            if result.get("code", 0) != 0:
                error = Exception(f"failed to create card: {result.get('msg', 'unknown error')}")
                logger.error(f"❌ 创建卡片实体失败：{error}")
                return False, error
            
            card_id = result["data"]["card_id"]
            logger.info(f"✅ 创建卡片实体成功：{card_id}")
            
            # 步骤 2：发送消息（带卡片实体 ID）
            send_message_url = "https://open.feishu.cn/open-apis/im/v1/messages"
            params = {"receive_id_type": receive_id_type}
            send_message_payload = {
                "receive_id": receive_id,
                "msg_type": "interactive",
                "content": json.dumps({
                    "type": "card",
                    "data": {
                        "card_id": card_id
                    }
                }, ensure_ascii=False)
            }
            
            logger.debug(f"POST: {send_message_url}")
            response = requests.post(send_message_url, params=params, json=send_message_payload, headers=headers)
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response body: {response.text[:500]}")
            response.raise_for_status()
            result = response.json()
            
            if result.get("code", 0) != 0:
                error = Exception(f"failed to send message: {result.get('msg', 'unknown error')}")
                logger.error(f"❌ 发送消息失败：{error}")
                return False, error
            
            self.card_id = card_id  # 保存卡片实体 ID
            self.message_id = result["data"]["message_id"]  # ⭐ 保存消息 ID，用于后续更新
            self.current_text = initial_content
            logger.info(f"✅ 发送流式卡片成功：卡片 ID={self.card_id}, 消息 ID={self.message_id}")
            return True, None
            
        except Exception as e:
            logger.error(f"❌ 发送流式卡片异常：{e}")
            return False, e
    
    def update(self, text: str) -> Tuple[bool, Optional[Exception]]:
        """
        流式更新卡片内容
        
        Args:
            text: 新的文本内容（全量文本，不是增量）
        
        Returns:
            Tuple[bool, Optional[Exception]]: (success, error)
        """
        if not self.message_id or self.closed:
            return False, Exception("流式会话未启动或已关闭")
        
        # 合并文本
        merged_text = self.current_text + text
        if not merged_text or merged_text == self.current_text:
            return True, None
        
        # 获取 access_token
        access_token, err = self._get_access_token()
        if err:
            return False, err
        
        # 构建完整的卡片内容
        card_content = {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True
            },
            "streaming_mode": True,
            "streaming_config": {
                "frequency": self.frequency_ms,
                "step_size": self.step_size
            },
            "elements": [{
                "tag": "div",
                "text": {
                    "content": merged_text,
                    "tag": "lark_md"
                }
            }]
        }
        
        # 使用飞书官方 CardKit API 流式更新文本
        # 文档：https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/cardkit-v1/card-element/content
        url = f"https://open.feishu.cn/open-apis/cardkit/v1/cards/{self.card_id}/elements/content"
        
        # 飞书 CardKit API 要求：传入全量文本内容，平台自动计算增量
        update_content = {
            "element_id": "markdown_1",  # 文本组件的唯一标识
            "content": merged_text  # 全量文本内容
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.debug(f"POST: {url}")
            logger.debug(f"Request body: {json.dumps(update_content, ensure_ascii=False)[:300]}...")
            response = requests.post(url, json=update_content, headers=headers)  # ⭐ 使用 POST 方法
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response body: {response.text[:500]}")
            response.raise_for_status()
            result = response.json()
            
            if result.get("code", 0) != 0:
                error = Exception(f"failed to update streaming card: {result.get('msg', 'unknown error')}")
                logger.error(f"❌ 更新流式卡片失败：{error}")
                return False, error
            
            self.current_text = merged_text
            logger.debug(f"✅ 更新流式卡片成功：{len(self.current_text)} 字符")
            return True, None
            
        except Exception as e:
            logger.error(f"❌ 更新流式卡片异常：{e}")
            return False, e
    
    def close(self, final_text: str = "") -> Tuple[bool, Optional[Exception]]:
        """
        关闭流式会话（调用 CardKit API 关闭流式模式）
        
        Args:
            final_text: 最终文本内容
        
        Returns:
            Tuple[bool, Optional[Exception]]: (success, error)
        """
        if not self.message_id:
            return False, Exception("流式会话未启动")
        
        if final_text:
            # 最后一次更新
            success, err = self.update(final_text)
            if not success:
                return False, err
        
        # 调用 CardKit API 关闭流式模式
        url = f"https://open.feishu.cn/open-apis/cardkit/v1/cards/{self.message_id}/settings"
        settings_content = {
            "config": {
                "streaming_mode": False  # 关闭流式模式
            }
        }
        
        # 获取 access_token
        access_token, err = self._get_access_token()
        if err:
            return False, err
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.debug(f"POST: {url}")
            response = requests.post(url, json=settings_content, headers=headers)
            logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()
            
            self.closed = True
            logger.info(f"✅ 流式会话已关闭：{self.message_id}")
            return True, None
        except Exception as e:
            logger.error(f"❌ 关闭流式会话异常：{e}")
            return False, e
