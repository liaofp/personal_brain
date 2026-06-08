# -*- coding: utf-8 -*-
"""
任务业务服务层
校验任务时间、优先级、状态等字段合规性
实现当日任务查询、新增待办、任务状态修改业务逻辑
不直接操作数据库底层模型
"""

from typing import Dict, Any, List, Optional
from src.dao.task_dao import TaskDAO


class TaskService:
    """
    任务业务服务
    处理任务管理相关业务逻辑
    """

    def __init__(self):
        self.task_dao = TaskDAO()

    def _validate_task_data(self, data: Dict[str, Any], is_update: bool = False) -> tuple:
        """
        校验任务数据合法性
        :param data: 任务数据字典
        :param is_update: 是否为更新操作
        :return: (是否通过, 错误信息)
        """
        if not is_update:
            if not data.get("title"):
                return False, "任务标题不能为空"

        if "title" in data and not data["title"]:
            return False, "任务标题不能为空"

        if "title" in data and len(data["title"]) > 200:
            return False, "任务标题长度不能超过200个字符"

        valid_priorities = ["紧急", "高", "普通", "低"]
        if "priority" in data and data["priority"]:
            if data["priority"] not in valid_priorities:
                return False, f"优先级必须是以下之一: {', '.join(valid_priorities)}"

        valid_statuses = ["待办", "进行中", "已完成", "已取消"]
        if "status" in data and data["status"]:
            if data["status"] not in valid_statuses:
                return False, f"任务状态必须是以下之一: {', '.join(valid_statuses)}"

        if "remind_before" in data and data["remind_before"] is not None:
            try:
                remind = int(data["remind_before"])
                if remind < 0:
                    return False, "提前提醒时长不能为负数"
            except (ValueError, TypeError):
                return False, "提前提醒时长必须是有效数字"

        return True, None

    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        新增任务
        :param task_data: 任务信息字典
        :return: 业务结果字典
        """
        valid, msg = self._validate_task_data(task_data)
        if not valid:
            return {"success": False, "message": msg}

        success, result = self.task_dao.create(task_data)
        if success:
            return {
                "success": True,
                "message": f"任务 '{result.title}' 新增成功",
                "data": result.to_dict()
            }
        return {"success": False, "message": result}

    def get_task_by_id(self, task_id: int) -> Dict[str, Any]:
        """
        根据ID查询任务
        :param task_id: 任务编号
        :return: 业务结果字典
        """
        success, result = self.task_dao.get_by_id(task_id)
        if success:
            return {
                "success": True,
                "message": "查询成功",
                "data": result.to_dict()
            }
        return {"success": False, "message": result}

    def get_all_tasks(self) -> Dict[str, Any]:
        """
        查询所有任务
        :return: 业务结果字典
        """
        success, result = self.task_dao.get_all()
        if success:
            return {
                "success": True,
                "message": f"共查询到 {len(result)} 条任务",
                "data": [t.to_dict() for t in result]
            }
        return {"success": False, "message": result}

    def get_today_tasks(self) -> Dict[str, Any]:
        """
        查询当日任务
        :return: 业务结果字典
        """
        success, result = self.task_dao.get_today_tasks()
        if success:
            return {
                "success": True,
                "message": f"今日共有 {len(result)} 条任务",
                "data": [t.to_dict() for t in result]
            }
        return {"success": False, "message": result}

    def get_tasks_by_status(self, status: str) -> Dict[str, Any]:
        """
        按状态查询任务
        :param status: 任务状态
        :return: 业务结果字典
        """
        success, result = self.task_dao.get_by_status(status)
        if success:
            return {
                "success": True,
                "message": f"状态为 '{status}' 的任务共 {len(result)} 条",
                "data": [t.to_dict() for t in result]
            }
        return {"success": False, "message": result}

    def update_task(self, task_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        修改任务
        :param task_id: 任务编号
        :param update_data: 更新数据字典
        :return: 业务结果字典
        """
        valid, msg = self._validate_task_data(update_data, is_update=True)
        if not valid:
            return {"success": False, "message": msg}

        success, result = self.task_dao.update(task_id, update_data)
        if success:
            return {
                "success": True,
                "message": f"任务 '{result.title}' 修改成功",
                "data": result.to_dict()
            }
        return {"success": False, "message": result}

    def delete_task(self, task_id: int) -> Dict[str, Any]:
        """
        删除任务
        :param task_id: 任务编号
        :return: 业务结果字典
        """
        success, result = self.task_dao.delete(task_id)
        if success:
            return {
                "success": True,
                "message": f"任务 '{result}' 删除成功"
            }
        return {"success": False, "message": result}
