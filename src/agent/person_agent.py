# -*- coding: utf-8 -*-
"""
人员智能代理层
接收交互层路由下发的人员管理任务与参数
调用人员业务Service执行对应操作
人员信息变动后，主动向事件总线推送状态变更事件
订阅关联业务事件，监听到消息后触发对应联动处理
"""

from typing import Dict, Any
from src.service.person_service import PersonService
from src.event_bus import event_bus


class PersonAgent:
    """
    人员管理Agent
    负责人员相关业务的协调与事件发布
    """

    def __init__(self):
        self.person_service = PersonService()
        self._subscribe_events()

    def _subscribe_events(self):
        """
        订阅关联业务事件
        """
        event_bus.subscribe("task_assigned_to_person", self._on_task_assigned)
        event_bus.subscribe("person_emergency_updated", self._on_emergency_updated)

    def _publish_person_changed(self, action: str, person_data: Dict[str, Any]):
        """
        发布人员变更事件
        :param action: 变更动作类型
        :param person_data: 人员数据
        """
        event_bus.publish("person_changed", {
            "action": action,
            "person": person_data
        })

    def _on_task_assigned(self, data: Dict[str, Any]):
        """
        任务分配给人员时的联动处理
        :param data: 事件数据
        """
        person_id = data.get("person_id")
        task_title = data.get("task_title")
        print(f"【人员Agent】收到任务分配联动: 人员ID={person_id}, 任务={task_title}")

    def _on_emergency_updated(self, data: Dict[str, Any]):
        """
        紧急联系人更新时的联动处理
        :param data: 事件数据
        """
        person_id = data.get("person_id")
        is_emergency = data.get("is_emergency")
        print(f"【人员Agent】紧急联系人状态更新: 人员ID={person_id}, 状态={'是' if is_emergency else '否'}")

    def create_person(self, person_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        新增人员
        :param person_data: 人员信息
        :return: 处理结果
        """
        result = self.person_service.create_person(person_data)
        if result.get("success"):
            self._publish_person_changed("created", result.get("data", {}))
        return result

    def get_person(self, person_id: int) -> Dict[str, Any]:
        """
        查询单个人员
        :param person_id: 人员编号
        :return: 处理结果
        """
        return self.person_service.get_person_by_id(person_id)

    def list_persons(self) -> Dict[str, Any]:
        """
        查询所有人员
        :return: 处理结果
        """
        return self.person_service.get_all_persons()

    def update_person(self, person_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        修改人员信息
        :param person_id: 人员编号
        :param update_data: 更新数据
        :return: 处理结果
        """
        result = self.person_service.update_person(person_id, update_data)
        if result.get("success"):
            self._publish_person_changed("updated", result.get("data", {}))
        return result

    def delete_person(self, person_id: int) -> Dict[str, Any]:
        """
        删除人员
        :param person_id: 人员编号
        :return: 处理结果
        """
        result = self.person_service.delete_person(person_id)
        if result.get("success"):
            self._publish_person_changed("deleted", {"id": person_id})
        return result

    def search_persons(self, name: str) -> Dict[str, Any]:
        """
        搜索人员
        :param name: 姓名关键字
        :return: 处理结果
        """
        return self.person_service.search_persons_by_name(name)
