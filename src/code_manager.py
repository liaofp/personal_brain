# ==========================================
# File: code_manager.py
# ==========================================
# -*- coding: utf-8 -*-
"""
OpenClaw 核心控制面：代码安全进化管理器
管理原子级排他锁、影子沙箱测试、Token版Git自动化流水线及容器自愈热重启。
"""

import os
import shutil
import logging
import threading
import subprocess
from typing import Tuple, Dict, Any
import docker

from src.event_bus import (
    event_bus,
    EVENT_CODE_EVOLUTION_START,
    EVENT_LOCK_ACQUIRED,
    EVENT_LOCK_FAILED,
    EVENT_SANDBOX_START,
    EVENT_SANDBOX_SUCCESS,
    EVENT_SANDBOX_FAILED,
    EVENT_GIT_PUSH_SUCCESS,
    EVENT_CONTAINER_RESTARTING
)

logger = logging.getLogger("OpenClaw.CodeManager")

class CodeEvolutionManager:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """
        单例模式：保证全局只有一个代码自进化管理器，维持锁状态绝对唯一
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(CodeEvolutionManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, workspace_dir: str = "/pb", sandbox_base_dir: str = "/tmp/pb_sandbox"):
        if self._initialized:
            return
        self.workspace_dir = workspace_dir
        self.sandbox_base_dir = sandbox_base_dir
        
        # 🏆 核心物理/内存双重保障排他锁
        self._state_lock = threading.Lock()
        self.is_evolving = False  # 互斥状态标志位
        
        # 初始化 Docker 客户端（完美通过 DOCKER_HOST 环境变量走 docker-proxy 通信）
        self._docker_client = None
        self._initialized = True

    @property
    def docker_client(self):
        if self._docker_client is None:
            try:
                self._docker_client = docker.from_env()
            except Exception as e:
                logger.error(f"无法初始化 Docker 客户端，请检查 DOCKER_HOST 或 docker-proxy 状态: {e}")
        return self._docker_client

    def acquire_lock(self) -> bool:
        """
        尝试抢占全局代码修改排他锁（非阻塞模式）
        """
        with self._state_lock:
            if self.is_evolving:
                logger.warning("加锁失败: 当前已有其他并发任务或用户正在修改维护代码。")
                event_bus.publish(EVENT_LOCK_FAILED, "已有其他用户或Agent线程正在修改代码，本次抢锁被拦截。")
                return False
            self.is_evolving = True
            logger.info("全局代码修改排他锁抢占成功。")
            event_bus.publish(EVENT_LOCK_ACQUIRED, "成功夺取代码进化排他锁，阻断其他并发修改。")
            return True

    def release_lock(self):
        """
        释放全局代码修改排他锁
        """
        with self._state_lock:
            self.is_evolving = False
            logger.info("全局代码修改排他锁已成功释放。")

    def execute_evolution_flow(self, target_rel_path: str, new_content: str) -> Dict[str, Any]:
        """
        全自动化修改维护流水线：抢锁 -> 影子沙箱测试 -> 覆写生产 -> 跨平台Git推送 -> 重启自身
        """
        # 1. 抢占排他锁。如果失败，立即拒绝请求，不阻塞调用线程
        if not self.acquire_lock():
            return {
                "success": False,
                "message": "❌ 拒绝操作：当前正有其他用户或大模型正在修改维护代码，系统已上锁，请稍后再试。"
            }

        event_bus.publish(EVENT_CODE_EVOLUTION_START, f"启动代码自进化。目标文件: {target_rel_path}")
        
        # 清理并创建纯净的影子沙箱代码目录
        if os.path.exists(self.sandbox_base_dir):
            shutil.rmtree(self.sandbox_base_dir)

        try:
            # 2. 复制当前运行期的物理代码到影子沙箱目录，隔绝对外污染
            # 忽略 .git 历史、Python 编译缓存以及本地读写中的持久化数据文件
            shutil.copytree(
                self.workspace_dir, 
                self.sandbox_base_dir, 
                ignore=shutil.ignore_patterns('.git', '__pycache__', 'data', '*.db', '.evolution.lock')
            )
            
            # 将大模型生成或修改的新代码，精准写入影子沙箱对应的文件路径中
            shadow_file_path = os.path.join(self.sandbox_base_dir, target_rel_path)
            os.makedirs(os.path.dirname(shadow_file_path), exist_ok=True)
            with open(shadow_file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # 3. 动态调用 Docker API 拉起物理隔离的影子测试沙箱运行 pytest
            event_bus.publish(EVENT_SANDBOX_START, f"拉起影子沙箱容器，对 {target_rel_path} 触发单元与回归测试...")
            
            if self.docker_client:
                # 动态以只读模式（ro）挂载影子代码目录到临时容器中跑测试
                # network_mode="none" 彻底切断测试网络，完全防御大模型反弹Shell或恶意投毒行为
                self.docker_client.containers.run(
                    image="personal-brain:evolution-v1.0", # 配合 docker-compose 构建的本地生产镜像
                    command=["pytest", "/pb"],
                    volumes={self.sandbox_base_dir: {'bind': '/pb', 'mode': 'ro'}},
                    network_mode="none",
                    remove=True, # 无论测试成功还是失败，测试完自动销毁容器
                    stdout=True,
                    stderr=True,
                    detach=False
                )
            else:
                # 兜底降级：如果 Docker 环境未初始化成功，使用物理子进程进行 pytest 回归测试
                logger.warning("Docker 客户端未就绪，使用宿主本地子进程环境降级运行测试...")
                res = subprocess.run(["pytest", self.sandbox_base_dir], capture_output=True, text=True, timeout=30)
                if res.returncode != 0:
                    raise Exception(f"本地降级测试未通过:\n{res.stderr or res.stdout}")

            event_bus.publish(EVENT_SANDBOX_SUCCESS, "🎉 影子沙箱回归测试 100% 通过！新代码逻辑安全。")

            # 4. 回归测试通过，将影子代码覆盖到真实的物理生产目录（/pb）
            real_production_path = os.path.join(self.workspace_dir, target_rel_path)
            os.makedirs(os.path.dirname(real_production_path), exist_ok=True)
            with open(real_production_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # 5. 安全执行 Git 自动化推送流程（通过 GitHub 环境变量中的 Token 无密码鉴权）
            token = os.getenv("GITHUB_TOKEN")
            repo_url_raw = os.getenv("GITHUB_REPO_URL") # 格式如: github.com/user/repo.git
            if token and repo_url_raw:
                repo_url_clean = repo_url_raw.replace("https://", "").replace("http://", "")
                authenticated_url = f"https://oauth2:{token}@{repo_url_clean}"
                
                # 配置临时环境凭证
                subprocess.run(["git", "config", "user.name", os.getenv("GIT_AUTHOR_NAME", "OpenClaw-Agent")], cwd=self.workspace_dir)
                subprocess.run(["git", "config", "user.email", os.getenv("GIT_AUTHOR_EMAIL", "agent@openclaw.io")], cwd=self.workspace_dir)
                
                # 执行 Git 提交组合拳
                subprocess.run(["git", "add", target_rel_path], cwd=self.workspace_dir)
                subprocess.run(["git", "commit", "-m", f"[OpenClaw Evolution] 自动优化维护 {target_rel_path}"], cwd=self.workspace_dir)
                
                push_res = subprocess.run(["git", "push", authenticated_url, "main"], cwd=self.workspace_dir, capture_output=True, text=True)
                if push_res.returncode == 0:
                    event_bus.publish(EVENT_GIT_PUSH_SUCCESS, "🚀 代码已成功同步 Push 提交至远端 GitHub 仓库。")
                else:
                    logger.error(f"Git Push 推送远端仓库失败: {push_res.stderr}")

            # 6. 安全触发热更新重启流程
            event_bus.publish(EVENT_CONTAINER_RESTARTING, "正在通过编排面安全重启 personal-brain 容器以加载新代码...")
            # 利用线程定时器延迟 2 秒执行重启，确保 FastAPI 能够把完整的成功响应推回给 OpenClaw 交互端
            threading.Timer(2.0, self._trigger_container_restart).start()

            return {
                "success": True,
                "message": f"✅ 代码 [{target_rel_path}] 修改成功！通过沙箱全量回归测试，已同步 GitHub，系统正在重启生效。"
            }

        except docker.errors.ContainerError as e:
            # 精准捕获 pytest 测试失败并抛出的容器内异常日志
            test_logs = e.stderr.decode('utf-8', errors='ignore')
            event_bus.publish(EVENT_SANDBOX_FAILED, f"❌ 测试失败：新代码存在逻辑缺陷，未通过影子沙箱测试。")
            return {
                "success": False,
                "message": f"❌ 未能通过影子沙箱测试，修改已被拦截安全撤销。测试崩溃日志如下:\n{test_logs}"
            }
        except Exception as e:
            logger.error(f"自进化流水线遭遇异常: {e}", exc_info=True)
            event_bus.publish(EVENT_SANDBOX_FAILED, f"自进化流水线异常中断: {str(e)}")
            return {"success": False, "message": f"❌ 系统修改异常: {str(e)}"}
        finally:
            # 🏆 无论进化成功还是中间报错，在结束时必须无条件释放排他锁，防止控制面死锁
            self.release_lock()

    def _trigger_container_restart(self):
        """
        通过安全代理平滑、安全地重新拉起自身容器
        """
        try:
            if self.docker_client:
                my_container = self.docker_client.containers.get("personal-brain")
                my_container.restart(timeout=5)
            else:
                # 极端兜底方案：直接强杀进程，依赖 docker-compose.yml 中的 restart: always 策略自动重启加载
                os._exit(0)
        except Exception as e:
            logger.error(f"安全代理控制面重启容器失败: {e}")
            os._exit(1)

# 全局暴露单例对象
code_manager = CodeEvolutionManager()