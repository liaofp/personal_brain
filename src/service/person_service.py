# -*- coding: utf-8 -*-
"""
人员业务服务层
承接人员新增、查询、编辑、删除核心业务
做数据合法性校验、格式规范、业务规则判断
不直接操作数据库底层模型
"""

from typing import Dict, Any, List, Optional
from src.dao.person_dao import PersonDAO


class PersonService:
    """
    人员业务服务
    处理人员管理相关业务逻辑
    """

    def __init__(self):
        self.person_dao = PersonDAO()

    def _validate_person_data(self, data: Dict[str, Any], is_update: bool = False) -> tuple:
        """
        校验人员数据合法性
        :param data: 人员数据字典
        :param is_update: 是否为更新操作
        :return: (是否通过, 错误信息)
        """
        if not is_update:
            if not data.get("name"):
                return False, "姓名不能为空"

        if "name" in data and not data["name"]:
            return False, "姓名不能为空"

        if "name" in data and len(data["name"]) > 100:
            return False, "姓名长度不能超过100个字符"

        if "phone" in data and data["phone"]:
            if len(data["phone"]) > 20:
                return False, "联系电话长度不能超过20个字符"

        if "id_card" in data and data["id_card"]:
            if len(data["id_card"]) > 18:
                return False, "身份证号长度不能超过18个字符"

        if "age" in data and data["age"] is not None:
            try:
                age = int(data["age"])
                if age < 0 or age > 150:
                    return False, "年龄必须在0-150之间"
            except (ValueError, TypeError):
                return False, "年龄必须是有效数字"

        return True, None

    def create_person(self, person_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        新增人员
        :param person_data: 人员信息字典
        :return: 业务结果字典
        """
        valid, msg = self._validate_person_data(person_data)
        if not valid:
            return {"success": False, "message": msg}

        success, result = self.person_dao.create(person_data)
        if success:
            return {
                "success": True,
                "message": f"人员 '{result.name}' 新增成功",
                "data": result.to_dict()
            }
        return {"success": False, "message": result}

    def get_person_by_id(self, person_id: int) -> Dict[str, Any]:
        """
        根据ID查询人员
        :param person_id: 人员编号
        :return: 业务结果字典
        """
        success, result = self.person_dao.get_by_id(person_id)
        if success:
            return {
                "success": True,
                "message": "查询成功",
                "data": result.to_dict()
            }
        return {"success": False, "message": result}

    def get_all_persons(self) -> Dict[str, Any]:
        """
        查询所有人员
        :return: 业务结果字典
        """
        success, result = self.person_dao.get_all()
        if success:
            return {
                "success": True,
                "message": f"共查询到 {len(result)} 位人员",
                "data": [p.to_dict() for p in result]
            }
        return {"success": False, "message": result}

    def update_person(self, person_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        修改人员信息
        :param person_id: 人员编号
        :param update_data: 更新数据字典
        :return: 业务结果字典
        """
        valid, msg = self._validate_person_data(update_data, is_update=True)
        if not valid:
            return {"success": False, "message": msg}

        success, result = self.person_dao.update(person_id, update_data)
        if success:
            return {
                "success": True,
                "message": f"人员 '{result.name}' 信息修改成功",
                "data": result.to_dict()
            }
        return {"success": False, "message": result}

    def delete_person(self, person_id: int) -> Dict[str, Any]:
        """
        删除人员
        :param person_id: 人员编号
        :return: 业务结果字典
        """
        success, result = self.person_dao.delete(person_id)
        if success:
            return {
                "success": True,
                "message": f"人员 '{result}' 删除成功"
            }
        return {"success": False, "message": result}

    def search_persons_by_name(self, name: str) -> Dict[str, Any]:
        """
        根据姓名搜索人员
        :param name: 姓名关键字
        :return: 业务结果字典
        """
        success, result = self.person_dao.search_by_name(name)
        if success:
            return {
                "success": True,
                "message": f"搜索到 {len(result)} 位匹配人员",
                "data": [p.to_dict() for p in result]
            }
        return {"success": False, "message": result}
