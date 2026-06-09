# -*- coding: utf-8 -*-
"""
任务数据访问层
封装任务新增、时间筛选查询、状态更新、任务删除方法
处理查询条件拼装、数据格式适配
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from src.db_model.base_model import get_db_session, Task


class TaskDAO:
    """
    任务数据访问对象
    仅做数据库读写操作，不处理业务逻辑
    """

    def __init__(self):
        pass

    def create(self, task_data: Dict[str, Any]) -> tuple:
        """
        新增任务
        :param task_data: 任务信息字典
        :return: (是否成功, 新增任务对象或错误信息)
        """
        session = get_db_session()
        try:
            task = Task(**task_data)
            session.add(task)
            session.commit()
            session.refresh(task)
            return True, task
        except Exception as e:
            session.rollback()
            return False, f"新增任务失败: {str(e)}"
        finally:
            session.close()

    def get_by_id(self, task_id: int) -> tuple:
        """
        根据ID查询单条任务
        :param task_id: 任务唯一编号
        :return: (是否成功, 任务对象或错误信息)
        """
        session = get_db_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                return True, task
            return False, f"未找到编号为 {task_id} 的任务"
        except Exception as e:
            return False, f"查询任务失败: {str(e)}"
        finally:
            session.close()

    def get_all(self) -> tuple:
        """
        查询所有任务列表
        :return: (是否成功, 任务列表或错误信息)
        """
        session = get_db_session()
        try:
            tasks = session.query(Task).order_by(Task.created_at.desc()).all()
            return True, tasks
        except Exception as e:
            return False, f"查询任务列表失败: {str(e)}"
        finally:
            session.close()

    def get_today_tasks(self) -> tuple:
        """
        查询当日任务
        :return: (是否成功, 任务列表或错误信息)
        """
        session = get_db_session()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            tasks = session.query(Task).filter(
                Task.start_time.like(f"{today}%")
            ).order_by(Task.created_at.desc()).all()
            return True, tasks
        except Exception as e:
            return False, f"查询当日任务失败: {str(e)}"
        finally:
            session.close()

    def get_by_status(self, status: str) -> tuple:
        """
        根据状态查询任务
        :param status: 任务状态
        :return: (是否成功, 任务列表或错误信息)
        """
        session = get_db_session()
        try:
            tasks = session.query(Task).filter(Task.status == status).order_by(Task.created_at.desc()).all()
            return True, tasks
        except Exception as e:
            return False, f"按状态查询任务失败: {str(e)}"
        finally:
            session.close()

    def update(self, task_id: int, update_data: Dict[str, Any]) -> tuple:
        """
        修改任务信息
        :param task_id: 任务唯一编号
        :param update_data: 要更新的字段字典
        :return: (是否成功, 更新后任务对象或错误信息)
        """
        session = get_db_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False, f"未找到编号为 {task_id} 的任务"

            for key, value in update_data.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            session.commit()
            session.refresh(task)
            return True, task
        except Exception as e:
            session.rollback()
            return False, f"修改任务失败: {str(e)}"
        finally:
            session.close()

    def delete(self, task_id: int) -> tuple:
        """
        删除任务
        :param task_id: 任务唯一编号
        :return: (是否成功, 删除的任务标题或错误信息)
        """
        session = get_db_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False, f"未找到编号为 {task_id} 的任务"

            title = task.title
            session.delete(task)
            session.commit()
            return True, title
        except Exception as e:
            session.rollback()
            return False, f"删除任务失败: {str(e)}"
        finally:
            session.close()