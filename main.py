# -*- coding: utf-8 -*-
"""
程序统一启动入口
依次初始化数据库模型、事件总线、各层级模块
启动人机交互循环程序
统一捕获全局异常，保障程序平稳运行
"""

import sys
import os

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db_model.base_model import init_database
from event_bus import event_bus
from interaction.interaction_layer import InteractionLayer


def initialize_system():
    """
    系统初始化
    按顺序初始化：数据库模型 -> 事件总线 -> 各层级模块
    """
    print("=" * 60)
    print("     Personal Brain 个人大脑事务管理系统 - 启动中")
    print("=" * 60)

    # 1. 初始化数据库基础模型层
    print("\n【初始化】正在初始化数据库...")
    try:
        init_database()
        print("【初始化】数据库初始化完成 ✓")
    except Exception as e:
        print(f"【错误】数据库初始化失败: {e}")
        return False

    # 2. 初始化事件总线（已在导入时创建单例，此处确认状态）
    print("\n【初始化】正在初始化事件总线...")
    try:
        print(f"【初始化】事件总线已就绪，当前订阅事件: {event_bus.get_subscribed_events()}")
        print("【初始化】事件总线初始化完成 ✓")
    except Exception as e:
        print(f"【错误】事件总线初始化失败: {e}")
        return False

    # 3. 加载各层级模块
    print("\n【初始化】正在加载各层级模块...")
    try:
        # 导入并初始化各层级（延迟导入确保路径正确）
        from dao.person_dao import PersonDAO
        from dao.task_dao import TaskDAO
        from service.person_service import PersonService
        from service.task_service import TaskService
        from agent.person_agent import PersonAgent
        from agent.task_agent import TaskAgent

        # 创建各层级实例（建立调用链）
        person_dao = PersonDAO()
        task_dao = TaskDAO()
        person_service = PersonService()
        task_service = TaskService()
        person_agent = PersonAgent()
        task_agent = TaskAgent()

        print("【初始化】DAO数据访问层加载完成 ✓")
        print("【初始化】Service业务服务层加载完成 ✓")
        print("【初始化】Agent智能代理层加载完成 ✓")
        print("【初始化】人机交互层加载完成 ✓")
    except Exception as e:
        print(f"【错误】模块加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("     系统初始化完成，所有模块就绪")
    print("=" * 60)
    return True


def main():
    """
    主程序入口
    """
    try:
        # 系统初始化
        if not initialize_system():
            print("\n【错误】系统初始化失败，程序退出")
            sys.exit(1)

        # 启动人机交互层
        print("\n【系统】正在启动人机交互界面...\n")
        interaction = InteractionLayer()
        interaction.start()

    except KeyboardInterrupt:
        print("\n\n【系统】收到中断信号，程序退出")
    except Exception as e:
        print(f"\n【严重错误】程序运行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("\n【系统】Personal Brain 已关闭")


if __name__ == "__main__":
    main()
