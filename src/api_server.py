# -*- coding: utf-8 -*-
# File: src/api_server.py
import logging
from fastapi import FastAPI
from src.dao.person_dao import PersonDAO
from src.dao.task_dao import TaskDAO
from src.event_bus import event_bus

logger = logging.getLogger("OpenClaw.ApiServer")

app = FastAPI(
    title="🧠 Personal Brain 统一生产网关",
    description="高内聚架构：纯粹的业务 API 服务层（控制面自进化完全移交 OpenClaw 原生插件）",
    version="2.5.0"
)

# 仅初始化业务 DAO 组件
person_dao = PersonDAO()
task_dao = TaskDAO(event_bus)

@app.get("/health")
async def health_check():
    # 状态由 OpenClaw 控制面统一管控，此处保持纯净健康检查
    return {"status": "healthy"}