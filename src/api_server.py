# -*- coding: utf-8 -*-
# File: src/api_server.py
"""
🧠 Personal Brain 统一生产网关 — RESTful API
完整覆盖人员管理、任务管理、事件总线、健康检查、数据库初始化等所有业务功能。
通过 Pydantic 模型提供请求体验证，响应格式统一。
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Body
from pydantic import BaseModel, Field, field_validator

from src.dao.person_dao import PersonDAO
from src.dao.task_dao import TaskDAO
from src.event_bus import event_bus
from src.service.person_service import PersonService
from src.service.task_service import TaskService
from src.agent.person_agent import PersonAgent
from src.agent.task_agent import TaskAgent
from src.db_model.base_model import init_database

logger = logging.getLogger("OpenClaw.ApiServer")

# =============================================================================
# FastAPI 应用实例
# =============================================================================
app = FastAPI(
    title="🧠 Personal Brain 统一生产网关",
    description=(
        "高内聚架构：纯粹的业务 API 服务层。\n\n"
        "完整覆盖人员管理、任务管理、事件监控三大模块。\n"
        "所有接口返回统一格式: {\"success\": bool, \"message\": str, \"data\": any}\n"
        "控制面自进化完全移交 OpenClaw 原生插件。"
    ),
    version="2.5.0"
)

# =============================================================================
# 业务组件初始化
# =============================================================================
person_dao = PersonDAO()
task_dao = TaskDAO(event_bus)
person_service = PersonService()
task_service = TaskService()
person_agent = PersonAgent()
task_agent = TaskAgent()

# =============================================================================
# Pydantic 请求/响应模型
# =============================================================================

class PersonCreate(BaseModel):
    """新增人员请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    relation_type: Optional[str] = Field(None, max_length=50, description="关系类型")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    birth_date: Optional[str] = Field(None, max_length=20, description="出生日期")
    age: Optional[int] = Field(None, ge=0, le=150, description="年龄")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    id_card: Optional[str] = Field(None, max_length=18, description="身份证号")
    household_address: Optional[str] = Field(None, description="户籍地址")
    work_unit: Optional[str] = Field(None, max_length=200, description="工作单位")
    position: Optional[str] = Field(None, max_length=100, description="职务")
    is_emergency_contact: Optional[bool] = Field(False, description="是否紧急联系人")
    remark: Optional[str] = Field(None, description="备注")


class PersonUpdate(BaseModel):
    """修改人员请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="姓名")
    relation_type: Optional[str] = Field(None, max_length=50, description="关系类型")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    birth_date: Optional[str] = Field(None, max_length=20, description="出生日期")
    age: Optional[int] = Field(None, ge=0, le=150, description="年龄")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    id_card: Optional[str] = Field(None, max_length=18, description="身份证号")
    household_address: Optional[str] = Field(None, description="户籍地址")
    work_unit: Optional[str] = Field(None, max_length=200, description="工作单位")
    position: Optional[str] = Field(None, max_length=100, description="职务")
    is_emergency_contact: Optional[bool] = Field(None, description="是否紧急联系人")
    remark: Optional[str] = Field(None, description="备注")


class TaskCreate(BaseModel):
    """新增任务请求模型"""
    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    task_type: Optional[str] = Field(None, max_length=50, description="任务类型")
    priority: Optional[str] = Field("普通", description="优先级 紧急/高/普通/低")
    start_time: Optional[str] = Field(None, max_length=20, description="开始时间")
    end_time: Optional[str] = Field(None, max_length=20, description="截止时间")
    remind_before: Optional[int] = Field(0, ge=0, description="提前提醒时长(分钟)")
    repeat_cycle: Optional[str] = Field(None, max_length=50, description="重复周期")
    status: Optional[str] = Field("待办", description="任务状态 待办/进行中/已完成/已取消")
    remark: Optional[str] = Field(None, description="任务备注")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ("紧急", "高", "普通", "低"):
            raise ValueError("优先级必须是: 紧急、高、普通、低")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ("待办", "进行中", "已完成", "已取消"):
            raise ValueError("状态必须是: 待办、进行中、已完成、已取消")
        return v


class TaskUpdate(BaseModel):
    """修改任务请求模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="任务标题")
    task_type: Optional[str] = Field(None, max_length=50, description="任务类型")
    priority: Optional[str] = Field(None, description="优先级 紧急/高/普通/低")
    start_time: Optional[str] = Field(None, max_length=20, description="开始时间")
    end_time: Optional[str] = Field(None, max_length=20, description="截止时间")
    remind_before: Optional[int] = Field(None, ge=0, description="提前提醒时长(分钟)")
    repeat_cycle: Optional[str] = Field(None, max_length=50, description="重复周期")
    status: Optional[str] = Field(None, description="任务状态 待办/进行中/已完成/已取消")
    remark: Optional[str] = Field(None, description="任务备注")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ("紧急", "高", "普通", "低"):
            raise ValueError("优先级必须是: 紧急、高、普通、低")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ("待办", "进行中", "已完成", "已取消"):
            raise ValueError("状态必须是: 待办、进行中、已完成、已取消")
        return v


class EventPublishRequest(BaseModel):
    """事件发布请求模型"""
    event_type: str = Field(..., min_length=1, description="事件类型")
    data: Any = Field(None, description="事件负载数据")


class EventSubscribeRequest(BaseModel):
    """事件订阅查询请求模型"""
    event_type: str = Field(..., min_length=1, description="事件类型")


class ApiResponse(BaseModel):
    """统一响应模型"""
    success: bool
    message: str
    data: Any = None


# =============================================================================
# 工具函数
# =============================================================================

def _wrap_response(result: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
    """
    将 Service 层返回的 dict 转换为统一格式的 API 响应。
    若 success=False 且状态码未特别指定，自动设为 400。
    """
    if not result.get("success", True) and status_code == 200:
        raise HTTPException(status_code=400, detail=result.get("message", "操作失败"))
    return result


# =============================================================================
# 数据库初始化
# =============================================================================

@app.on_event("startup")
async def startup_init():
    """应用启动时自动初始化数据库表"""
    init_database()
    logger.info("数据库表初始化完成")


# =============================================================================
# 健康检查 — 0. 系统状态与元信息
# =============================================================================

@app.get("/health", tags=["系统"])
async def health_check():
    """纯健康检查接口，由 OpenClaw 控制面统一管控"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "2.5.0"
    }


@app.get("/api/v1/version", tags=["系统"])
async def get_version():
    """获取 API 版本信息"""
    return {
        "success": True,
        "message": "Personal Brain API Server",
        "data": {
            "version": "2.5.0",
            "title": "🧠 Personal Brain 统一生产网关",
            "framework": "FastAPI"
        }
    }


# =============================================================================
# 人员管理 API — 1. 人员 CRUD
# =============================================================================

@app.post("/api/v1/persons", tags=["人员管理"])
async def create_person(person: PersonCreate):
    """新增人员"""
    result = person_agent.create_person(person.model_dump(exclude_none=True))
    return _wrap_response(result, 201)


@app.get("/api/v1/persons", tags=["人员管理"])
async def list_persons(
    name: Optional[str] = Query(None, description="按姓名模糊搜索", min_length=1)
):
    """
    查询所有人员。
    支持 name 参数进行模糊搜索。
    """
    if name:
        result = person_agent.search_persons(name)
    else:
        result = person_agent.list_persons()
    return _wrap_response(result)


@app.get("/api/v1/persons/{person_id}", tags=["人员管理"])
async def get_person(person_id: int):
    """根据 ID 查询单个人员"""
    result = person_agent.get_person(person_id)
    return _wrap_response(result)


@app.put("/api/v1/persons/{person_id}", tags=["人员管理"])
async def update_person(person_id: int, person: PersonUpdate):
    """修改人员信息"""
    update_data = person.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="未提供任何需要更新的字段")
    result = person_agent.update_person(person_id, update_data)
    return _wrap_response(result)


@app.delete("/api/v1/persons/{person_id}", tags=["人员管理"])
async def delete_person(person_id: int):
    """删除人员"""
    result = person_agent.delete_person(person_id)
    return _wrap_response(result)


# =============================================================================
# 任务管理 API — 2. 任务 CRUD
# =============================================================================

@app.post("/api/v1/tasks", tags=["任务管理"])
async def create_task(task: TaskCreate):
    """新增任务"""
    result = task_agent.create_task(task.model_dump(exclude_none=True))
    return _wrap_response(result, 201)


@app.get("/api/v1/tasks", tags=["任务管理"])
async def list_tasks(
    status: Optional[str] = Query(None, description="按状态筛选 待办/进行中/已完成/已取消"),
    today: Optional[bool] = Query(False, description="是否只查询今日任务"),
):
    """
    查询任务列表。
    - 不传参数: 返回所有任务
    - ?today=true: 返回今日任务
    - ?status=待办: 按状态筛选
    """
    if today:
        result = task_agent.list_today_tasks()
    elif status:
        result = task_agent.list_tasks_by_status(status)
    else:
        result = task_agent.list_tasks()
    return _wrap_response(result)


@app.get("/api/v1/tasks/{task_id}", tags=["任务管理"])
async def get_task(task_id: int):
    """根据 ID 查询单个任务"""
    result = task_agent.get_task(task_id)
    return _wrap_response(result)


@app.put("/api/v1/tasks/{task_id}", tags=["任务管理"])
async def update_task(task_id: int, task: TaskUpdate):
    """修改任务信息"""
    update_data = task.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="未提供任何需要更新的字段")
    result = task_agent.update_task(task_id, update_data)
    return _wrap_response(result)


@app.delete("/api/v1/tasks/{task_id}", tags=["任务管理"])
async def delete_task(task_id: int):
    """删除任务"""
    result = task_agent.delete_task(task_id)
    return _wrap_response(result)


@app.put("/api/v1/tasks/{task_id}/complete", tags=["任务管理"])
async def complete_task(task_id: int):
    """快捷完成任务（状态设为"已完成"）"""
    result = task_agent.complete_task(task_id)
    return _wrap_response(result)


# =============================================================================
# 事件总线 API — 3. 事件发布与监控
# =============================================================================

@app.post("/api/v1/events/publish", tags=["事件总线"])
async def publish_event(event: EventPublishRequest):
    """
    向事件总线发布一个事件。
    可用于测试事件联动或触发关联业务逻辑。
    """
    event_bus.publish(event.event_type, event.data)
    return {
        "success": True,
        "message": f"事件 '{event.event_type}' 已发布",
        "data": {"event_type": event.event_type, "data": event.data}
    }


@app.get("/api/v1/events/types", tags=["事件总线"])
async def list_event_types():
    """列出系统已知的所有事件类型常量"""
    from src.event_bus import (
        EVENT_CODE_EVOLUTION_START,
        EVENT_LOCK_ACQUIRED,
        EVENT_LOCK_FAILED,
        EVENT_GIT_BRANCH_CREATED,
        EVENT_SANDBOX_START,
        EVENT_SANDBOX_SUCCESS,
        EVENT_SANDBOX_FAILED,
        EVENT_GIT_PUSH_SUCCESS,
        EVENT_CONTAINER_RESTARTING,
    )
    return {
        "success": True,
        "message": "系统事件类型列表",
        "data": {
            "EVENT_CODE_EVOLUTION_START": EVENT_CODE_EVOLUTION_START,
            "EVENT_LOCK_ACQUIRED": EVENT_LOCK_ACQUIRED,
            "EVENT_LOCK_FAILED": EVENT_LOCK_FAILED,
            "EVENT_GIT_BRANCH_CREATED": EVENT_GIT_BRANCH_CREATED,
            "EVENT_SANDBOX_START": EVENT_SANDBOX_START,
            "EVENT_SANDBOX_SUCCESS": EVENT_SANDBOX_SUCCESS,
            "EVENT_SANDBOX_FAILED": EVENT_SANDBOX_FAILED,
            "EVENT_GIT_PUSH_SUCCESS": EVENT_GIT_PUSH_SUCCESS,
            "EVENT_CONTAINER_RESTARTING": EVENT_CONTAINER_RESTARTING,
        }
    }


@app.get("/api/v1/events/subscribers", tags=["事件总线"])
async def list_subscribers(event_type: Optional[str] = Query(None, description="按事件类型筛选")):
    """查看当前事件总线的订阅情况"""
    from src.event_bus import event_bus as eb
    subscribers = {}
    # 通过内部 _subscribers 获取快照（仅管理/调试用途）
    with eb._registry_lock:
        for evt_type, callbacks in eb._subscribers.items():
            if event_type and evt_type != event_type:
                continue
            subscribers[evt_type] = [cb.__name__ for cb in callbacks]
    return {
        "success": True,
        "message": "事件订阅列表",
        "data": subscribers
    }


# =============================================================================
# 数据库管理 API — 4. 数据库维护
# =============================================================================

@app.post("/api/v1/database/init", tags=["数据库"])
async def initialize_database():
    """手动触发数据库表初始化（重建缺失的表，不删已有数据）"""
    try:
        init_database()
        return {"success": True, "message": "数据库表初始化完成"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库初始化失败: {str(e)}")


@app.get("/api/v1/database/stats", tags=["数据库"])
async def get_database_stats():
    """获取数据库统计信息"""
    from src.db_model.base_model import Person, Task, get_db_session
    session = get_db_session()
    try:
        person_count = session.query(Person).count()
        task_count = session.query(Task).count()
        return {
            "success": True,
            "message": "数据库统计信息",
            "data": {
                "person_count": person_count,
                "task_count": task_count,
                "total_records": person_count + task_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
    finally:
        session.close()


# =============================================================================
# 根路由
# =============================================================================

@app.get("/", tags=["根路由"])
async def root():
    """API 根路由，返回服务概览"""
    return {
        "service": "🧠 Personal Brain 统一生产网关",
        "version": "2.5.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
        "endpoints": {
            "系统": ["GET /health", "GET /api/v1/version"],
            "人员管理": [
                "POST   /api/v1/persons",
                "GET    /api/v1/persons",
                "GET    /api/v1/persons/{id}",
                "PUT    /api/v1/persons/{id}",
                "DELETE /api/v1/persons/{id}",
            ],
            "任务管理": [
                "POST   /api/v1/tasks",
                "GET    /api/v1/tasks",
                "GET    /api/v1/tasks/{id}",
                "PUT    /api/v1/tasks/{id}",
                "DELETE /api/v1/tasks/{id}",
                "PUT    /api/v1/tasks/{id}/complete",
            ],
            "事件总线": [
                "POST   /api/v1/events/publish",
                "GET    /api/v1/events/types",
                "GET    /api/v1/events/subscribers",
            ],
            "数据库": [
                "POST   /api/v1/database/init",
                "GET    /api/v1/database/stats",
            ],
        }
    }
