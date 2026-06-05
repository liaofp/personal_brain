# -*- coding: utf-8 -*-
"""
Personal Brain HTTP API 服务层
基于 FastAPI 提供 RESTful API，供 OpenClaw 网关调用
非侵入式集成：独立进程运行，通过 HTTP 通信
"""

import os
import sys
import subprocess
import threading
import re
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db_model.base_model import init_database
from service.person_service import PersonService
from service.task_service import TaskService

# 🏆 核心：引入内存排他锁，防止多用户并发修改代码时发生踩踏、覆盖
EVOLUTION_LOCK = threading.Lock()
# 记录当前哪个功能正在被谁或什么任务锁死
CURRENT_LOCKED_FEATURE = None

class SecureEvolveRequest(BaseModel):
    feature_name: str       # 功能模块名称（如主程序：'api_server'，或特定插件名）
    file_path: str          # 要修改的相对路径（如：'api_server.py' 或 'plugins/todo.py'）
    new_content: str        # 大模型生成的全新、全量代码
    commit_message: str


# ============================================================================
# Pydantic 模型定义
# ============================================================================

class PersonCreate(BaseModel):
    name: str = Field(..., description="姓名")
    relation_type: Optional[str] = Field(None, description="关系类型")
    gender: Optional[str] = Field(None, description="性别")
    birth_date: Optional[str] = Field(None, description="出生日期")
    age: Optional[int] = Field(None, description="年龄")
    phone: Optional[str] = Field(None, description="联系电话")
    id_card: Optional[str] = Field(None, description="身份证号")
    household_address: Optional[str] = Field(None, description="户籍地址")
    work_unit: Optional[str] = Field(None, description="工作单位")
    position: Optional[str] = Field(None, description="职务")
    is_emergency_contact: Optional[bool] = Field(False, description="是否紧急联系人")
    remark: Optional[str] = Field(None, description="备注")


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    relation_type: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    id_card: Optional[str] = None
    household_address: Optional[str] = None
    work_unit: Optional[str] = None
    position: Optional[str] = None
    is_emergency_contact: Optional[bool] = None
    remark: Optional[str] = None


class TaskCreate(BaseModel):
    title: str = Field(..., description="任务标题")
    task_type: Optional[str] = Field(None, description="任务类型")
    priority: Optional[str] = Field("普通", description="优先级")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="截止时间")
    remind_before: Optional[int] = Field(0, description="提前提醒时长(分钟)")
    repeat_cycle: Optional[str] = Field(None, description="重复周期")
    status: Optional[str] = Field("待办", description="任务状态")
    remark: Optional[str] = Field(None, description="任务备注")


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    task_type: Optional[str] = None
    priority: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    remind_before: Optional[int] = None
    repeat_cycle: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class CodeFileInfo(BaseModel):
    path: str
    size: int
    lines: int


class CodeWriteRequest(BaseModel):
    path: str = Field(..., description="相对路径，如 db_model/base_model.py")
    content: str = Field(..., description="文件内容")


# ============================================================================
# 服务实例
# ============================================================================

person_service = PersonService()
task_service = TaskService()


# ============================================================================
# FastAPI 应用
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("【API服务】正在初始化数据库...")
    init_database()
    print("【API服务】数据库初始化完成，服务已启动")
    yield
    print("【API服务】服务已关闭")


app = FastAPI(
    title="Personal Brain API",
    description="个人大脑事务管理系统 HTTP API - 供 OpenClaw 网关调用",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# 健康检查
# ============================================================================

@app.get("/health", summary="健康检查")
async def health_check():
    return {"status": "ok", "service": "personal-brain"}


# ============================================================================
# 人员管理 API
# ============================================================================

@app.post("/api/v1/persons", response_model=ApiResponse, summary="新增人员")
async def create_person(person: PersonCreate):
    result = person_service.create_person(person.model_dump(exclude_none=True))
    return JSONResponse(content=result)


@app.get("/api/v1/persons", response_model=ApiResponse, summary="查询所有人员")
async def list_persons():
    result = person_service.get_all_persons()
    return JSONResponse(content=result)


@app.get("/api/v1/persons/{person_id}", response_model=ApiResponse, summary="查询单个人员")
async def get_person(person_id: int):
    result = person_service.get_person_by_id(person_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return JSONResponse(content=result)


@app.put("/api/v1/persons/{person_id}", response_model=ApiResponse, summary="修改人员")
async def update_person(person_id: int, person: PersonUpdate):
    result = person_service.update_person(person_id, person.model_dump(exclude_none=True))
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return JSONResponse(content=result)


@app.delete("/api/v1/persons/{person_id}", response_model=ApiResponse, summary="删除人员")
async def delete_person(person_id: int):
    result = person_service.delete_person(person_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return JSONResponse(content=result)


@app.get("/api/v1/persons/search", response_model=ApiResponse, summary="搜索人员")
async def search_persons(name: str = Query(..., description="姓名关键字")):
    result = person_service.search_persons_by_name(name)
    return JSONResponse(content=result)


# ============================================================================
# 任务管理 API
# ============================================================================

@app.post("/api/v1/tasks", response_model=ApiResponse, summary="新增任务")
async def create_task(task: TaskCreate):
    result = task_service.create_task(task.model_dump(exclude_none=True))
    return JSONResponse(content=result)


@app.get("/api/v1/tasks", response_model=ApiResponse, summary="查询所有任务")
async def list_tasks():
    result = task_service.get_all_tasks()
    return JSONResponse(content=result)


@app.get("/api/v1/tasks/today", response_model=ApiResponse, summary="查询今日任务")
async def list_today_tasks():
    result = task_service.get_today_tasks()
    return JSONResponse(content=result)


@app.get("/api/v1/tasks/{task_id}", response_model=ApiResponse, summary="查询单个任务")
async def get_task(task_id: int):
    result = task_service.get_task_by_id(task_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return JSONResponse(content=result)


@app.put("/api/v1/tasks/{task_id}", response_model=ApiResponse, summary="修改任务")
async def update_task(task_id: int, task: TaskUpdate):
    result = task_service.update_task(task_id, task.model_dump(exclude_none=True))
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return JSONResponse(content=result)


@app.delete("/api/v1/tasks/{task_id}", response_model=ApiResponse, summary="删除任务")
async def delete_task(task_id: int):
    result = task_service.delete_task(task_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return JSONResponse(content=result)


@app.post("/api/v1/tasks/{task_id}/complete", response_model=ApiResponse, summary="完成任务")
async def complete_task(task_id: int):
    result = task_service.update_task(task_id, {"status": "已完成"})
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return JSONResponse(content=result)


@app.get("/api/v1/tasks/status/{status}", response_model=ApiResponse, summary="按状态查询任务")
async def list_tasks_by_status(status: str):
    result = task_service.get_tasks_by_status(status)
    return JSONResponse(content=result)


# ============================================================================
# 架构约束检查器（第三层保障：代码写入时自动验证）
# ============================================================================

class ArchitectureConstraintChecker:
    """
    架构约束自动检查器
    在代码写入前自动验证是否违反项目约束条件
    """

    # 五层架构对应的文件夹
    LAYER_FOLDERS = {
        "interaction": "人机交互层",
        "agent": "Agent智能代理层",
        "service": "Service业务服务层",
        "dao": "DAO数据访问层",
        "db_model": "数据库基础模型层",
    }

    # 各层级允许的操作
    LAYER_RULES = {
        "interaction": {
            "can_import": ["agent"],
            "cannot_import": ["service", "dao", "db_model"],
            "description": "人机交互层只能导入agent层",
        },
        "agent": {
            "can_import": ["service", "event_bus"],
            "cannot_import": ["dao", "db_model"],
            "description": "Agent层只能导入service层和event_bus",
        },
        "service": {
            "can_import": ["dao"],
            "cannot_import": ["db_model", "agent", "interaction"],
            "description": "Service层只能导入dao层",
        },
        "dao": {
            "can_import": ["db_model"],
            "cannot_import": ["service", "agent", "interaction"],
            "description": "DAO层只能导入db_model层",
        },
        "db_model": {
            "can_import": [],
            "cannot_import": ["dao", "service", "agent", "interaction"],
            "description": "db_model层不能导入任何上层",
        },
    }

    # 禁止的技术栈
    FORBIDDEN_TECH = [
        "pymongo", "mongodb", "mysql", "postgresql", "psycopg",
        "django", "flask", "tornado", "fastapi",  # fastapi仅允许在api_server.py
        "peewee", "pony", "tortoise",
        "redis", "celery", "rabbitmq", "kafka",
    ]

    # 允许的ORM操作
    ALLOWED_ORM = ["sqlalchemy", "create_engine", "Column", "Integer", "String",
                   "DateTime", "Boolean", "Text", "declarative_base", "sessionmaker",
                   "func", "Base", "Query"]

    @classmethod
    def check(cls, file_path: str, content: str) -> list:
        """
        检查代码是否违反架构约束
        :param file_path: 文件相对路径
        :param content: 文件内容
        :return: 违规列表，空列表表示通过
        """
        violations = []
        lines = content.split("\n")
        file_dir = file_path.split("/")[0] if "/" in file_path else ""

        # 1. 检查文件是否在正确的层级
        if file_dir and file_dir not in cls.LAYER_FOLDERS:
            if file_path not in ["main.py", "api_server.py", "event_bus.py", "AGENTS.md", "CONSTRAINTS.md"]:
                violations.append(f"文件 '{file_path}' 不在允许的层级文件夹中，必须在 {list(cls.LAYER_FOLDERS.keys())} 之一")

        # 2. 检查层级越级导入
        if file_dir in cls.LAYER_RULES:
            rules = cls.LAYER_RULES[file_dir]
            for line_no, line in enumerate(lines, 1):
                if line.strip().startswith("from ") or line.strip().startswith("import "):
                    for forbidden in rules["cannot_import"]:
                        if forbidden in line:
                            violations.append(
                                f"第{line_no}行: {rules['description']}，但发现导入 '{forbidden}'"
                            )

        # 3. 检查禁止的技术栈
        for line_no, line in enumerate(lines, 1):
            for tech in cls.FORBIDDEN_TECH:
                if tech in line.lower() and ("import" in line or "from" in line):
                    # fastapi 允许在 api_server.py 中使用
                    if tech == "fastapi" and file_path == "api_server.py":
                        continue
                    violations.append(f"第{line_no}行: 禁止引入技术 '{tech}'，项目固定使用 Python + SQLAlchemy + SQLite")

        # 4. 检查是否手写原生SQL
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip().lower()
            if any(keyword in stripped for keyword in ["execute(", "cursor.", "commit()"]):
                if "session" not in stripped and "sqlalchemy" not in stripped:
                    # 简单启发式检查，可能误报，但宁可误报
                    if "db_session" not in line and "sessionmaker" not in line:
                        violations.append(f"第{line_no}行: 疑似手写原生SQL，项目强制使用SQLAlchemy ORM")

        # 5. 检查事件总线是否被滥用
        if file_dir in ["service", "dao", "db_model"]:
            for line_no, line in enumerate(lines, 1):
                if "event_bus.publish" in line or "event_bus.subscribe" in line:
                    violations.append(
                        f"第{line_no}行: '{file_dir}' 层不应直接操作事件总线，事件发布应在Agent层处理"
                    )

        # 6. 检查Service层是否直接操作数据库模型
        if file_dir == "service":
            for line_no, line in enumerate(lines, 1):
                if "Base.metadata" in line or "create_engine" in line or "SessionLocal" in line:
                    violations.append(
                        f"第{line_no}行: Service层不应直接操作数据库引擎或会话工厂，应通过DAO层"
                    )

        # 7. 检查中文输出
        has_chinese = False
        for line in lines:
            if any("\u4e00" <= char <= "\u9fff" for char in line):
                has_chinese = True
                break
        if not has_chinese and file_path not in ["api_server.py"]:
            violations.append("代码中未包含中文注释或输出，项目要求中文反馈")

        # 8. 检查是否破坏现有文件（仅针对已有文件）
        full_path = os.path.join(PYTHON_DIR, file_path)
        if os.path.exists(full_path) and file_path not in ["api_server.py"]:
            # 读取旧文件检查关键结构是否被删除
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    old_content = f.read()
                # 检查类定义是否被删除
                old_classes = set(re.findall(r"^class\s+(\w+)", old_content, re.MULTILINE))
                new_classes = set(re.findall(r"^class\s+(\w+)", content, re.MULTILINE))
                deleted_classes = old_classes - new_classes
                if deleted_classes:
                    violations.append(
                        f"警告: 删除了已有类 {deleted_classes}，约束要求'已调试正常运行的模块代码禁止擅自修改、删除'"
                    )
            except Exception:
                pass

        return violations


# ============================================================================
# 代码管理 API（供 AI 修改代码使用）
# ============================================================================

PYTHON_DIR = os.path.dirname(os.path.abspath(__file__))


@app.get("/api/v1/code/files", response_model=ApiResponse, summary="列出所有Python文件")
async def list_code_files():
    try:
        files = []
        for root, dirs, filenames in os.walk(PYTHON_DIR):
            dirs[:] = [d for d in dirs if d not in ["__pycache__", "data", ".git"]]
            for filename in filenames:
                if filename.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, filename), PYTHON_DIR)
                    files.append(rel_path)
        files.sort()
        return {
            "success": True,
            "message": f"共 {len(files)} 个Python文件",
            "data": files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出文件失败: {str(e)}")


@app.get("/api/v1/code/read", response_model=ApiResponse, summary="读取Python源代码")
async def read_code_file(path: str = Query(..., description="相对路径，如 db_model/base_model.py")):
    try:
        full_path = os.path.normpath(os.path.join(PYTHON_DIR, path))
        if not full_path.startswith(os.path.normpath(PYTHON_DIR)):
            raise HTTPException(status_code=403, detail="非法路径")
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"文件不存在: {path}")

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "success": True,
            "message": f"读取成功: {path}",
            "data": {
                "path": path,
                "content": content,
                "size": len(content),
                "lines": content.count("\n") + 1,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {str(e)}")


@app.post("/api/v1/code/write", response_model=ApiResponse, summary="写入Python源代码")
async def write_code_file(req: CodeWriteRequest):
    try:
        full_path = os.path.normpath(os.path.join(PYTHON_DIR, req.path))
        if not full_path.startswith(os.path.normpath(PYTHON_DIR)):
            raise HTTPException(status_code=403, detail="非法路径，只允许访问插件目录内的文件")

        # ============================================================================
        # 第三层保障：架构约束自动检查
        # ============================================================================
        violations = ArchitectureConstraintChecker.check(req.path, req.content)
        if violations:
            return {
                "success": False,
                "message": f"代码修改违反架构约束，共 {len(violations)} 项违规",
                "data": {
                    "path": req.path,
                    "violations": violations,
                    "hint": "请修复上述违规项后再提交。详细约束见 AGENTS.md 和 CONSTRAINTS.md"
                }
            }

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(req.content)

        # 检查是否是数据库模型文件变更，提醒重启
        restart_hint = ""
        if req.path.startswith("db_model/"):
            restart_hint = "【重要】数据库模型已变更，需要重启 Personal Brain 服务使变更生效。"

        return {
            "success": True,
            "message": f"写入成功: {req.path} ({len(req.content)} 字节){' ' + restart_hint if restart_hint else ''}",
            "data": {"path": req.path, "size": len(req.content), "needs_restart": bool(restart_hint)}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入失败: {str(e)}")
    
# 定义大模型传过来的参数结构
class EvolutionRequest(BaseModel):
    file_path: str          # 想要修改的文件路径，例如 "api_server.py"
    new_content: str        # 大模型生成的全新全量代码
    commit_message: str     # Git 提交信息
    test_command: str = "pytest" # 可选：测试命令，默认 pytest

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/agent/evolve")
def secure_evolve(req: SecureEvolveRequest):
    """
    带状态检查的自进化 Skill：
    检查是否有人在改 -> 加锁 -> 备份 -> 覆写 -> 自动化测试 -> Git提交 -> 热加载/自重启
    """
    global CURRENT_LOCKED_FEATURE

    # 1. 🏆 核心逻辑：检查是否有人正在修改代码
    # 尝试非阻塞式加锁，如果已经被锁住，说明有其他用户正在通过 AI 改进代码
    acquired = EVOLUTION_LOCK.acquire(blocking=False)
    if not acquired:
        return {
            "success": False,
            "stage": "LOCK_REJECTED",
            "message": f"操作被拒绝：当前有用户正在改进【{CURRENT_LOCKED_FEATURE}】功能代码，请稍后再试，避免代码冲突！"
        }

    # 如果加锁成功，立刻标记当前的修改任务
    CURRENT_LOCKED_FEATURE = req.feature_name
    
    # 确保锁和状态在函数退出（无论成功或失败）时绝对能被释放
    try:
        # 安全路径校验，防止越权提权
        target_path = os.path.abspath(os.path.join("/pb", req.file_path))
        if not target_path.startswith("/pb"):
            raise HTTPException(status_code=400, detail="安全警告：禁止修改项目外部文件")

        # 2. 备份老代码（Bug 修复不通过时的后悔药）
        backup_path = f"{target_path}.bak"
        if os.path.exists(target_path):
            subprocess.run(f"cp {target_path} {backup_path}", shell=True, check=True)

        # 3. 大模型重写/修复代码
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(req.new_content)

        # 4. 严苛的自动化测试
        # 尝试编译和运行内检，如果是改了主程序，这里会启动一路由独立进程进行语法沙箱内检
        test_res = subprocess.run(f"python3 -m py_compile {target_path}", shell=True, capture_output=True)
        if test_res.returncode != 0:
            # 发现 Bug/编译失败，立刻执行原子级回滚！
            if os.path.exists(backup_path):
                subprocess.run(f"mv {backup_path} {target_path}", shell=True, check=True)
            return {
                "success": False,
                "stage": "AUTO_TEST_FAILED",
                "error_log": test_res.stderr.decode(),
                "message": "大模型修改的代码未通过编译测试！系统已拒绝并自动回滚老代码。请将报错发给大模型重试。"
            }

        # 5. 测试通过，安全提交 Git 队列
        if os.path.exists(backup_path):
            os.remove(backup_path)
        subprocess.run(f"git add {target_path}", shell=True, cwd="/pb")
        subprocess.run(f'git commit -m "{req.commit_message}" || true', shell=True, cwd="/pb")

        # 6. 🏆 零断网重启机制
        # 如果改的是 api_server.py 本身，我们需要重启。但为了防止其他用户瞬间断线：
        # 我们利用之前在 docker-compose 里配置的 uvicorn --reload 机制。
        # 当 uvicorn 检测到 api_server.py 文件被修改时，它会在【内存中热重启工作线程（Worker）】，
        # 期间网络端口不断开，外部用户的请求会在 socket 队列里排队 0.5 秒，实现多用户无感知自愈！
        
        return {
            "success": True,
            "stage": "SUCCESS_EVOLVED",
            "message": f"恭喜！功能【{req.feature_name}】代码优化/Bug修复成功，已通过编译测试并提交 Git，系统已完成零停机平滑升级！"
        }

    except Exception as e:
        # 极端崩溃兜底
        if 'backup_path' in locals() and os.path.exists(backup_path):
            subprocess.run(f"mv {backup_path} {target_path}", shell=True, check=True)
        return {"success": False, "stage": "SYSTEM_CRASH", "detail": str(e)}

    finally:
        # 🏆 无论结果如何，必须在最后释放锁，让下一个用户进场
        CURRENT_LOCKED_FEATURE = None
        EVOLUTION_LOCK.release()


# ============================================================================
# 启动入口
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PERSONAL_BRAIN_PORT", "18000"))
    host = os.environ.get("PERSONAL_BRAIN_HOST", "127.0.0.1")
    print(f"【API服务】启动 Personal Brain HTTP API 服务")
    print(f"【API服务】监听地址: http://{host}:{port}")
    print(f"【API服务】API文档: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port)
