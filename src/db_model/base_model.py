# -*- coding: utf-8 -*-
"""
数据库基础模型层
定义全局统一 BaseModel 基础父类，包含人员表和任务表结构
仅做模型定义与库连接，不处理业务逻辑
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import os

# 数据库文件路径
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "brain_data.db")

# 确保数据目录存在
os.makedirs(DB_DIR, exist_ok=True)

# 创建数据库引擎
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

# 创建会话工厂
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# 声明基类
Base = declarative_base()


class BaseModel(Base):
    """
    全局统一基础父类
    所有业务数据表强制继承该基类
    """
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True, comment="唯一编号")
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")


class Person(BaseModel):
    """
    人员信息数据表
    """
    __tablename__ = "person"

    name = Column(String(100), nullable=False, comment="姓名")
    relation_type = Column(String(50), nullable=True, comment="关系类型")
    gender = Column(String(10), nullable=True, comment="性别")
    birth_date = Column(String(20), nullable=True, comment="出生日期")
    age = Column(Integer, nullable=True, comment="年龄")
    phone = Column(String(20), nullable=True, comment="联系电话")
    id_card = Column(String(18), nullable=True, comment="身份证号")
    household_address = Column(Text, nullable=True, comment="户籍地址")
    work_unit = Column(String(200), nullable=True, comment="工作单位")
    position = Column(String(100), nullable=True, comment="职务")
    is_emergency_contact = Column(Boolean, default=False, comment="是否紧急联系人")
    remark = Column(Text, nullable=True, comment="备注")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "relation_type": self.relation_type,
            "gender": self.gender,
            "birth_date": self.birth_date,
            "age": self.age,
            "phone": self.phone,
            "id_card": self.id_card,
            "household_address": self.household_address,
            "work_unit": self.work_unit,
            "position": self.position,
            "is_emergency_contact": self.is_emergency_contact,
            "remark": self.remark,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }


class Task(BaseModel):
    """
    任务提醒数据表
    """
    __tablename__ = "task"

    title = Column(String(200), nullable=False, comment="任务标题")
    task_type = Column(String(50), nullable=True, comment="任务类型")
    priority = Column(String(20), default="普通", comment="优先级")
    start_time = Column(String(20), nullable=True, comment="开始时间")
    end_time = Column(String(20), nullable=True, comment="截止时间")
    remind_before = Column(Integer, default=0, comment="提前提醒时长(分钟)")
    repeat_cycle = Column(String(50), nullable=True, comment="重复周期")
    status = Column(String(20), default="待办", comment="任务状态")
    remark = Column(Text, nullable=True, comment="任务备注")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "task_type": self.task_type,
            "priority": self.priority,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "remind_before": self.remind_before,
            "repeat_cycle": self.repeat_cycle,
            "status": self.status,
            "remark": self.remark,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }


def init_database():
    """
    初始化数据库，自动创建所有数据表
    """
    Base.metadata.create_all(bind=engine)
    print("【数据库】数据表初始化完成")


def get_db_session():
    """
    获取数据库会话
    """
    return SessionLocal()