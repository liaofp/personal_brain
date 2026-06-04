# OpenClaw + Personal Brain Docker Compose 部署文档

> **部署目标**：使用 Docker Compose 一键部署 OpenClaw 网关（官方镜像）+ Personal Brain HTTP API 服务 + Web UI，LLM 主模型使用 **Kimi Code**（通过 Anthropic-compatible 代理）。

---

## 目录

- [架构概览](#架构概览)
- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [详细部署步骤](#详细部署步骤)
- [配置文件说明](#配置文件说明)
- [日常使用](#日常使用)
- [交互操作指南](#交互操作指南)
- [AI 修改代码流程](#ai-修改代码流程)
- [故障排查](#故障排查)
- [高级配置](#高级配置)

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         单容器架构（OpenClaw 官方镜像）                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    openclaw-gateway 容器                         │   │
│  │              ghcr.io/openclaw/openclaw:latest                   │   │
│  │                                                                  │   │
│  │  ┌─────────────────────────┐    ┌─────────────────────────────┐ │   │
│  │  │   OpenClaw Gateway      │    │   Personal Brain (内置)     │ │   │
│  │  │   Node.js 24            │    │   Python 3 + FastAPI        │ │   │
│  │  │   端口: 18789/18790     │    │   端口: 18000               │ │   │
│  │  │                         │    │                             │ │   │
│  │  │  ┌─────────────────┐   │    │  ┌─────────────────────┐   │ │   │
│  │  │  │  AI Agent       │   │    │  │  五层架构 Python     │   │ │   │
│  │  │  │  Kimi Code      │◄──┘    │  │  SQLite 数据库       │   │ │   │
│  │  │  │  Moonshot API   │        │  └─────────────────────┘   │ │   │
│  │  │  └─────────────────┘   │    │                             │ │   │
│  │  │                        │    │  API: /api/v1/persons       │ │   │
│  │  │  工具: shell/browser   │    │       /api/v1/tasks         │ │   │
│  │  │       ↓ curl 调用      │    │       /api/v1/code/*        │ │   │
│  │  │       ↓ localhost:18000│    │                             │ │   │
│  │  └─────────────────────────┘    └─────────────────────────────┘ │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  配置绑定:                                                               │
│    - openclaw.json → /root/.openclaw/openclaw.json (ro)                 │
│    - AGENTS.md     → /pb/AGENTS.md (ro)                                 │
│    - CONSTRAINTS.md → /pb/CONSTRAINTS.md (ro)                           │
│                                                                          │
│  宿主机访问:                                                              │
│    - OpenClaw Web UI: http://localhost:18789                            │
│    - Personal Brain API: http://localhost:18000                         │
│    - API 文档: http://localhost:18000/docs                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**核心设计原则**:
- **零侵入**：不修改 OpenClaw 任何源码，不创建 OpenClaw 插件
- **官方镜像**：使用 `ghcr.io/openclaw/openclaw:latest`，无需本地构建
- **配置绑定**：`openclaw.json` 直接挂载到容器，注入 `systemPromptOverride`
- **HTTP 通信**：OpenClaw 通过标准 `shell` 工具执行 curl 调用 Personal Brain API
- **数据持久化**：SQLite 数据库和 OpenClaw 配置使用 bind mount

---

## 前置要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Kimi Code API Key | - | Kimi Code 的 Anthropic Auth Token |

**检查环境**：

```bash
docker --version          # Docker version 24.0.0+
docker compose version    # Docker Compose version v2.20.0+
```

---

## 快速开始

### 1. 进入目录

```bash
cd personal_brain
```

### 2. 配置环境变量

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env，填入你的 Kimi Code API Key
nano .env
```

`.env` 文件关键配置：

```bash
# Kimi Code - Anthropic Auth Token（必填）
ANTHROPIC_AUTH_TOKEN=sk-your-kimi-code-auth-token

# 时区（推荐）
TZ=Asia/Shanghai

# 端口（可选修改）
PERSONAL_BRAIN_PORT=18000
OPENCLAW_GATEWAY_PORT=18789
```

### 3. 启动

```bash
# 拉取官方镜像并启动
docker compose up -d

# 查看启动状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 4. 验证部署

```bash
# 检查 OpenClaw Gateway 健康状态
curl http://localhost:18789/healthz

# 检查 Personal Brain 健康状态
curl http://localhost:18000/health

# 测试添加人员
curl -s -X POST http://localhost:18000/api/v1/persons \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","relation_type":"父亲","phone":"13800138000"}'

# 查询人员列表
curl -s http://localhost:18000/api/v1/persons
```

---

## 详细部署步骤

### 步骤一：获取 Kimi Code API Key

1. 安装 Kimi Code CLI 并登录获取 Auth Token
2. 或从 Kimi Code 配置文件中找到 `ANTHROPIC_AUTH_TOKEN`
3. 复制 Token 到 `.env` 文件的 `ANTHROPIC_AUTH_TOKEN`

> ⚠️ **安全提示**：API Key 是敏感信息，不要提交到 Git 仓库。`.env` 文件已被 `.gitignore` 保护。

### 步骤二：理解目录结构

```
personal_brain/
├── docker-compose.yml         # Docker Compose 编排配置
├── .env.example               # 环境变量示例模板
├── .env                       # 实际环境变量（不提交到 Git）
├── .gateway-token             # Gateway 访问令牌（自动生成）
├── openclaw.json              # OpenClaw 全局配置文件（挂载到容器）
├── DEPLOY.md                  # 本部署文档
│
├── AGENTS.md                  # 项目级架构约束（挂载到 OpenClaw 容器）
├── CONSTRAINTS.md             # 代码生成指令（挂载到 OpenClaw 容器）
├── api_server.py              # FastAPI HTTP 服务
├── main.py                    # 控制台交互入口
├── event_bus.py               # 事件总线
├── interaction/               # 人机交互层
├── agent/                     # Agent 智能代理层
├── service/                   # Service 业务服务层
├── dao/                       # DAO 数据访问层
├── db_model/                  # 数据库基础模型层
└── data/                      # SQLite 数据库文件（Docker bind mount 持久化）
```

### 步骤三：配置绑定说明

`docker-compose.yml` 中的关键绑定：

```yaml
volumes:
  # OpenClaw 全局配置（核心：注入 systemPromptOverride）
  - ./openclaw.json:/root/.openclaw/openclaw.json:ro

  # Personal Brain 项目目录（读写挂载，支持 AI 修改代码）
  - .:/pb:rw
```

**绑定效果**：
- OpenClaw 启动时自动读取 `/root/.openclaw/openclaw.json`
- AI Agent 的 `systemPromptOverride` 已注入 Personal Brain 约束
- AI 可通过文件路径 `/pb/AGENTS.md` 读取完整约束

### 步骤四：验证服务间通信

```bash
# 从容器内测试访问 Personal Brain
docker compose exec openclaw-gateway sh -c \
  "curl -s http://127.0.0.1:18000/health"

# 预期输出: {"status":"ok","service":"personal-brain"}
```

---

## 配置文件说明

### openclaw.json（全局配置）

OpenClaw 启动时读取的配置文件，包含：

1. **Kimi Code 模型配置**：`models.providers.anthropic` 指向 Kimi Code 代理
2. **systemPromptOverride**：注入 Personal Brain 约束条件
   - 强制读取 `AGENTS.md` 和 `CONSTRAINTS.md`
   - 五层架构约束提醒
   - Personal Brain API 地址
   - AI 修改代码流程

**关键字段**：

```json
{
  "gateway": { "mode": "local" },
  "agents": {
    "defaults": {
      "model": "anthropic/kimi-k2.5",
      "systemPromptOverride": "..."
    }
  },
  "models": {
    "providers": {
      "anthropic": {
        "baseUrl": "https://api.kimi.com/coding",
        "apiKey": "${ANTHROPIC_AUTH_TOKEN}",
        "api": "anthropic-messages",
        "models": [{ "id": "kimi-k2.5", ... }]
      }
    }
  }
}
```

### 环境变量 (.env)

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `ANTHROPIC_AUTH_TOKEN` | ✅ | - | Kimi Code Anthropic Auth Token |
| `PERSONAL_BRAIN_PORT` | ❌ | 18000 | Personal Brain 宿主机端口 |
| `OPENCLAW_GATEWAY_PORT` | ❌ | 18789 | OpenClaw Gateway 宿主机端口 |
| `OPENCLAW_BRIDGE_PORT` | ❌ | 18790 | OpenClaw Bridge 端口 |
| `OPENCLAW_GATEWAY_BIND` | ❌ | lan | Gateway 绑定地址 |
| `OPENCLAW_GATEWAY_TOKEN` | ❌ | 自动生成 | Gateway 访问令牌 |
| `OPENCLAW_DISABLE_BONJOUR` | ❌ | 1 | 禁用 Bonjour |
| `TZ` | ❌ | Asia/Shanghai | 时区 |

**数据持久化路径（可选配置）**：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PERSONAL_BRAIN_DATA_DIR` | `./data` | SQLite 数据库目录 |
| `OPENCLAW_CONFIG_DIR` | `./.openclaw-config` | OpenClaw 配置目录 |
| `OPENCLAW_WORKSPACE_DIR` | `./.openclaw-workspace` | OpenClaw 工作区目录 |

> 默认使用当前目录下的相对路径，Docker Compose 会自动创建。
> 如需自定义路径，取消 `.env` 中对应变量的注释并修改。

### Docker Compose 服务

| 服务名 | 镜像 | 端口 | 说明 |
|--------|------|------|------|
| `openclaw-gateway` | `ghcr.io/openclaw/openclaw:latest` | 18789/18790/18000 | OpenClaw AI 网关 + Personal Brain（内置） |
| `openclaw-cli` | `ghcr.io/openclaw/openclaw:latest` | - | 交互式 CLI（可选） |

---

## 日常使用

### 启动/停止/重启

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 停止并删除数据卷（⚠️ 会清空数据库！）
docker compose down -v

# 重启单个服务
docker compose restart openclaw-gateway

# 查看实时日志
docker compose logs -f

# 查看单个服务日志
docker compose logs -f openclaw-gateway
```

### 更新 OpenClaw 镜像

```bash
# 拉取最新官方镜像
docker compose pull openclaw-gateway

# 重启使用新镜像
docker compose up -d openclaw-gateway
```

### 数据备份

```bash
# 备份 SQLite 数据库（默认路径 ./data）
docker compose exec openclaw-gateway sh -c \
  "cp /pb/data/brain_data.db /pb/data/brain_data.db.backup.$(date +%Y%m%d)"

# 导出到宿主机（默认路径 ./data）
docker compose cp openclaw-gateway:/pb/data/brain_data.db ./brain_data.db.backup

# 备份 OpenClaw 配置（默认路径 ./.openclaw-config）
docker compose cp openclaw-gateway:/root/.openclaw ./openclaw-backup
```

### 数据恢复

```bash
# 从宿主机恢复数据库（默认路径 ./data）
docker compose cp ./brain_data.db.backup openclaw-gateway:/pb/data/brain_data.db

# 重启服务
docker compose restart openclaw-gateway
```

### 修改 openclaw.json 后生效

```bash
# 修改宿主机 openclaw.json 后，重启 OpenClaw 即可生效
docker compose restart openclaw-gateway
```

---

## 交互操作指南

系统启动后，有三种方式与 Personal Brain 交互：

### 方式一：Web UI（浏览器）—— 推荐

**适用场景**：日常对话、自然语言管理家人和任务、AI 自动修改代码

**操作步骤**：

1. **打开 Web UI**
   ```
   浏览器访问 http://localhost:18789
   ```

2. **获取 Gateway Token**
   ```bash
   # 在项目目录下查看自动生成的令牌
   cat ~/workspace/personal_brain/.gateway-token
   ```

3. **粘贴令牌登录**
   - 在 Web UI 的认证框中粘贴 `.gateway-token` 文件内容
   - 点击 **Connect** 连接

4. **创建会话**
   - 点击左上角 **+ New Session**
   - 模型会自动选择配置好的 **Kimi Code**

5. **开始使用**

   **示例 1：添加家人**
   ```
   用户: 帮我添加一个家人，姓名张三，关系是父亲，电话13800138000
   
   AI: [自动调用 Personal Brain API]
       curl -X POST http://127.0.0.1:18000/api/v1/persons \
         -H "Content-Type: application/json" \
         -d '{"name":"张三","relation_type":"父亲","phone":"13800138000"}'
   
   AI: ✅ 已成功添加人员「张三」（关系：父亲，电话：13800138000）
   ```

   **示例 2：查询任务**
   ```
   用户: 我今天有什么任务？
   
   AI: [自动调用 API]
       curl -s http://127.0.0.1:18000/api/v1/tasks/today
   
   AI: 📋 今日任务：
       1. 买牛奶（优先级：普通，状态：待办）
       2. 取快递（优先级：紧急，状态：待办）
   ```

   **示例 3：AI 修改代码（添加字段）**
   ```
   用户: 帮我在人员表里添加「微信号」字段
   
   AI: [读取现有代码 → 分析架构 → 逐层修改 → 写入代码]
   
   AI: ✅ 已添加「微信号」字段：
       - db_model/base_model.py: Person 表新增 wechat 字段
       - service/person_service.py: 新增微信号格式校验
       - dao/person_dao.py: 无需修改（ORM 自动适配）
       
       ⚠️ 数据库模型已变更，需要重启服务使变更生效。
       是否立即重启？
   ```

**Web UI 界面说明**：

| 区域 | 功能 |
|------|------|
| 左侧边栏 | 会话列表、新建会话、设置 |
| 中间区域 | 对话消息、输入框 |
| 顶部 | 当前模型、工具调用状态 |
| 输入框 | 支持 Markdown、多行输入、文件上传 |

---

### 方式二：OpenClaw CLI（命令行）

**适用场景**：快速命令、脚本化操作、调试测试

**操作步骤**：

1. **启动 CLI**
   ```bash
   cd ~/workspace/personal_brain
   docker compose run --rm openclaw-cli
   ```

2. **CLI 交互示例**
   ```
   > 帮我添加一个家人，姓名李四，关系是母亲，电话13900139000
   
   [AI 调用 API]
   ✅ 已成功添加人员「李四」
   
   > 列出所有人员
   
   [AI 调用 API]
   📋 人员列表：
   1. 张三（父亲）- 13800138000
   2. 李四（母亲）- 13900139000
   ```

3. **退出 CLI**
   ```
   > /quit
   ```

---

### 方式三：直接调用 HTTP API

**适用场景**：第三方系统集成、自动化脚本、前端开发

**操作步骤**：

1. **健康检查**
   ```bash
   curl http://localhost:18000/health
   # 输出: {"status":"ok","service":"personal-brain"}
   ```

2. **人员管理**
   ```bash
   # 添加人员
   curl -X POST http://localhost:18000/api/v1/persons \
     -H "Content-Type: application/json" \
     -d '{"name":"张三","relation_type":"父亲","phone":"13800138000"}'

   # 查询所有人员
   curl -s http://localhost:18000/api/v1/persons

   # 查询单个人员
   curl -s http://localhost:18000/api/v1/persons/1

   # 修改人员
   curl -X PUT http://localhost:18000/api/v1/persons/1 \
     -H "Content-Type: application/json" \
     -d '{"phone":"13900139000"}'

   # 删除人员
   curl -X DELETE http://localhost:18000/api/v1/persons/1
   ```

3. **任务管理**
   ```bash
   # 添加任务
   curl -X POST http://localhost:18000/api/v1/tasks \
     -H "Content-Type: application/json" \
     -d '{"title":"买牛奶","priority":"普通","end_time":"2025-12-31"}'

   # 查询今日任务
   curl -s http://localhost:18000/api/v1/tasks/today

   # 完成任务
   curl -X POST http://localhost:18000/api/v1/tasks/1/complete
   ```

4. **AI 代码管理（供 AI 使用）**
   ```bash
   # 列出所有代码文件
   curl -s http://localhost:18000/api/v1/code/files

   # 读取代码
   curl -s "http://localhost:18000/api/v1/code/read?path=db_model/base_model.py"

   # 写入代码（AI 修改）
   curl -X POST http://localhost:18000/api/v1/code/write \
     -H "Content-Type: application/json" \
     -d '{
       "path": "db_model/base_model.py",
       "content": "# 新的代码内容..."
     }'
   ```

---

## AI 修改代码流程

当用户要求 AI 修改 Personal Brain 功能时，OpenClaw 会按以下流程执行：

### 流程图

```
用户输入修改需求
       │
       ▼
┌─────────────────┐
│ OpenClaw Agent  │◄── systemPromptOverride 注入约束
│ (Kimi Code 模型)│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ 1. 读取约束文件              │
│    /pb/AGENTS.md             │
│    /pb/CONSTRAINTS.md        │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 2. 读取现有代码              │
│    GET /api/v1/code/read     │
│    ?path=db_model/base_model.py
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 3. 分析架构影响              │
│    确认涉及层级，检查约束    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 4. 逐层修改代码              │
│    POST /api/v1/code/write   │
│    {path, content}           │
│    ► 自动架构约束检查        │
│    ► 违规则拒绝写入          │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 5. 重启服务验证（如需要）    │
│    docker compose restart    │
│    openclaw-gateway (内置)   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 6. 中文反馈结果              │
│    报告修改内容和验证结果    │
└─────────────────────────────┘
```

### 示例对话

**用户**：帮我在人员表里添加「微信号」字段

**AI 执行过程**：

```bash
# 1. 读取约束文件
cat /pb/AGENTS.md
cat /pb/CONSTRAINTS.md

# 2. 读取现有模型
GET http://127.0.0.1:18000/api/v1/code/read?path=db_model/base_model.py

# 3. 读取 Service 层
GET http://127.0.0.1:18000/api/v1/code/read?path=service/person_service.py

# 4. 修改并写入（自动通过约束检查）
POST http://127.0.0.1:18000/api/v1/code/write
{
  "path": "db_model/base_model.py",
  "content": "# ... 新增 wechat 字段后的代码"
}

# 5. 修改 Service 层校验
POST http://127.0.0.1:18000/api/v1/code/write
{
  "path": "service/person_service.py",
  "content": "# ... 新增 wechat 校验后的代码"
}

# 6. 提醒重启
# API 返回: needs_restart: true
```

**AI 回复用户**：

> ✅ 已添加「微信号」字段：
> - `db_model/base_model.py`: Person 表新增 `wechat` 字段（VARCHAR(50)）
> - `service/person_service.py`: 新增微信号格式校验
> - `dao/person_dao.py`: 无需修改（ORM 自动适配）
>
> ⚠️ 数据库模型已变更，需要重启服务使变更生效。
>
> 是否立即重启？

---

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker compose logs --tail=100 openclaw-gateway

# 检查端口占用
ss -tlnp | grep -E '18000|18789'

# 检查容器状态
docker compose ps
```

### Personal Brain API 无响应

```bash
# 从宿主机测试
curl -v http://localhost:18000/health

# 从容器内测试
docker compose exec openclaw-gateway curl -s http://127.0.0.1:18000/health

# 检查数据库权限（默认路径 ./data）
docker compose exec openclaw-gateway ls -la /pb/data/
```

### OpenClaw 无法调用 Personal Brain

```bash
# 测试 HTTP 访问
docker compose exec openclaw-gateway curl -s http://127.0.0.1:18000/health
```

### Kimi API 调用失败（401/404）

```bash
# 检查 API Key 是否正确设置
docker compose exec openclaw-gateway sh -c 'echo "TOKEN=$ANTHROPIC_AUTH_TOKEN"'

# 测试 API 连通性
curl -s https://api.kimi.com/coding/v1/models \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN"
```

### openclaw.json 未生效

```bash
# 检查文件是否正确挂载
docker compose exec openclaw-gateway cat /root/.openclaw/openclaw.json

# 检查文件内容
docker compose exec openclaw-gateway sh -c \
  'grep -c "systemPromptOverride" /root/.openclaw/openclaw.json'

# 重启生效
docker compose restart openclaw-gateway
```

### 数据库损坏

```bash
# 停止服务
docker compose down

# 删除损坏的数据库（数据会丢失！）
rm -rf ./data/brain_data.db

# 或者从备份恢复
docker compose cp ./brain_data.db.backup openclaw-gateway:/pb/data/brain_data.db

# 重新启动
docker compose up -d
```

### 常见错误码

| 错误 | 原因 | 解决 |
|------|------|------|
| `ECONNREFUSED` | 服务未启动 | `docker compose up -d` |
| `403 Forbidden` | 代码写入路径越界 | 确保 path 在 personal_brain/ 内 |
| `架构约束违规` | 代码违反 AGENTS.md | 按返回的 violations 修复 |
| `needs_restart` | 数据库模型变更 | `docker compose restart openclaw-gateway` |
| `ImagePullBackOff` | 镜像拉取失败 | 检查网络或手动 `docker pull` |
| `HTTP 401` | API Key 无效 | 检查 `ANTHROPIC_AUTH_TOKEN` |
| `HTTP 404` | API 端点错误 | 检查 `baseUrl` 和 `api` 配置 |

---

## 高级配置

### 使用其他 LLM 模型

编辑 `openclaw.json`，添加或修改 providers：

```json
{
  "models": {
    "providers": {
      "openai": {
        "baseUrl": "https://api.openai.com/v1",
        "apiKey": "${OPENAI_API_KEY}",
        "api": "openai-completions",
        "models": [
          {
            "id": "gpt-4",
            "name": "GPT-4",
            "contextWindow": 128000,
            "maxTokens": 8192
          }
        ]
      }
    }
  }
}
```

修改后重启：

```bash
docker compose restart openclaw-gateway
```

### 启用 HTTPS（生产环境）

使用反向代理（如 Caddy 或 Nginx）：

```yaml
# 在 docker-compose.yml 中添加
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
      - caddy-config:/config
    networks:
      - openclaw-net
```

```
# Caddyfile
openclaw.yourdomain.com {
    reverse_proxy openclaw-gateway:18789
}

brain.yourdomain.com {
    reverse_proxy openclaw-gateway:18000
}
```

### 资源限制

```yaml
services:
  openclaw-gateway:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 512M
```

### 指定 OpenClaw 镜像版本

```yaml
services:
  openclaw-gateway:
    image: ghcr.io/openclaw/openclaw:v1.2.3  # 指定版本号
```

### 离线部署（无网络环境）

```bash
# 1. 在有网络的环境中拉取镜像
docker pull ghcr.io/openclaw/openclaw:latest

# 2. 保存镜像
docker save ghcr.io/openclaw/openclaw:latest > openclaw.tar

# 3. 传输到目标机器后加载
docker load < openclaw.tar

# 4. 启动（无需拉取）
docker compose up -d
```

---

## 安全建议

1. **API Key 保护**：
   - `.env` 文件权限设为 `600`
   - 不要将 `.env` 提交到 Git
   - 定期轮换 API Key

2. **网络隔离**：
   - 生产环境使用 Docker Network 隔离
   - 不要暴露 Personal Brain 到公网
   - 使用反向代理 + HTTPS

3. **数据安全**：
   - 定期备份 `./data` 目录
   - 敏感字段（身份证号、电话）考虑加密存储

4. **容器安全**：
   - 已配置 `cap_drop` 和 `security_opt`

---

## 参考链接

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [OpenClaw Container Registry](https://github.com/openclaw/openclaw/pkgs/container/openclaw)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)

---

**部署完成！** 🎉

现在你可以通过以下方式使用服务：

| 方式 | 地址/命令 | 说明 |
|------|----------|------|
| **Web UI** | http://localhost:18789 | 浏览器打开，粘贴 `.gateway-token` 登录 |
| **CLI** | `docker compose run --rm openclaw-cli` | 命令行交互 |
| **API** | http://localhost:18000 | HTTP 直接调用 |
| **API 文档** | http://localhost:18000/docs | FastAPI 自动文档 |
