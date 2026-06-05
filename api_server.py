# ==========================================
# File: api_server.py
# ==========================================
# -*- coding: utf-8 -*-
"""
OpenClaw - Personal Brain 统一 REST API 路由网关
处理代码读取、基础运行状态，并将修改维护请求原子化路由至安全自进化控制面。
"""

import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from code_manager import code_manager

app = FastAPI(
    title="Personal Brain REST API Gate",
    description="支持 OpenClaw AI Agent 的代码安全自进化个人大脑控制面接口",
    version="2.0.0"
)

# ==========================================
# Pydantic 请求数据模型定义
# ==========================================
class CodeWriteRequest(BaseModel):
    path: str       # 相对 /pb 的代码文件路径，如 "api_server.py" 或 "models.py"
    content: str    # 大模型重新生成或修复后的完整物理文件源码内容

@app.get("/health")
async def health_check():
    """
    健康检查接口，保障 OpenClaw 网关、探针与本大脑容器无缝互通
    """
    return {
        "status": "ok",
        "service": "personal-brain",
        "lock_occupied": code_manager.is_evolving  # 暴露当前的锁状态，便于人机交互层感知
    }

# ==========================================
# 【模式 A】执行与运行代码 / 基础数据读写维护
# ==========================================
@app.get("/api/v1/code/files")
async def list_python_files():
    """
    获取当前系统中全部可供维护、修改和理解的 Python 代码文件清单
    """
    python_files = []
    root_dir = "/pb"
    for root, dirs, files in os.walk(root_dir):
        # 严格过滤 Git 目录、Python 编译缓存以及运行时产生的数据存放区
        if '.git' in root or '__pycache__' in root or 'data' in root or '.tmp' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, file), root_dir)
                python_files.append(rel_path)
    return {"files": python_files}

@app.get("/api/v1/code/read")
async def read_code_file(path: str):
    """
    读取指定的物理源码内容（供大模型理解系统架构与上下文关联）
    """
    if not path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="路径不能为空")

    # 🔒 严防死守：通过路径标准化，彻底斩断大模型通过 "../" 发起的目录遍历攻击 (Directory Traversal)
    safe_path = os.path.normpath(os.path.join("/pb", path))
    if not safe_path.startswith("/pb"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="安全防御拦截：禁止大模型非法读取容器外部的宿主机敏感文件！"
        )
    
    if not os.path.exists(safe_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到指定的源码文件: {path}")
        
    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            return {"path": path, "content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"文件读取失败: {str(e)}")

# ==========================================
# 【模式 B】修改与改进代码（核心演进控制网关）
# ==========================================
@app.post("/api/v1/code/write")
async def modify_and_evolve_code(req: CodeWriteRequest):
    """
    修改/改进代码核心接口。
    拒绝大模型直接覆写本地生产环境，全量路由并激活【排他锁 + 影子沙箱隔离测试 + Git推送 + 重启自愈】流水线。
    """
    if not req.path or not req.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="不合法的写入请求：路径与代码内容均不可为空"
        )
    
    # 路径越界安全性校验
    safe_path = os.path.normpath(os.path.join("/pb", req.path))
    if not safe_path.startswith("/pb"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="安全防御拦截：越界非法写入")

    # 执行全自动化修改进化流水线
    result = code_manager.execute_evolution_flow(req.path, req.content)
    
    if not result["success"]:
        # 🏆 采用 HTTP 423 Locked（已锁定）标准状态码，精准、规范地向前端网关透传排他锁互斥拒绝响应
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED, 
            detail=result["message"]
        )
        
    return result