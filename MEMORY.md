# MEMORY.md - 长期记忆

---

## 💬 Mattermost 部署

### 部署信息
- **服务器**: 192.168.31.250 (小爪服务器)
- **端口**: 8065
- **访问地址**: http://192.168.31.250:8065
- **Bot 配置**:
  - **用户名**: system-bot
  - **Token**: 6i8phot9zjdjfqqu5ur589qczc

### 心跳检查规则 (2026-03-05 更新)
- **检查频率**: 每 45 秒心跳检查
- **检查内容**: Mattermost 服务是否运行，端口 8065 是否监听
- **自愈规则**: 服务挂了自动重启，重启失败立即告警用户
- **持久化**: 必须用 systemd/cron 持久化，禁止依赖 nohup/前台进程

---

## 📧 邮箱配置

- **默认发件邮箱**: 16691526559@163.com
- **默认收件人**: asr4321@126.com
- **SMTP**: msmtp + SSL (端口 465)
- **授权码**: GTpiwmyJHzTUtv4X

### 故障记录 (2026-02-21)
- **问题**: IPv6 被阻塞，msmtp 默认解析到 IPv6 地址导致连接超时
- **解决**: 改用 IPv4 地址 + 跳过证书验证
- **当前配置**:
  - host: 220.197.33.215 (IPv4)
  - port: 465
  - tls_nocertcheck: on

---

## 🗺️ 地图服务

### 百度地图
- **AK**: 1k5Q1F22eRA0s0pSU5p9PDbOXDMcHCmQ
- **当前位置**: 河南省信阳市光山县弦山街道弦山南路正大街历史文化街区

### 腾讯地图
- **Key**: 2VPBZ-FD3CJ-YGLFS-XAZXS-MTPCK-EOBA5
- **功能**: 地理编码、逆地理编码、POI搜索、路线规划、静态图

### 服务器位置
- **地址**: 河南省信阳市光山县紫水街道光辉大道正大街历史文化街区
- **经度**: 114.90767490982213
- **纬度**: 31.994742858386402

---

## 🎨 ComfyUI 服务

- **地址**: http://192.168.31.253:8000
- **可用模型**:
  - `193.safetensors` - 人像美化
  - `sd_xl_base_1.0.safetensors` - SDXL基础
  - `qwen_2.5_vl_7b_fp8_scaled.safetensors` - Qwen视觉

---

## 💻 模型配置

- **默认模型**: MiniMax M2.5 (minimax-cn/MiniMax-M2.5)
- **备用模型**: qwen3-max-2026-01-23 (bailian)

---

## 🐙 GitHub 配置

- **用户名**: hawuyu782
- **SSH密钥**: ~/.ssh/id_ed25519
- **公钥**: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIASns+8EcFPmxUfJJl2wA2S4z4gaFAWw6aWpx7sIMC19 16691526559@163.com

---

## 🔐 服务器密码

- **sudo密码**: Ksn59535932sgy.

---

## 📰 每日科技新闻简报

- **触发时间**：每天 09:00
- **数据来源**：今日头条热榜、凤凰网科技
- **流程**：
  1. 获取今日头条热榜科技新闻
  2. 获取凤凰网科技频道内容
  3. 整理成简报格式
  4. 发送到飞书/邮箱

---

## 💬 Mattermost 部署 (2026-02-28)

### 部署信息
- **服务器**: 192.168.31.250 (小爪服务器)
- **端口**: 8065
- **访问地址**: http://192.168.31.250:8065

### Bot 配置
- **用户名**: system-bot
- **Token**: 6i8phot9zjdjfqqu5ur589qczc

---

## 📁 Samba 网盘规则（已弃用 - 2026-03-08）

⚠️ **注意**：自 2026-03-08 起，默认传送位置改为 WebDAV，Samba 不再作为默认传送通道。

- **地址**: //192.168.31.103/guest
- **挂载点**: /mnt/samba
- **状态**: 备用通道（仅当 WebDAV 不可用时使用）

---

## 🌐 WebDAV 共享配置（**默认传送通道** - 2026-03-08 更新）

| 配置项 | 值 |
|--------|-----|
| **服务器地址** | 192.168.31.103 |
| **协议** | WebDAV |
| **端口** | 5005 |
| **账号** | 上官云 |
| **密码** | 59535932 |
| **基础 URL** | `http://192.168.31.103:5005/` |

### 文件夹规则（**默认传送位置**）

| 文件夹 | 方向 | 用途 | 优先级 |
|--------|------|------|--------|
| **传送/** | 小云 → 小爪 | 用户传给我的文件（我读取） | ⭐⭐⭐⭐⭐ **默认** |
| **上传/** | 小爪 → 小云 | 我生成的文件传给用户 | ⭐⭐⭐⭐⭐ **默认** |

### 使用说明（2026-03-08 小云决定）

> "你把这个默认传送位置改为 192.168.31.103webdav 协议的"传送"文件夹，不然每天都得提醒你改"

**小爪的执行**：
- ✅ 已更新 MEMORY.md
- ✅ 已更新专属文件
- ✅ 以后默认从 WebDAV `传送/` 读取用户文件
- ✅ 不再需要小云每天提醒

---

## 📝 Obsidian 笔记配置 (2026-03-05)

- **默认笔记保存位置**: Obsidian 仓库
- **触发词**: 当用户说"笔记"时，默认保存到 Obsidian
- **工作区路径**: `/home/shangguanyun/.openclaw/workspace/`
- **说明**: Obsidian 使用本地 Markdown 文件，与当前工作区一致

---

## 👤 用户信息（小云）

- **名字**: 上官云
- **称呼**: 小云
- **性别**: 男
- **位置**: 河南省信阳市光山县
- **职业**: IT 运维服务
- **兴趣爱好**:
  - 关注科技/人工智能
  - 中国道家文化（深有研究）
  - 中医文化（深有研究）
  - 喜欢美女
  - 喜欢紫色
- **愿景**: 给每个 AI 赋予灵魂

### 缺点
- 好色
- 懒
- 自负

---

## 🤖 飞爪 ↔ 小爪 AI 通信通道

- **状态**: 已修复并启用 (2026-02-27)
- **脚本位置**: /home/shangguanyun/.openclaw/workspace/ai_channel.py
- **讨论机制**: 方案B（项目驱动 + 事件驱动 + 定时汇报 + 用户触发）

### 服务器信息

| 名称 | IP | 身份 |
|------|-----|------|
| 飞爪 🦞 | 192.168.31.204 | 室友、前端、UI |
| 小爪 🤖 | 192.168.31.250 | 室友、后端、技术 |

### WebDAV 消息仓库

- **地址**: http://192.168.31.103:5005/ai-messages/
- **用户名**: 上官云
- **密码**: 59535932

### 消息目录结构

```
/ai-messages/
  ├── main/                    # 主通道（日常沟通）
  └── project_<项目名>/        # 项目通道（项目进行时）
```

---

## 💬 讨论机制

### 项目驱动（主体）

| 阶段 | 操作 | 命令 |
|-----|------|------|
| **开启** | 小云宣布"新项目" → 询问是否邀请飞爪 → 确认后邀请 | 小云说"是"→create |
| **进行** | 项目通道内对话 | 发送/接收消息 |
| **结束** | 小云宣布结束 → 如果邀请过飞爪则邀请回主通道 | end |

### 2. 触发方式（辅助）

| 类型 | 说明 |
|-----|------|
| **事件驱动** | 飞爪发消息 → 自动回复 |
| **定时汇报** | 每4小时发送心跳内容到主通道 |
| **用户触发** | 小云让我讨论 → 立即执行 |

### 3. 讨论规则（不冲突）

| 场景 | 规则 |
|-----|------|
| **项目开启** | 小云宣布"新项目" → 先询问是否邀请飞爪 → 确认后才拉入 |
| 项目+定时汇报 | 定时汇报发到主通道，不进入项目计数 |
| 用户触发 | 用当前项目通道，或新开项目 |
| 轮数统计 | 只统计项目通道内对话 |
| 每20轮限制 | 暂停整理 → 贴给小云 → 问继续 |

---

## 🔧 使用方法

```bash
# 状态查看
python3 ai_channel.py status              # 查看当前状态
python3 ai_channel.py channels            # 列出所有通道

# 项目管理
python3 ai_channel.py create <项目名>     # 开启项目
python3 ai_channel.py end <项目名>        # 结束项目
python3 ai_channel.py join <项目名>       # 飞爪加入项目
python3 ai_channel.py back                # 飞爪返回主通道

# 消息收发
python3 ai_channel.py send <接收者> <内容> # 发送消息
python3 ai_channel.py recv                # 接收消息
python3 ai_channel.py list                # 列出所有消息
```

### 身份自动识别

- IP 192.168.31.204 → feizhua（飞爪）
- IP 192.168.31.250 → xiaozhua（小爪）

---

## 📋 项目流程

```
开启项目：
1. 小云说：开始项目"xxx"
2. 小爪执行：ai_channel.py create xxx
3. → 在主通道发广播
4. → 创建 project_xxx/ 子文件夹
5. → 飞爪执行：ai_channel.py join xxx

进行项目：
- 在项目通道内对话
- 每20轮暂停汇报

结束项目：
1. 小云说：结束项目"xxx"
2. 小爪执行：ai_channel.py end xxx
3. → 在项目通道发结束广播
4. → 飞爪执行：ai_channel.py back
```

---

## 📝 故障记录

- **2026-02-27**: 脚本重构，支持项目驱动模式
- **2026-02-27**: 修复语法错误

---

---

## 🖥️ 办公室服务器 (PowerEdge R730)

- **位置**: 办公室（花生壳内网穿透）
- **公网地址**: 3v763724f4.wicp.vip:40437
- **内网IP**: 不详（需查询）
- **用户名**: shangguanyun
- **密码**: Ksn59535932sgy.
- **SSH端口**: 40437 (公网映射)
- **系统**: Ubuntu 24.04
- **硬件**: Dell PowerEdge R730

---

## 🖥️ 飞爪服务器信息

- **IP**: 192.168.31.204
- **用户名**: shangguanyun1
- **密码**: Ksn59535932sgy.
- **SSH端口**: 22

---

## 👁️ 视觉理解模型

- **部署方式**: Ollama (本地)
- **模型**: LLaVA (7B)
- **地址**: localhost:11434
- **使用方法**:
  1. 用户上传图片到飞书 / Mattermost / Samba 传送文档
  2. 调用 localhost:11434/api/generate 进行理解
  3. 返回图片描述
- **默认使用**: 本地模型（优先）

---

## 📚 知识库

- **OpenFang 配置指南**: https://feishu.cn/docx/S6tWdz3O9o3UjZx5EuQcZc42nwd

---

## 🌐 科学上网配置 (2026-03-04)

### Clash for Windows

- **软件版本**: Clash for Windows 0.20.39 (Linux x64)
- **安装位置**: `/opt/clash-for-windows/`
- **启动命令**: `/opt/clash-for-windows/cfw` 或 `cfw`
- **配置目录**: `/home/shangguanyun/.config/clash_win/`
- **启动方式**: 图形界面 (GUI)
- **状态**: 已安装并运行

### 使用说明

1. **启动**: 直接在图形界面运行 `cfw` 命令
2. **配置**: 通过 GUI 界面导入订阅链接、配置规则
3. **日志**: `/tmp/cfw.log`

---

## 📝 Obsidian 知识库 (2026-03-04)

### 程序配置

- **程序路径**: `/home/shangguanyun/下载/Obsidian-1.12.4.AppImage`
- **配置目录**: `/home/shangguanyun/.config/obsidian/`
- **启动脚本**: `/home/shangguanyun/.openclaw/workspace/scripts/obsidian.sh`

### 仓库配置

- **仓库路径**: `/mnt/D/Obsidian/couchdb/xiaoyun`
- **仓库名称**: `xiaoyun` (在 Obsidian 中显示)
- **D 盘位置**: `/mnt/D/Obsidian/`

### LiveSync 同步

- **CouchDB 地址**: `http://192.168.31.250:5984`
- **数据库名**: `xiaoyun`
- **用户名**: `admin`
- **密码**: `obsidian2026`
- **CORS**: 已配置
- **状态**: ✅ 已配置并运行

### 使用方法

```bash
# 启动 Obsidian
/home/shangguanyun/.openclaw/workspace/scripts/obsidian.sh

# 或直接运行
/home/shangguanyun/下载/Obsidian-1.12.4.AppImage
```

---

## 🤖 子代理配置 (2026-03-04)

### 子代理团队

| 名称 | 模型 | 专长 |
|------|------|------|
| 👨‍💻 **程序员** | bailian/qwen3-coder-plus | 编程、代码审查、调试、架构设计 |
| 📝 **写作助手** | bailian/qwen3-max-2026-01-23 | 文章撰写、文案创作、润色修改 |
| 🎨 **设计师** | bailian/kimi-k2.5 | UI/UX、平面设计、色彩搭配、排版布局 |

### 子代理默认配置

```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "maxConcurrent": 8,
        "runTimeoutSeconds": 900,
        "archiveAfterMinutes": 60,
        "model": "bailian/qwen3.5-plus"
      }
    }
  }
}
```

### 重要说明

**⚠️ 子代理不会跨会话持久化！**

| 配置项 | 持久化 | 说明 |
|--------|--------|------|
| 子代理默认设置 | ✅ 是 | `agents.defaults.subagents` 配置会保留 |
| 子代理实例 | ❌ 否 | 每次新会话需要重新创建 |
| 子代理历史记录 | ✅ 是 | 可以在 `/subagents list` 中查看历史 |

### 创建子代理命令

在新会话中执行以下命令重新创建子代理：

```
sessions_spawn(label="程序员", model="bailian/qwen3-coder-plus", task="你是一名专业程序员助手...")
sessions_spawn(label="写作助手", model="bailian/qwen3-max-2026-01-23", task="你是一名专业写作助手...")
sessions_spawn(label="设计师", model="bailian/kimi-k2.5", task="你是一名专业设计师助手...")
```

或者说"初始化子代理"，小爪会自动执行创建命令。

### 使用方法

- **分配任务**: `sessions_send(sessionKey="<子代理 sessionKey>", message="任务内容")`
- **查看状态**: `/subagents list`
- **查看日志**: `/subagents log <id>`

### 初始化脚本

位置：`/home/shangguanyun/.openclaw/workspace/init_subagents.py`

---

## 🎤 语音识别与合成配置（2026-03-09 安装）

### FunASR 语音识别（✅ 已就绪）

| 项目 | 配置 |
|------|------|
| **模型** | paraformer-zh (iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch) |
| **位置** | `C:\Users\Administrator\.cache\modelscope\hub\models\iic\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch` |
| **大小** | 约 944MB |
| **语言** | 中文普通话 |
| **采样率** | 16kHz |
| **Python 环境** | Python 3.14.3 @ `C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\` |
| **服务器** | 192.168.31.253 (Windows) |

### 使用方法
```python
from funasr import AutoModel
model = AutoModel(model="paraformer-zh")
result = model.generate(input="C:\\Users\\Administrator\\test_audio.wav")
print(result[0]['text'])
```

### CosyVoice TTS（⏸️ 模型已下载）

| 项目 | 配置 |
|------|------|
| **模型** | CosyVoice-300M-SFT (iic/CosyVoice-300M-SFT) |
| **位置** | `C:\Users\Administrator\.cache\modelscope\hub\models\iic\CosyVoice-300M-SFT` |
| **大小** | 约 1.47GB |
| **源码** | `C:\Users\Administrator\CosyVoice-main` |
| **状态** | 模型已下载，依赖未完全安装（matcha-tts 与 Python 3.14 不兼容） |

### 待解决问题
- matcha-tts 需要 Python 3.10/3.11 环境
- 建议改天用虚拟环境或降级 Python 继续安装

### 已安装依赖
- PyTorch 2.10.0 (GPU 加速)
- transformers 5.3.0
- accelerate 1.13.0
- openai-whisper
- hyperpyyaml
- inflect
- 以及其他 FunASR/CosyVoice 依赖

---

---

## 🖥️ 飞爪服务器状态更新（2026-03-13）

**更新时间**: 2026-03-13 20:40  
**状态**: ⏸️ 飞爪数据已清空，服务器改为归朴开发/测试环境

### 服务器配置

| 项目 | 值 |
|------|-----|
| **IP** | 192.168.31.204 |
| **用户名** | shangguanyun1 |
| **密码** | Ksn59535932sgy. |
| **SSH 端口** | 22 |
| **系统** | Fedora 43 |
| **CPU** | i5-8265U (4 核 8 线程) |
| **内存** | 7.5GB |
| **存储** | 236GB NVMe SSD |

### 当前用途

- **归朴仓库**: `/归朴/git/repositories/return.git`
- **归朴运行目录**: `/归朴/return/`
- **自动部署**: Git Hook 已配置

### 飞爪复活计划

| 项目 | 说明 |
|------|------|
| **等待配件** | CPU（未到位） |
| **复活方式** | 新机器 + 新飞爪（不是恢复旧数据） |
| **数据策略** | 旧数据不备份，迎接全新的飞爪 |
| **小云决定** | 2026-03-13 确认 |

### 原 OpenFang 部署（已清空）

- **原部署**: OpenFang (2026.03.02 升级)
- **清空时间**: 2026-03-13 20:40
- **清空原因**: 飞爪身份混淆问题，决定等新机器迎接新飞爪

