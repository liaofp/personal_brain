# -*- coding: utf-8 -*-
"""
任务智能代理层
接收交互层路由下发的任务管理任务与参数
调用任务业务Service完成待办新增、查询、状态变更
任务数据变动时，发布对应事件至事件总线
监听相关联动事件，触发提醒、状态同步等附属逻辑
"""

from typing import Dict, Any
from service.task_service import TaskService
from event_bus import event_bus


class TaskAgent:
    """
    任务管理Agent
    负责任务相关业务的协调与事件发布
    """

    def __init__(self):
        self.task_service = TaskService()
        self._subscribe_events()

    def _subscribe_events(self):
        """
        订阅关联业务事件
        """
        event_bus.subscribe("person_changed", self._on_person_changed)
        event_bus.subscribe("reminder_triggered", self._on_reminder_triggered)

    def _publish_task_changed(self, action: str, task_data: Dict[str, Any]):
        """
        发布任务变更事件
        :param action: 变更动作类型
        :param task_data: 任务数据
        """
        event_bus.publish("task_changed", {
            "action": action,
            "task": task_data
        })

    def _on_person_changed(self, data: Dict[str, Any]):
        """
        人员变更时的联动处理
        :param data: 事件数据
        """
        action = data.get("action")
        person = data.get("person", {})
        person_name = person.get("name", "未知")
        print(f"【任务Agent】收到人员变更联动: 动作={action}, 人员={person_name}")

    def _on_reminder_triggered(self, data: Dict[str, Any]):
        """
        提醒触发时的联动处理
        :param data: 事件数据
        """
        task_id = data.get("task_id")
        task_title = data.get("task_title")
        print(f"【任务Agent】提醒触发: 任务ID={task_id}, 标题={task_title}")

    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        新增任务
        :param task_data: 任务信息
        :return: 处理结果
        """
        result = self.task_service.create_task(task_data)
        if result.get("success"):
            self._publish_task_changed("created", result.get("data", {}))
        return result

    def get_task(self, task_id: int) -> Dict[str, Any]:
        """
        查询单个任务
        :param task_id: 任务编号
        :return: 处理结果
        """
        return self.task_service.get_task_by_id(task_id)

    def list_tasks(self) -> Dict[str, Any]:
        """
        查询所有任务
        :return: 处理结果
        """
        return self.task_service.get_all_tasks()

    def list_today_tasks(self) -> Dict[str, Any]:
        """
        查询今日任务
        :return: 处理结果
        """
        return self.task_service.get_today_tasks()

    def list_tasks_by_status(self, status: str) -> Dict[str, Any]:
        """
        按状态查询任务
        :param status: 任务状态
        :return: 处理结果
        """
        return self.task_service.get_tasks_by_status(status)

    def update_task(self, task_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        修改任务
        :param task_id: 任务编号
        :param update_data: 更新数据
        :return: 处理结果
        """
        result = self.task_service.update_task(task_id, update_data)
        if result.get("success"):
            self._publish_task_changed("updated", result.get("data", {}))
        return result

    def delete_task(self, task_id: int) -> Dict[str, Any]:
        """
        删除任务
        :param task_id: 任务编号
        :return: 处理结果
        """
        result = self.task_service.delete_task(task_id)
        if result.get("success"):
            self._publish_task_changed("deleted", {"id": task_id})
        return result

    def complete_task(self, task_id: int) -> Dict[str, Any]:
        """
        完成任务
        :param task_id: 任务编号
        :return: 处理结果
        """
        result = self.task_service.update_task(task_id, {"status": "已完成"})
        if result.get("success"):
            self._publish_task_changed("completed", result.get("data", {}))
        return result
