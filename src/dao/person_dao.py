# -*- coding: utf-8 -*-
"""
人员数据访问层
封装人员信息新增、单条查询、列表查询、修改、删除通用方法
承接Service层调用，转换业务数据与数据库存储格式
"""

from typing import List, Optional, Dict, Any
from src.db_model.base_model import get_db_session, Person


class PersonDAO:
    """
    人员数据访问对象
    仅做数据库读写操作，不处理业务逻辑
    """

    def __init__(self):
        pass

    def create(self, person_data: Dict[str, Any]) -> tuple:
        """
        新增人员信息
        :param person_data: 人员信息字典
        :return: (是否成功, 新增人员对象或错误信息)
        """
        session = get_db_session()
        try:
            person = Person(**person_data)
            session.add(person)
            session.commit()
            session.refresh(person)
            return True, person
        except Exception as e:
            session.rollback()
            return False, f"新增人员失败: {str(e)}"
        finally:
            session.close()

    def get_by_id(self, person_id: int) -> tuple:
        """
        根据ID查询单条人员信息
        :param person_id: 人员唯一编号
        :return: (是否成功, 人员对象或错误信息)
        """
        session = get_db_session()
        try:
            person = session.query(Person).filter(Person.id == person_id).first()
            if person:
                return True, person
            return False, f"未找到编号为 {person_id} 的人员"
        except Exception as e:
            return False, f"查询人员失败: {str(e)}"
        finally:
            session.close()

    def get_all(self) -> tuple:
        """
        查询所有人员信息列表
        :return: (是否成功, 人员列表或错误信息)
        """
        session = get_db_session()
        try:
            persons = session.query(Person).order_by(Person.created_at.desc()).all()
            return True, persons
        except Exception as e:
            return False, f"查询人员列表失败: {str(e)}"
        finally:
            session.close()

    def update(self, person_id: int, update_data: Dict[str, Any]) -> tuple:
        """
        修改人员信息
        :param person_id: 人员唯一编号
        :param update_data: 要更新的字段字典
        :return: (是否成功, 更新后人员对象或错误信息)
        """
        session = get_db_session()
        try:
            person = session.query(Person).filter(Person.id == person_id).first()
            if not person:
                return False, f"未找到编号为 {person_id} 的人员"

            for key, value in update_data.items():
                if hasattr(person, key):
                    setattr(person, key, value)

            session.commit()
            session.refresh(person)
            return True, person
        except Exception as e:
            session.rollback()
            return False, f"修改人员失败: {str(e)}"
        finally:
            session.close()

    def delete(self, person_id: int) -> tuple:
        """
        删除人员信息
        :param person_id: 人员唯一编号
        :return: (是否成功, 删除的人员姓名或错误信息)
        """
        session = get_db_session()
        try:
            person = session.query(Person).filter(Person.id == person_id).first()
            if not person:
                return False, f"未找到编号为 {person_id} 的人员"

            name = person.name
            session.delete(person)
            session.commit()
            return True, name
        except Exception as e:
            session.rollback()
            return False, f"删除人员失败: {str(e)}"
        finally:
            session.close()

    def search_by_name(self, name: str) -> tuple:
        """
        根据姓名模糊查询人员
        :param name: 姓名关键字
        :return: (是否成功, 人员列表或错误信息)
        """
        session = get_db_session()
        try:
            persons = session.query(Person).filter(Person.name.like(f"%{name}%")).all()
            return True, persons
        except Exception as e:
            return False, f"搜索人员失败: {str(e)}"
        finally:
            session.close()
