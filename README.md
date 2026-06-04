# Personal Brain 个人大脑事务管理系统

基于 Python + SQLAlchemy + SQLite 的个人事务管理系统，采用严格的五层架构设计，支持通过 HTTP API 与 OpenClaw 网关非侵入式集成。

## 项目结构

```
personal_brain/
├── main.py                    # 控制台交互入口
├── api_server.py              # FastAPI HTTP 服务入口（OpenClaw集成）
├── event_bus.py               # 事件总线
├── interaction/               # 人机交互层
│   └── interaction_layer.py
├── agent/                     # Agent智能代理层
│   ├── person_agent.py
│   └── task_agent.py
├── service/                   # Service业务服务层
│   ├── person_service.py
│   └── task_service.py
├── dao/                       # DAO数据访问层
│   ├── person_dao.py
│   └── task_dao.py
├── db_model/                  # 数据库基础模型层
│   └── base_model.py
├── data/                      # SQLite数据库文件
│   └── brain_data.db
├── openclaw-integration.md    # OpenClaw集成指南
└── README.md                  # 本文件
```

## Windows 10 部署步骤

以下步骤针对 **Windows 10** 系统，使用 Docker Desktop + Docker Compose 一键部署 OpenClaw 网关 + Personal Brain HTTP API 服务。

> **端口说明**：Personal Brain API 服务运行在容器内部的 `18000` 端口，**不映射到宿主机**。OpenClaw 通过容器内 `localhost:18000` 直接调用 API，宿主机无法直接访问该端口，提升安全性。

---

### 前置要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| Windows 10 | 1903+ | 64位专业版/企业版/家庭版 |
| WSL2 | 已启用 | Docker Desktop 依赖 |
| Docker Desktop | 4.20+ | 包含 Docker Compose v2 |
| 大模型 API Key | - | 至少配置一个 LLM 提供商（见下方「常见大模型配置」） |

**检查环境**：

```powershell
# PowerShell 中执行
docker --version          # 应显示 Docker version 24.0.0+
docker compose version    # 应显示 Docker Compose version v2.20.0+
```

> 如果尚未安装 Docker Desktop，请前往 https://www.docker.com/products/docker-desktop 下载安装，安装过程中会自动启用 WSL2。

---

### 步骤一：获取大模型 API Key

根据你选择的模型提供商，获取对应的 API Key：

| 模型 | 获取地址 | 说明 |
|------|---------|------|
| **Kimi Code**（推荐） | [Moonshot AI 开放平台](https://platform.moonshot.cn/) | 注册 → API Key 管理 → 创建 Key → 勾选「Kimi Code」模型权限 |
| **OpenAI GPT** | [OpenAI Platform](https://platform.openai.com/) | 注册 → API Keys → Create new secret key |
| **Anthropic Claude** | [Anthropic Console](https://console.anthropic.com/) | 注册 → API Keys → Create Key |
| **阿里云通义千问** | [阿里云百炼](https://bailian.console.aliyun.com/) | 注册 → API Key 管理 → 创建 Key |
| **百度文心一言** | [百度智能云千帆](https://qianfan.cloud.baidu.com/) | 注册 → 应用接入 → 创建应用获取 API Key |
| **智谱 GLM** | [智谱 AI 开放平台](https://open.bigmodel.cn/) | 注册 → API Keys → 添加新的 API Key |
| **DeepSeek** | [DeepSeek 开放平台](https://platform.deepseek.com/) | 注册 → API Keys → 创建 API Key |

> ⚠️ **安全提示**：API Key 是敏感信息，不要截图、不要发送到聊天群、不要提交到 Git 仓库。`.env` 文件已被 `.gitignore` 保护。

---

### 步骤二：下载项目代码

```powershell
# 使用 PowerShell，进入你想存放项目的目录，例如 D:\Projects
cd D:\Projects

# 克隆项目（如果你使用 Git）
git clone https://github.com/your-repo/personal_brain.git
cd personal_brain

# 或者手动下载 ZIP 解压后进入目录
cd D:\Projects\personal_brain
```

---

### 步骤三：配置环境变量

```powershell
# 复制示例配置文件
copy .env.example .env

# 用记事本编辑 .env 文件
notepad .env
```

在记事本中修改以下关键配置：

```bash
# ============================================
# 必填：选择一个大模型提供商，填入对应的 API Key
# ============================================

# 方案 A：Kimi Code（推荐，默认已配置）
KIMI_CODE_API_KEY=sk-你的实际-kimi-api-key

# 方案 B：OpenAI GPT（可选）
# OPENAI_API_KEY=sk-你的实际-openai-api-key

# 方案 C：Anthropic Claude（可选）
# ANTHROPIC_API_KEY=sk-你的实际-anthropic-api-key

# ============================================
# 可选配置
# ============================================

# 如果 18789 端口被占用，可修改 Gateway 端口
# OPENCLAW_GATEWAY_PORT=18789

# 时区
TZ=Asia/Shanghai
```

保存后关闭记事本。

---

### 步骤四：启动服务

```powershell
# 在项目根目录下执行
docker compose up -d
```

首次启动会自动：
1. 拉取 OpenClaw 官方镜像（`ghcr.io/openclaw/openclaw:latest`）
2. 在容器内安装 Python 依赖（SQLAlchemy、FastAPI、Uvicorn）
3. 启动 Personal Brain HTTP API 服务（容器内部端口 18000，不暴露到宿主机）
4. 启动 OpenClaw Gateway 服务（端口 18789，映射到宿主机）

等待约 1-2 分钟，查看启动状态：

```powershell
# 查看容器状态
docker compose ps

# 查看实时日志（按 Ctrl+C 退出日志查看）
docker compose logs -f
```

当看到类似以下输出时，表示启动成功：

```
[Personal Brain] 服务已启动在 http://0.0.0.0:18000
[OpenClaw] 启动 Gateway...
```

---

### 步骤五：验证部署

打开 **PowerShell**，执行以下命令：

```powershell
# 检查 OpenClaw Gateway 健康状态
curl http://localhost:18789/healthz
# 预期输出: ok

# 查看自动生成的 Gateway Token（Web UI 登录需要）
type .gateway-token
```

> **注意**：`18000` 端口不映射到宿主机，因此宿主机无法直接 `curl localhost:18000`。OpenClaw 容器内部通过 `localhost:18000` 访问 Personal Brain API，这是正常设计。

---

### 步骤六：使用 Web UI 交互（推荐）

1. **打开浏览器**，访问：
   ```
   http://localhost:18789
   ```

2. **获取 Gateway Token**
   ```powershell
   # 在项目目录下查看自动生成的令牌
   type .gateway-token
   ```
   复制输出的那一长串字符。

3. **粘贴令牌登录**
   - 在 Web UI 的认证框中粘贴 `.gateway-token` 文件内容
   - 点击 **Connect** 连接

4. **创建会话**
   - 点击左上角 **+ New Session**
   - 模型会自动选择配置好的大模型

5. **开始使用**

   **示例 1：添加家人**
   ```
   用户: 帮我添加一个家人，姓名张三，关系是父亲，电话13800138000
   
   AI: [自动调用 Personal Brain API]
       curl -X POST http://127.0.0.1:18000/api/v1/persons ...
   
   AI: ✅ 已成功添加人员「张三」（关系：父亲，电话：13800138000）
   ```

   **示例 2：查询任务**
   ```
   用户: 我今天有什么任务？
   
   AI: [自动调用 API]
       curl -s http://127.0.0.1:18000/api/v1/tasks/today
   
   AI: 📋 今日任务：...
   ```

   **示例 3：AI 修改代码**
   ```
   用户: 帮我在人员表里添加「微信号」字段
   
   AI: [读取代码 → 分析架构 → 逐层修改 → 写入代码]
   
   AI: ✅ 已添加「微信号」字段：
       - db_model/base_model.py: Person 表新增 wechat 字段
       - service/person_service.py: 新增微信号格式校验
       
       ⚠️ 数据库模型已变更，需要重启服务使变更生效。
       是否立即重启？
   ```

---

### 步骤七：日常使用命令

```powershell
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重启服务
docker compose restart

# 查看实时日志
docker compose logs -f

# 更新 OpenClaw 镜像
docker compose pull openclaw-gateway
docker compose up -d openclaw-gateway

# 备份数据库（数据在 .\data\brain_data.db）
copy .\data\brain_data.db .\data\brain_data.db.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%

# 从容器内测试 Personal Brain API（验证内部通信）
docker compose exec openclaw-gateway sh -c "curl -s http://127.0.0.1:18000/health"
# 预期输出: {"status":"ok","service":"personal-brain"}
```

---

### 常见大模型配置

如需切换或添加其他大模型，编辑项目根目录下的 `openclaw.json` 文件，在 `models.providers` 中添加对应配置。

#### 1. Kimi Code（默认已配置）

```json
{
  "models": {
    "providers": {
      "anthropic": {
        "baseUrl": "https://api.kimi.com/coding",
        "apiKey": "${KIMI_CODE_API_KEY}",
        "api": "anthropic-messages",
        "models": [
          { "id": "kimi-k2.5", "name": "Kimi K2.5", "contextWindow": 128000, "maxTokens": 8192 }
        ]
      }
    }
  }
}
```

对应 `.env`：
```bash
KIMI_CODE_API_KEY=sk-你的实际-api-key
```

#### 2. OpenAI GPT-4 / GPT-4o

```json
{
  "models": {
    "providers": {
      "openai": {
        "baseUrl": "https://api.openai.com/v1",
        "apiKey": "${OPENAI_API_KEY}",
        "api": "openai-chat",
        "models": [
          { "id": "gpt-4o", "name": "GPT-4o", "contextWindow": 128000, "maxTokens": 4096 },
          { "id": "gpt-4-turbo", "name": "GPT-4 Turbo", "contextWindow": 128000, "maxTokens": 4096 }
        ]
      }
    }
  }
}
```

对应 `.env`：
```bash
OPENAI_API_KEY=sk-你的实际-api-key
```

#### 3. Anthropic Claude 3.5 Sonnet

```json
{
  "models": {
    "providers": {
      "anthropic": {
        "baseUrl": "https://api.anthropic.com",
        "apiKey": "${ANTHROPIC_API_KEY}",
        "api": "anthropic-messages",
        "models": [
          { "id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "contextWindow": 200000, "maxTokens": 8192 }
        ]
      }
    }
  }
}
```

对应 `.env`：
```bash
ANTHROPIC_API_KEY=sk-你的实际-api-key
```

#### 4. 阿里云通义千问

```json
{
  "models": {
    "providers": {
      "openai": {
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": "${DASHSCOPE_API_KEY}",
        "api": "openai-chat",
        "models": [
          { "id": "qwen-max", "name": "通义千问 Max", "contextWindow": 32000, "maxTokens": 8192 },
          { "id": "qwen-plus", "name": "通义千问 Plus", "contextWindow": 32000, "maxTokens": 8192 }
        ]
      }
    }
  }
}
```

对应 `.env`：
```bash
DASHSCOPE_API_KEY=sk-你的实际-api-key
```

#### 5. 百度文心一言

```json
{
  "models": {
    "providers": {
      "openai": {
        "baseUrl": "https://qianfan.baidubce.com/v2",
        "apiKey": "${QIANFAN_API_KEY}",
        "api": "openai-chat",
        "models": [
          { "id": "ernie-4.0-turbo-8k", "name": "文心一言 4.0 Turbo", "contextWindow": 8192, "maxTokens": 4096 }
        ]
      }
    }
  }
}
```

对应 `.env`：
```bash
QIANFAN_API_KEY=你的实际-api-key
```

#### 6. 智谱 GLM-4

```json
{
  "models": {
    "providers": {
      "openai": {
        "baseUrl": "https://open.bigmodel.cn/api/paas/v4",
        "apiKey": "${ZHIPU_API_KEY}",
        "api": "openai-chat",
        "models": [
          { "id": "glm-4", "name": "GLM-4", "contextWindow": 128000, "maxTokens": 4096 },
          { "id": "glm-4-plus", "name": "GLM-4 Plus", "contextWindow": 128000, "maxTokens": 4096 }
        ]
      }
    }
  }
}
```

对应 `.env`：
```bash
ZHIPU_API_KEY=你的实际-api-key
```

#### 7. DeepSeek

```json
{
  "models": {
    "providers": {
      "openai": {
        "baseUrl": "https://api.deepseek.com",
        "apiKey": "${DEEPSEEK_API_KEY}",
        "api": "openai-chat",
        "models": [
          { "id": "deepseek-chat", "name": "DeepSeek Chat", "contextWindow": 64000, "maxTokens": 8192 },
          { "id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "contextWindow": 64000, "maxTokens": 8192 }
        ]
      }
    }
  }
}
```

对应 `.env`：
```bash
DEEPSEEK_API_KEY=sk-你的实际-api-key
```

> **修改 `openclaw.json` 后，必须重启服务才能生效**：
> ```powershell
> docker compose restart openclaw-gateway
> ```

---

### Windows 10 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `docker compose` 命令不存在 | Docker Desktop 版本过旧 | 升级到 Docker Desktop 4.20+ |
| 端口 18789 被占用 | 其他程序占用了端口 | 修改 `.env` 中的 `OPENCLAW_GATEWAY_PORT` |
| 容器启动后立刻退出 | API Key 未配置或无效 | 检查 `.env` 中的对应模型 API Key |
| Web UI 无法访问 | 防火墙拦截 | 在 Windows 防火墙中放行 18789 端口 |
| PowerShell 中 curl 报错 | Windows 自带 curl 行为不同 | 使用 `Invoke-RestMethod` 替代，或安装 Git Bash |
| 中文显示乱码 | PowerShell 编码问题 | 执行 `chcp 65001` 切换到 UTF-8 |
| API 返回 401 | Gateway Token 错误 | 重新复制 `.gateway-token` 文件内容 |
| AI 不调用 Personal Brain API | openclaw.json 配置未生效 | 检查挂载路径，重启容器 |

---

## 架构约束

本项目严格遵守以下约束：

1. **五层架构**：人机交互层 → Agent层 → Service层 → DAO层 → 数据库模型层
2. **双模式运行**：同步业务调用 + 异步事件联动
3. **技术栈**：Python + SQLAlchemy + SQLite
4. **中文反馈**：所有操作输出中文结果

---

## 数据库表结构

### 人员表 (person)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| name | VARCHAR(100) | 姓名 |
| relation_type | VARCHAR(50) | 关系类型 |
| gender | VARCHAR(10) | 性别 |
| birth_date | VARCHAR(20) | 出生日期 |
| age | INTEGER | 年龄 |
| phone | VARCHAR(20) | 联系电话 |
| id_card | VARCHAR(18) | 身份证号 |
| household_address | TEXT | 户籍地址 |
| work_unit | VARCHAR(200) | 工作单位 |
| position | VARCHAR(100) | 职务 |
| is_emergency_contact | BOOLEAN | 是否紧急联系人 |
| remark | TEXT | 备注 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 任务表 (task)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| title | VARCHAR(200) | 任务标题 |
| task_type | VARCHAR(50) | 任务类型 |
| priority | VARCHAR(20) | 优先级 |
| start_time | VARCHAR(20) | 开始时间 |
| end_time | VARCHAR(20) | 截止时间 |
| remind_before | INTEGER | 提前提醒时长(分钟) |
| repeat_cycle | VARCHAR(50) | 重复周期 |
| status | VARCHAR(20) | 任务状态 |
| remark | TEXT | 任务备注 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

## 许可证

MIT
