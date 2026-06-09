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
@app.post("/api/v1/evolution/mutate")
async def mutate_code_base(payload: MutateRequest, background_tasks: BackgroundTasks):
    if not payload.target_file or not payload.new_content:
        raise HTTPException(status_code=400, detail="突变参数缺失")

    # 🔒 目录遍历安全防御：统一防线切归到 /workspace
    safe_path = os.path.normpath(os.path.join("/workspace", payload.target_file))
    if not safe_path.startswith("/workspace"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="安全防御拦截：禁止大模型修改容器外部的任何敏感文件！"
        )

    # 试图抢占排他锁（独占编译测试流）
    if not code_manager.acquire_lock():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="当前系统有另一个自我进化流水线正在独占执行，请稍后再试"
        )

    try:
        # 执行你在 code_manager 中写好的核心业务流：
        # 复制影子代码 -> 拉起隔离容器跑 pytest -> 覆写真实工作区 -> 本地 Git 自动 Commit
        result = code_manager.execute_evolution_flow(payload.target_file, payload.new_content)
        
        if not result.get("success"):
            code_manager.release_lock()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"影子沙箱测试未通过！变更已安全拦截。Pytest 报错原因:\n{result.get('error')}"
            )

        # 🚀 代码完美通过测试：将其加入后台异步任务，安全地延迟自愈重启容器
        background_tasks.add_task(code_manager.trigger_production_restart)
        
        return {
            "success": True,
            "message": f"文件 {payload.target_file} 顺利通过影子回归测试，变更已并入主干，服务正在重启自愈中。"
        }

    except HTTPException:
        raise
    except Exception as e:
        code_manager.release_lock()
        raise HTTPException(status_code=500, detail=f"突变网关内部遭遇致命异常: {str(e)}")

# --- 2. 业务面：常驻核心业务接口群 ---
@app.get("/health")
async def health_check():
    return {"status": "healthy", "lock_state": "locked" if code_manager.is_evolving else "unlocked"}