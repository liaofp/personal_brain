# ==========================================
# File: interaction_layer.py
# ==========================================
# -*- coding: utf-8 -*-
"""
OpenClaw 人机交互层主循环
集成意图识别路由，并通过事件总线（EventBus）异步渲染代码进化状态。
"""

import time
import threading
import logging
from typing import Dict, Any

from event_bus import (
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
from code_manager import CodeEvolutionManager

# 初始化日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("OpenClaw.Interaction")

class OpenClawInteractionLayer:
    def __init__(self):
        self.running = False
        # 初始化代码进化管理器
        self.code_manager = CodeEvolutionManager()
        self.current_user = "Developer_Admin" # 模拟当前交互用户名
        
        # 注册事件总线回调，实时在终端打印 AI 进化进度
        self._setup_event_subscriptions()

    def _setup_event_subscriptions(self):
        """
        订阅全链路进化事件，使用户在终端能清晰看到 AI 动态，消除卡死感
        """
        event_bus.subscribe(EVENT_CODE_EVOLUTION_START, lambda et, data: print(f"\n[🔄 进化启动] {data}"))
        event_bus.subscribe(EVENT_LOCK_ACQUIRED, lambda et, data: print(f"[🔒 锁控制] 成功为用户 {data} 抢占排他锁，阻断其他并发修改。"))
        event_bus.subscribe(EVENT_LOCK_FAILED, lambda et, data: print(f"[🚨 锁冲突] {data}"))
        event_bus.subscribe(EVENT_SANDBOX_START, lambda et, data: print(f"[🧪 沙箱测试] {data}"))
        
        def on_sandbox_success(et, data):
            print("============================================================")
            print("[✅ 测试通过] 影子沙箱单元测试 100% 成功！准备合并主线并推送 GitHub。")
            print("============================================================")
        event_bus.subscribe(EVENT_SANDBOX_SUCCESS, on_sandbox_success)

        def on_sandbox_failed(et, data):
            print("============================================================")
            print("[❌ 测试失败] 💥 AI 修改的代码未能通过沙箱测试！漏洞日志如下：")
            print(data)
            print("============================================================")
        event_bus.subscribe(EVENT_SANDBOX_FAILED, on_sandbox_failed)
        
        event_bus.subscribe(EVENT_GIT_PUSH_SUCCESS, lambda et, data: print(f"[🚀 GitHub] {data}"))
        event_bus.subscribe(EVENT_CONTAINER_RESTARTING, lambda et, data: print(f"[🔄 重启通知] {data}\n【提示】系统正在热更新，请等待容器重启完毕..."))

    def _parse_intent(self, user_input: str) -> Dict[str, Any]:
        """
        利用规则或大模型识别用户意图
        """
        ui_lower = user_input.lower()
        # 简单路由规则示例（实际生产中可接入 LLM 进行 Function Calling 意图识别）
        if "修改" in ui_lower or "改进" in ui_lower or "优化代码" in ui_lower or "fix" in ui_lower:
            return {"intent": "modify_code", "prompt": user_input}
        elif "执行" in ui_lower or "运行" in ui_lower:
            return {"intent": "execute_code", "prompt": user_input}
        else:
            return {"intent": "chat", "prompt": user_input}

    def _route_and_execute(self, intent_result: Dict[str, Any], raw_input: str) -> str:
        """
        根据意图分发路由
        """
        intent = intent_result.get("intent")
        prompt = intent_result.get("prompt")

        if intent == "execute_code":
            return f"【执行引擎】正在生产容器中安全运行指定代码... [执行成功]"
            
        elif intent == "modify_code":
            # 触发排他锁检查
            if not self.code_manager.acquire_lock(self.current_user):
                return "【拒绝操作】由于当前有其他工程师正在修改代码，系统已锁定，请稍后再试。"
            
            # 启动后台线程异步处理耗时的 AI 代码进化工作流，防止主线程 input 卡死
            threading.Thread(target=self._async_evolution_workflow, args=(prompt,), daemon=True).start()
            return "【系统响应】已成功受理您的代码修改请求。安全自进化流水线已在后台异步启动，请观察下方实时进度..."
            
        else:
            return f"【大脑对话】您说的是: '{raw_input}'。我是一个精通 Docker 和 OpenClaw 的 AI 助手。"

    def _async_evolution_workflow(self, prompt: str):
        """
        后台异步自进化工作流：修改 -> 沙箱测试 -> 提交 -> 释放锁 -> 重启
        """
        try:
            event_bus.publish(EVENT_CODE_EVOLUTION_START, "大模型正在思考并重构物理代码文件...")
            
            # -------------------------------------------------------------
            # 步骤 1：大模型修改代码逻辑（此处模拟大模型写出新代码到本地文件）
            # -------------------------------------------------------------
            time.sleep(3) # 模拟大模型推理和写文件耗时
            logger.info("AI 已经成功覆写了目标代码文件。")
            
            # -------------------------------------------------------------
            # 步骤 2：拉起物理隔离的影子沙箱进行安全性测试
            # -------------------------------------------------------------
            success, test_logs = self.code_manager.execute_shadow_sandbox_test(test_cmd="pytest tests/")
            
            if not success:
                logger.warning("沙箱测试未通过，中止后续发布流程。")
                # 在真实业务中，此处可将 test_logs 扔回给 LLM 开启最多3次的代码自愈（Self-Healing）
                return
            
            # -------------------------------------------------------------
            # 步骤 3：代码通过测试，使用 Token 凭证跨平台推送到 GitHub 远端
            # -------------------------------------------------------------
            commit_msg = f"自动优化: {prompt[:20]}..."
            push_ok, push_err = self.code_manager.commit_and_push_via_token(commit_msg)
            if not push_ok:
                logger.error(f"代码推送到 GitHub 失败: {push_err}")
                return
                
            # -------------------------------------------------------------
            # 步骤 4：通过安全代理滚动重启生产容器 personal-brain
            # -------------------------------------------------------------
            self.code_manager.trigger_production_restart()
            
        except Exception as e:
            logger.error(f"后台异步进化流水线遭遇致命异常: {e}", exc_info=True)
        finally:
            # 💡 雷打不动：无论进化成功还是中间出错，必须在结束时释放排他锁，防止死锁
            self.code_manager.release_lock()

    def start(self):
        """
        启动人机交互终端循环
        """
        self.running = True
        print("\n" + "=" * 60)
        print("    🧠 OpenClaw-Brain 安全代码自进化系统 V2 (Token版) 🧠")
        print("=" * 60)
        print("提示：输入包含 '修改' 或 '改进' 将触发【排他锁 + 影子沙箱测试 + Git提交】流水线。\n")

        while self.running:
            try:
                user_input = input("\n🧠 您想做什么？> ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'q', '退出']:
                    print("正在退出交互系统...")
                    self.running = False
                    break

                # 1. 意图识别
                intent_result = self._parse_intent(user_input)

                # 2. 路由分发与执行
                response = self._route_and_execute(intent_result, user_input)
                print(f"\n{response}")

            except KeyboardInterrupt:
                print("\n\n【提示】程序被用户中断，正在退出...")
                self.running = False
            except Exception as e:
                print(f"\n【错误】系统异常: {e}")
                
if __name__ == "__main__":
    # 启动交互层
    interaction = OpenClawInteractionLayer()
    interaction.start()