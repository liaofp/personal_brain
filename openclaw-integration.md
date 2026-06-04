# Personal Brain × OpenClaw 非侵入式集成指南

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        OpenClaw 网关                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  AI Agent   │  │  CLI命令    │  │  消息渠道(Telegram等)    │ │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘ │
│         │                │                      │              │
│         └────────────────┼──────────────────────┘              │
│                          ▼                                     │
│              ┌─────────────────────┐                           │
│              │   标准工具调用        │  ← shell/browser工具     │
│              │  (不修改OpenClaw源码) │                           │
│              └──────────┬──────────┘                           │
│                         │ HTTP API                             │
└─────────────────────────┼──────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              Personal Brain HTTP 服务 (独立进程)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  FastAPI    │  │  Python五层  │  │    SQLite数据库          │ │
│  │  REST API   │  │  架构代码    │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                 │
│  启动: cd personal_brain && python3 api_server.py               │
│  端口: 18000 (可通过环境变量配置)                                │
└─────────────────────────────────────────────────────────────────┘
```

**核心原则：零侵入**
- 不修改 OpenClaw 任何源码
- 不添加 OpenClaw 插件
- 仅通过 OpenClaw 已有的标准工具（shell/browser）进行通信

---

## 第一步：启动 Personal Brain HTTP 服务

```bash
cd /path/to/personal_brain

# 安装依赖（如果尚未安装）
uv pip install sqlalchemy fastapi uvicorn

# 启动服务
python3 api_server.py
```

服务启动后：
- API 地址：`http://127.0.0.1:18000`
- API 文档：`http://127.0.0.1:18000/docs`
- 健康检查：`curl http://127.0.0.1:18000/health`

### 环境变量配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PERSONAL_BRAIN_HOST` | `127.0.0.1` | 监听地址 |
| `PERSONAL_BRAIN_PORT` | `18000` | 监听端口 |

### 后台运行（Linux/macOS）

```bash
# 使用 nohup
nohup python3 api_server.py > brain.log 2>&1 &

# 使用 systemd（推荐生产环境）
# 见文末 systemd 服务配置
```

---

## 第二步：OpenClaw 中调用 Personal Brain

### 方式一：AI 通过 shell 工具调用（推荐）

OpenClaw 的 AI 已经可以使用 `shell` 工具执行命令。直接让 AI 使用 curl 调用 API：

**示例对话：**

```
用户: 帮我添加一个家人，姓名张三，关系是父亲，电话13800138000

AI: 我来帮您添加这个人到 Personal Brain。

[AI 调用 shell 工具]
命令: curl -s -X POST http://127.0.0.1:18000/api/v1/persons \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","relation_type":"父亲","phone":"13800138000"}'

结果: {"success":true,"message":"人员 '张三' 新增成功",...}

AI: ✅ 已成功添加人员「张三」（关系：父亲，电话：13800138000）
```

### 方式二：AI 通过 browser 工具调用

如果 Personal Brain 服务暴露在公网或有内网访问，AI 可以使用 `browser` 工具：

```
[AI 调用 browser 工具]
action: open
targetUrl: http://127.0.0.1:18000/api/v1/persons
```

### 方式三：OpenClaw CLI 手动调用

```bash
# 添加人员
openclaw shell "curl -s -X POST http://127.0.0.1:18000/api/v1/persons -H 'Content-Type: application/json' -d '{\"name\":\"张三\",\"relation_type\":\"父亲\",\"phone\":\"13800138000\"}'"

# 查询所有人员
openclaw shell "curl -s http://127.0.0.1:18000/api/v1/persons"

# 添加任务
openclaw shell "curl -s -X POST http://127.0.0.1:18000/api/v1/tasks -H 'Content-Type: application/json' -d '{\"title\":\"买牛奶\",\"priority\":\"普通\",\"end_time\":\"2025-12-31\"}'"

# 查询今日任务
openclaw shell "curl -s http://127.0.0.1:18000/api/v1/tasks/today"

# 完成任务
openclaw shell "curl -s -X POST http://127.0.0.1:18000/api/v1/tasks/1/complete"
```

---

## 第三步：AI 修改 Personal Brain 代码

Personal Brain 提供了代码管理 API，允许 AI 读取和修改源代码。

### 列出所有代码文件

```bash
curl -s http://127.0.0.1:18000/api/v1/code/files
```

### 读取代码文件

```bash
curl -s "http://127.0.0.1:18000/api/v1/code/read?path=db_model/base_model.py"
```

### 写入代码文件（AI 修改代码）

```bash
curl -s -X POST http://127.0.0.1:18000/api/v1/code/write \
  -H "Content-Type: application/json" \
  -d '{
    "path": "db_model/base_model.py",
    "content": "# 新的代码内容..."
  }'
```

### AI 对话示例（修改代码）

```
用户: 帮我在 Personal Brain 的人员表里添加一个「微信号」字段

AI: 我来帮您修改代码。首先查看当前的数据库模型。

[AI 调用 shell 工具读取代码]
curl -s "http://127.0.0.1:18000/api/v1/code/read?path=db_model/base_model.py"

[AI 分析代码后，修改并写回]
curl -s -X POST http://127.0.0.1:18000/api/v1/code/write \
  -H "Content-Type: application/json" \
  -d '{"path":"db_model/base_model.py","content":"# -*- coding: utf-8 -*-\n..."}'

AI: ✅ 已添加「微信号」字段。修改内容：
   - db_model/base_model.py: Person表新增 wechat 字段
   - service/person_service.py: 校验逻辑已更新
   - dao/person_dao.py: 数据访问已更新

注意：需要重启 Personal Brain 服务使数据库变更生效。
```

---

## API 完整列表

### 人员管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/persons` | 新增人员 |
| GET | `/api/v1/persons` | 查询所有人员 |
| GET | `/api/v1/persons/{id}` | 查询单个人员 |
| PUT | `/api/v1/persons/{id}` | 修改人员 |
| DELETE | `/api/v1/persons/{id}` | 删除人员 |
| GET | `/api/v1/persons/search?name=关键字` | 搜索人员 |

### 任务管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/tasks` | 新增任务 |
| GET | `/api/v1/tasks` | 查询所有任务 |
| GET | `/api/v1/tasks/today` | 查询今日任务 |
| GET | `/api/v1/tasks/{id}` | 查询单个任务 |
| PUT | `/api/v1/tasks/{id}` | 修改任务 |
| DELETE | `/api/v1/tasks/{id}` | 删除任务 |
| POST | `/api/v1/tasks/{id}/complete` | 完成任务 |
| GET | `/api/v1/tasks/status/{status}` | 按状态查询 |

### 代码管理（AI 代码修改）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/code/files` | 列出所有 Python 文件 |
| GET | `/api/v1/code/read?path=xxx` | 读取源代码 |
| POST | `/api/v1/code/write` | 写入源代码 |

---

## OpenClaw 配置建议

### 1. 在 OpenClaw 配置中添加 Personal Brain 上下文

编辑 `~/.openclaw/openclaw.json`（或对应配置文件），在 agent 提示中添加 Personal Brain 的使用说明：

```json
{
  "agents": {
    "defaults": {
      "systemPrompt": "你可以使用 Personal Brain 个人大脑系统管理家人和任务。\n\nPersonal Brain API 地址: http://127.0.0.1:18000\n\n可用操作:\n- 人员管理: POST/GET/PUT/DELETE /api/v1/persons\n- 任务管理: POST/GET/PUT/DELETE /api/v1/tasks\n- 代码修改: GET/POST /api/v1/code/*\n\n使用 shell 工具执行 curl 命令调用 API。"
    }
  }
}
```

### 2. 使用 OpenClaw 的 `shell` 工具

确保 OpenClaw 配置中允许使用 `shell` 工具，并且 AI 知道如何调用 curl。

### 3. 可选：配置 systemd 自动启动

创建 `/etc/systemd/system/personal-brain.service`：

```ini
[Unit]
Description=Personal Brain HTTP API Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/personal_brain
ExecStart=/usr/bin/python3 /path/to/personal_brain/api_server.py
Restart=always
RestartSec=5
Environment=PERSONAL_BRAIN_PORT=18000
Environment=PERSONAL_BRAIN_HOST=127.0.0.1

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl enable personal-brain
sudo systemctl start personal-brain
sudo systemctl status personal-brain
```

---

## 安全注意事项

1. **代码写入安全**：代码管理 API 限制只能在 `personal_brain/` 目录内操作，禁止目录遍历
2. **网络访问**：默认只监听 `127.0.0.1`，不暴露给公网
3. **如需公网访问**：建议使用反向代理（nginx/caddy）+ HTTPS + API Key 认证
4. **数据库**：SQLite 文件存储在 `personal_brain/data/brain_data.db`，注意备份

---

## 故障排查

| 问题 | 排查方法 |
|------|----------|
| 服务无法启动 | 检查 `sqlalchemy`/`fastapi`/`uvicorn` 是否安装 |
| API 无响应 | 检查服务是否运行：`curl http://127.0.0.1:18000/health` |
| OpenClaw 调用失败 | 检查 OpenClaw 是否有 shell 工具权限 |
| 数据库错误 | 检查 `data/brain_data.db` 文件权限 |
| 代码写入失败 | 检查文件系统权限 |
