# ==========================================
# File: event_bus.py
# ==========================================
# -*- coding: utf-8 -*
"""
基于观察者模式和线程安全架构的事件总线。
用于将 OpenClaw 代码自我进化、测试和部署的长耗时中间状态异步通知给人机交互层。
"""

import logging
import threading
from typing import Callable, Dict, List, Any

# 初始化日志记录
logger = logging.getLogger("OpenClaw.EventBus")

# ==========================================
# 核心事件类型常量定义
# ==========================================
EVENT_CODE_EVOLUTION_START = "code.evolution.start"
EVENT_LOCK_ACQUIRED        = "lock.acquired"
EVENT_LOCK_FAILED          = "lock.failed"
EVENT_GIT_BRANCH_CREATED   = "git.branch.created"
EVENT_SANDBOX_START        = "sandbox.start"
EVENT_SANDBOX_SUCCESS      = "sandbox.success"
EVENT_SANDBOX_FAILED       = "sandbox.failed"
EVENT_GIT_PUSH_SUCCESS     = "git.push.success"
EVENT_CONTAINER_RESTARTING = "container.restarting"


class NewEventBus:
    """
    单例模式的高性能线程安全事件总线
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """
        确保全局只有一个事件总线实例，维持状态一致性
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(NewEventBus, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._subscribers: Dict[str, List[Callable[[str, Any], None]]] = {}
        self._registry_lock = threading.Lock()  # 保护订阅者名册的并发安全锁
        self._initialized = True
        logger.info("OpenClaw 全局事件总线初始化成功。")

    def subscribe(self, event_type: str, callback: Callable[[str, Any], None]):
        """
        订阅特定类型的事件
        :param event_type: 事件类型常量 (例如 EVENT_SANDBOX_START)
        :param callback: 触发事件时的回调函数，签名需为 func(event_type: str, data: Any)
        """
        with self._registry_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                logger.debug(f"订阅成功 - 事件: {event_type} | 回调: {callback.__name__}")

    def unsubscribe(self, event_type: str, callback: Callable[[str, Any], None]):
        """
        取消订阅特定类型的事件
        """
        with self._registry_lock:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"退订成功 - 事件: {event_type} | 回调: {callback.__name__}")

    def publish(self, event_type: str, data: Any = None):
        """
        同步或异步广播发布一个事件，触发所有注册过的回调
        :param event_type: 事件类型常量
        :param data: 附带的上下文负载数据（如同异步传输的日志、错误信息或中间状态）
        """
        # 获取当前时间点订阅者的快照，防止在回调执行过程中有其他线程修改订阅列表引发 RuntimeError
        callbacks_to_execute = []
        with self._registry_lock:
            if event_type in self._subscribers:
                callbacks_to_execute = list(self._subscribers[event_type])

        if not callbacks_to_execute:
            logger.debug(f"发布事件 {event_type}，但当前没有订阅者接收。")
            return

        for callback in callbacks_to_execute:
            try:
                # 触发回调执行
                callback(event_type, data)
            except Exception as e:
                logger.error(f"事件总线在执行回调时崩溃 | 事件: {event_type} | 错误: {str(e)}", exc_info=True)


# 全局单例导出，方便其他模块直接 import 使用
event_bus = NewEventBus()