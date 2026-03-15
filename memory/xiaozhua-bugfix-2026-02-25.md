# 小爪聊天服务 - Bug 修复记录

## 问题描述

**日期：** 2026-02-25

**问题：** 群聊中出现 "xiaozhua: xiaozhua: xxx" 的消息前缀重复叠加问题（叠叠乐bug）

## 根因分析

**文件：** `~/xiaozhua_agent/xiaozhua_heartbeat_phase2.py`

**问题位置：** 第 253 行

```python
# 错误代码
messages.append({'role': role, 'content': f"{h.get('from', '')}: {h.get('content', '')}"})
```

**原因：** 历史消息的 `content` 字段已经是完整的消息内容，不需要再加 `from_user:` 前缀。每次拼接都会累积一层，导致叠叠乐。

## 修复方案

```python
# 修复后
messages.append({'role': role, 'content': h.get('content', '')})
```

## 服务信息

- **部署位置：** 192.168.31.204 (本地服务器)
- **运行命令：** `python3 ~/xiaozhua_agent/xiaozhua_heartbeat_phase2.py`
- **进程管理：** supervisor 或 nohup 后台运行

## 服务角色区分

| 角色 | 名字 | 对话模型 |
|------|------|----------|
| **小小爪** | `xiaozhua_heartbeat_phase2.py` | DeepSeek Chat |
| **小爪** | OpenClaw (我) | MiniMax M2.5 |

记住：
- **小小爪** = Python 脚本，部署在服务器，服务飞书群"DeepSeek AI 配置完成！"
- **小爪** = OpenClaw AI 助手 (就是我 🦞)

## 相关文件

- 主程序：`~/xiaozhua_agent/xiaozhua_heartbeat_phase2.py`
- 启动脚本：`~/xiaozhua_agent/daemon.sh`
- 配置记忆：`~/xiaozhua_agent/xiaozhua_memory.json`

## 教训

在构建对话历史时，如果 `content` 已经是完整消息内容，就不要再拼接发送者前缀。否则会导致多层叠加。
