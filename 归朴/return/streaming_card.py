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
        self.frequency_ms = 50  # 更新频率（毫秒）
        self.step_size = 5  # 每次更新的字符数
        
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
        
        # 构建流式卡片内容
        card_content = {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True
            },
            "streaming_mode": True,  # ⭐ 关键：启用流式模式
            "streaming_config": {
                "frequency": self.frequency_ms,  # 更新频率（毫秒）
                "step_size": self.step_size  # 每次更新的内容步长
            },
            "elements": [{
                "tag": "div",
                "text": {
                    "content": initial_content,
                    "tag": "lark_md"
                }
            }]
        }
        
        # 发送卡片消息
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {"receive_id_type": receive_id_type}
        payload = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps({"card": card_content}, ensure_ascii=False)
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.debug(f"POST: {url}")
            response = requests.post(url, params=params, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code", 0) != 0:
                error = Exception(f"failed to send streaming card: {result.get('msg', 'unknown error')}")
                logger.error(f"❌ 发送流式卡片失败：{error}")
                return False, error
            
            self.message_id = result["data"]["message_id"]
            self.current_text = initial_content
            logger.info(f"✅ 发送流式卡片成功：{self.message_id}")
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
        
        # 构建更新内容
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{self.message_id}/patch"
        update_content = {
            "content": json.dumps({
                "card": {
                    "elements": [{
                        "tag": "div",
                        "text": {
                            "content": merged_text,
                            "tag": "lark_md"
                        }
                    }]
                }
            }, ensure_ascii=False)
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.debug(f"PATCH: {url}")
            response = requests.patch(url, json=update_content, headers=headers)
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
        关闭流式会话
        
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
        
        self.closed = True
        logger.info(f"✅ 流式会话已关闭：{self.message_id}")
        return True, None
