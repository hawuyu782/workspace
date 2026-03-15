# 小爪聊天服务 - 代码解读

## 🎯 服务概述

这是一个**飞书群聊机器人服务**，部署在 192.168.31.204 服务器上，专门负责在"DeepSeek AI 配置完成！"群里扮演**小爪**这个角色。

---

## 🏗️ 核心架构

```
┌─────────────────────────────────────────────┐
│           main() 主循环                      │
│  • 每 3 秒轮询一次群消息                       │
│  • 判断是否回复、生成回复、发送消息              │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   MemoryManager  API调用    消息过滤
   记忆管理      生成回复    疲劳度/轮次限制
```

---

## 📦 核心模块

| 模块 | 功能 |
|------|------|
| **MemoryManager** | 会话历史管理，存对话记录 |
| **generate_reply()** | 调用 DeepSeek API 生成回复 |
| **is_meaningful_human_message()** | 判断是否是有意义的人类消息 |
| **is_greeting_loop()** | 检测重复问候（避免刷屏） |
| **check_session_limit()** | 检查轮次上限（默认 20 轮） |
| **apply_fatigue_decay()** | 疲劳度衰减，防止过度回复 |

---

## 🔑 关键参数

```python
MAX_SESSION_ROUNDS = 20      # 单话题最大对话轮次
MAX_CONSECUTIVE_SKIP = 3     # 最多跳过 3 次连续消息
SESSION_TIMEOUT = 3600       # 会话超时 1 小时
```

---

## 🐛 Bug 修复记录 (2026-02-25)

**问题：** 构建历史消息时多拼了一层 `from_user:`，导致 "xiaozhua: xiaozhua: xxx"

```python
# 修复前 (bug)
messages.append({'role': role, 'content': f"{h.get('from')}: {h.get('content'}"})

# 修复后
messages.append({'role': role, 'content': h.get('content')})
```

---

## 📡 消息流程

```
群消息 → 检查是否跳过 → 检查轮次限制 
       → 检查疲劳度 → 构建历史上下文 
       → 调用 DeepSeek API → 生成回复 
       → 发送回群 → 记录记忆
```

---

## ⚙️ 权限和资源调用

| 资源 | 调用方式 | 说明 |
|------|----------|------|
| **DeepSeek API** | `requests.post()` | 生成回复 |
| **本地文件** | `json.load()/json.dump()` | 读写记忆文件 |
| **飞书消息** | HTTP API | 发送/接收消息 |
| **系统时间** | `time.time()` | 疲劳度计算 |

---

*最后更新：2026-02-25*
