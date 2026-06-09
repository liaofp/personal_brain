# -*- coding: utf-8 -*-
import os
import logging
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any

from src.event_bus import NewEventBus
from src.code_manager import CodeEvolutionManager
from src.dao.person_dao import PersonDAO
from src.dao.task_dao import TaskDAO

logger = logging.getLogger("OpenClaw.ApiServer")

app = FastAPI(
    title="🧠 Personal Brain 统一生产网关",
    description="高内聚架构：融合业务 API 服务与控制面自进化隔离突变接口",
    version="2.5.0"
)

# 内存单例组件初始化（统一锚定 /workspace）
event_bus = NewEventBus()
code_manager = CodeEvolutionManager(workspace_dir="/workspace")
person_dao = PersonDAO()
task_dao = TaskDAO(event_bus)

class MutateRequest(BaseModel):
    target_file: str
    new_content: str

# --- 1. 控制面：大模型代码进化网关接口 ---
@app.post("/api/v1/evolution/mutate", summary="触发代码自进化流水线")
async def mutate_code_base(
    payload: MutateRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    接收 OpenClaw / LLM 下发的代码突变指令，执行完整的自进化流水线：
      抢锁 → 影子沙箱回归测试 → 覆写生产代码 → Git 自动推送 → 容器热重启
 
    锁管理完全由 CodeEvolutionManager.execute_evolution_flow() 负责，
    本接口不手动调用 acquire_lock() / release_lock()，彻底消除 double-lock 死锁。
    """
 
    # ── Step 1: 基础参数校验 ──────────────────────────────────
    if not payload.target_file or not payload.new_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="突变参数缺失：target_file 与 new_content 均为必填项。",
        )
 
    # ── Step 2: 路径安全防御（目录遍历拦截）──────────────────
    safe_path = os.path.normpath(os.path.join("/workspace", payload.target_file))
    if not safe_path.startswith("/workspace/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="安全防御拦截：禁止大模型修改 /workspace 之外的任何文件！",
        )
 
    # ── Step 3: 调用进化流水线（锁由内部统一管理）────────────
    logger.info(f"[突变请求] 目标文件: {payload.target_file}，安全路径校验通过，移交进化流水线。")
 
    result: Dict[str, Any] = code_manager.execute_evolution_flow(
        target_rel_path=payload.target_file,
        new_content=payload.new_content,
    )
 
    # ── Step 4: 根据流水线返回值映射 HTTP 响应 ────────────────
    if not result.get("success"):
        message = result.get("message", "未知错误")
 
        # 区分"锁冲突"与"流程失败"，返回语义准确的状态码
        if "已上锁" in message or "正在修改维护代码" in message:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=message,
            )
 
        # 沙箱测试未通过或其他流程失败
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
 
    # ── Step 5: 流水线成功 ────────────────────────────────────
    # execute_evolution_flow 内部已通过 threading.Timer 调度了容器重启，
    # 此处不再重复添加 background_tasks，避免双重重启。
    logger.info(f"[突变成功] {payload.target_file} 进化完毕，服务重启已调度。")
 
    return {
        "success": True,
        "message": result.get(
            "message",
            f"文件 {payload.target_file} 顺利通过影子回归测试，变更已并入主干，服务正在重启自愈中。",
        ),
    }

# --- 2. 业务面：常驻核心业务接口群 ---
@app.get("/health")
async def health_check():
    return {"status": "healthy", "lock_state": "locked" if code_manager.is_evolving else "unlocked"}