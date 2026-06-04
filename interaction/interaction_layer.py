# -*- coding: utf-8 -*-
"""
人机交互层
搭建控制台循环交互界面，接收用户自然语言输入
对接大模型接口，完成语义理解、行为意图判定
从对话文本中自动抽取业务参数
编写路由分发函数，根据识别结果匹配业务类型
接收底层处理结果，格式化中文反馈展示在控制台
不编写业务运算、数据存取逻辑
"""

import re
from typing import Dict, Any, Optional
from agent.person_agent import PersonAgent
from agent.task_agent import TaskAgent


class InteractionLayer:
    """
    人机交互层
    负责用户输入接收、意图识别、路由分发、结果展示
    """

    def __init__(self):
        self.person_agent = PersonAgent()
        self.task_agent = TaskAgent()
        self.running = False

    def _parse_intent(self, user_input: str) -> Dict[str, Any]:
        """
        解析用户输入意图（简化版语义识别）
        实际生产环境可对接大模型API进行意图识别
        :param user_input: 用户输入文本
        :return: 意图识别结果
        """
        text = user_input.strip().lower()

        # 退出指令
        if text in ["退出", "再见", "拜拜", "quit", "exit", "q"]:
            return {"intent": "exit", "params": {}}

        # 帮助指令
        if text in ["帮助", "help", "h", "?"]:
            return {"intent": "help", "params": {}}

        # 人员管理意图识别
        person_patterns = [
            (r"添加人员|新增人员|添加家人|新增家人|添加联系人", "person_create"),
            (r"查询人员|查看人员|人员列表|所有人员|列出人员", "person_list"),
            (r"查询人员\s*(\d+)|查看人员\s*(\d+)|人员详情\s*(\d+)", "person_get"),
            (r"修改人员\s*(\d+)|编辑人员\s*(\d+)", "person_update"),
            (r"删除人员\s*(\d+)|移除人员\s*(\d+)", "person_delete"),
            (r"搜索人员\s*(.+)|查找人员\s*(.+)|人员搜索\s*(.+)", "person_search"),
        ]

        for pattern, intent in person_patterns:
            match = re.search(pattern, text)
            if match:
                params = {}
                groups = match.groups()
                if groups:
                    if intent == "person_get":
                        params["person_id"] = int(groups[0] or groups[1] or groups[2])
                    elif intent == "person_update":
                        params["person_id"] = int(groups[0] or groups[1])
                    elif intent == "person_delete":
                        params["person_id"] = int(groups[0] or groups[1])
                    elif intent == "person_search":
                        params["name"] = (groups[0] or groups[1] or groups[2]).strip()
                return {"intent": intent, "params": params}

        # 任务管理意图识别
        task_patterns = [
            (r"添加任务|新增任务|创建任务|添加待办|新增待办", "task_create"),
            (r"查询任务|查看任务|任务列表|所有任务|列出任务", "task_list"),
            (r"今日任务|今天任务|今日待办", "task_today"),
            (r"查询任务\s*(\d+)|查看任务\s*(\d+)|任务详情\s*(\d+)", "task_get"),
            (r"修改任务\s*(\d+)|编辑任务\s*(\d+)", "task_update"),
            (r"删除任务\s*(\d+)|移除任务\s*(\d+)", "task_delete"),
            (r"完成任务\s*(\d+)|任务完成\s*(\d+)", "task_complete"),
            (r"待办任务|进行中的任务", "task_status_todo"),
            (r"已完成任务|完成的任务", "task_status_done"),
        ]

        for pattern, intent in task_patterns:
            match = re.search(pattern, text)
            if match:
                params = {}
                groups = match.groups()
                if groups:
                    if intent in ["task_get", "task_update", "task_delete", "task_complete"]:
                        params["task_id"] = int(groups[0] or groups[1])
                return {"intent": intent, "params": params}

        # 默认：无法识别意图
        return {"intent": "unknown", "params": {"original_input": user_input}}

    def _extract_person_params(self, user_input: str) -> Dict[str, Any]:
        """
        从用户输入中提取人员参数
        :param user_input: 用户输入
        :return: 提取的参数字典
        """
        params = {}

        # 提取姓名（支持 姓名:xxx 或 姓名：xxx，遇到下一个字段关键字或行尾停止）
        name_match = re.search(r"姓名[:：]\s*([^\s,，性别关系电话生日备注]+?)(?:\s+(?:性别|关系|电话|生日|备注)[:：]|$)", user_input)
        if name_match:
            params["name"] = name_match.group(1).strip()

        # 提取关系
        relation_match = re.search(r"关系[:：]\s*([^\s,，性别电话生日备注]+?)(?:\s+(?:性别|电话|生日|备注)[:：]|$)", user_input)
        if relation_match:
            params["relation_type"] = relation_match.group(1).strip()

        # 提取性别
        gender_match = re.search(r"性别[:：]\s*([^\s,，关系电话生日备注]+?)(?:\s+(?:关系|电话|生日|备注)[:：]|$)", user_input)
        if gender_match:
            params["gender"] = gender_match.group(1).strip()

        # 提取电话
        phone_match = re.search(r"电话[:：]\s*(\d+)(?:\s+(?:性别|关系|生日|备注)[:：]|$)", user_input)
        if phone_match:
            params["phone"] = phone_match.group(1).strip()

        # 提取出生日期
        birth_match = re.search(r"生日[:：]\s*(\d{4}-\d{2}-\d{2})(?:\s+(?:性别|关系|电话|备注)[:：]|$)", user_input)
        if birth_match:
            params["birth_date"] = birth_match.group(1).strip()

        # 提取备注
        remark_match = re.search(r"备注[:：]\s*(.+)$", user_input)
        if remark_match:
            params["remark"] = remark_match.group(1).strip()

        return params

    def _extract_task_params(self, user_input: str) -> Dict[str, Any]:
        """
        从用户输入中提取任务参数
        :param user_input: 用户输入
        :return: 提取的参数字典
        """
        params = {}

        # 提取标题（遇到下一个字段关键字或行尾停止）
        title_match = re.search(r"标题[:：]\s*([^\s,，优先级截止开始类型备注]+?)(?:\s+(?:优先级|截止|开始|类型|备注)[:：]|$)", user_input)
        if title_match:
            params["title"] = title_match.group(1).strip()
        else:
            # 尝试从整句话提取标题（简化处理）
            clean = re.sub(r"添加任务|新增任务|创建任务|[:：]", "", user_input).strip()
            if clean:
                params["title"] = clean

        # 提取优先级
        priority_match = re.search(r"优先级[:：]\s*(紧急|高|普通|低)(?:\s+(?:标题|截止|开始|类型|备注)[:：]|$)", user_input)
        if priority_match:
            params["priority"] = priority_match.group(1).strip()

        # 提取截止时间
        end_match = re.search(r"截止[:：]\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?)(?:\s+(?:标题|优先级|开始|类型|备注)[:：]|$)", user_input)
        if end_match:
            params["end_time"] = end_match.group(1).strip()

        # 提取开始时间
        start_match = re.search(r"开始[:：]\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?)(?:\s+(?:标题|优先级|截止|类型|备注)[:：]|$)", user_input)
        if start_match:
            params["start_time"] = start_match.group(1).strip()

        # 提取任务类型
        type_match = re.search(r"类型[:：]\s*([^\s,，优先级截止开始备注]+?)(?:\s+(?:标题|优先级|截止|开始|备注)[:：]|$)", user_input)
        if type_match:
            params["task_type"] = type_match.group(1).strip()

        # 提取备注
        remark_match = re.search(r"备注[:：]\s*(.+)$", user_input)
        if remark_match:
            params["remark"] = remark_match.group(1).strip()

        return params

    def _route_and_execute(self, intent_result: Dict[str, Any], user_input: str) -> str:
        """
        路由分发并执行对应业务
        :param intent_result: 意图识别结果
        :param user_input: 原始用户输入
        :return: 处理结果文本
        """
        intent = intent_result["intent"]
        params = intent_result["params"]

        # 退出
        if intent == "exit":
            self.running = False
            return "程序已退出，再见！"

        # 帮助
        if intent == "help":
            return self._get_help_text()

        # 人员管理路由
        if intent == "person_create":
            person_params = self._extract_person_params(user_input)
            if not person_params.get("name"):
                return "【提示】添加人员需要提供姓名，格式：添加人员 姓名:张三 关系:父亲 电话:13800138000"
            result = self.person_agent.create_person(person_params)
            return self._format_result(result)

        elif intent == "person_list":
            result = self.person_agent.list_persons()
            return self._format_person_list(result)

        elif intent == "person_get":
            person_id = params.get("person_id")
            if not person_id:
                return "【提示】查询人员需要提供人员编号，格式：查询人员 1"
            result = self.person_agent.get_person(person_id)
            return self._format_result(result)

        elif intent == "person_update":
            person_id = params.get("person_id")
            if not person_id:
                return "【提示】修改人员需要提供人员编号，格式：修改人员 1 电话:13900139000"
            update_params = self._extract_person_params(user_input)
            result = self.person_agent.update_person(person_id, update_params)
            return self._format_result(result)

        elif intent == "person_delete":
            person_id = params.get("person_id")
            if not person_id:
                return "【提示】删除人员需要提供人员编号，格式：删除人员 1"
            result = self.person_agent.delete_person(person_id)
            return self._format_result(result)

        elif intent == "person_search":
            name = params.get("name", "")
            if not name:
                name = self._extract_person_params(user_input).get("name", "")
            if not name:
                return "【提示】搜索人员需要提供姓名关键字，格式：搜索人员 张"
            result = self.person_agent.search_persons(name)
            return self._format_person_list(result)

        # 任务管理路由
        elif intent == "task_create":
            task_params = self._extract_task_params(user_input)
            if not task_params.get("title"):
                return "【提示】添加任务需要提供标题，格式：添加任务 标题:买牛奶 优先级:普通 截止:2025-01-01"
            result = self.task_agent.create_task(task_params)
            return self._format_result(result)

        elif intent == "task_list":
            result = self.task_agent.list_tasks()
            return self._format_task_list(result)

        elif intent == "task_today":
            result = self.task_agent.list_today_tasks()
            return self._format_task_list(result)

        elif intent == "task_get":
            task_id = params.get("task_id")
            if not task_id:
                return "【提示】查询任务需要提供任务编号，格式：查询任务 1"
            result = self.task_agent.get_task(task_id)
            return self._format_result(result)

        elif intent == "task_update":
            task_id = params.get("task_id")
            if not task_id:
                return "【提示】修改任务需要提供任务编号，格式：修改任务 1 状态:已完成"
            update_params = self._extract_task_params(user_input)
            result = self.task_agent.update_task(task_id, update_params)
            return self._format_result(result)

        elif intent == "task_delete":
            task_id = params.get("task_id")
            if not task_id:
                return "【提示】删除任务需要提供任务编号，格式：删除任务 1"
            result = self.task_agent.delete_task(task_id)
            return self._format_result(result)

        elif intent == "task_complete":
            task_id = params.get("task_id")
            if not task_id:
                return "【提示】完成任务需要提供任务编号，格式：完成任务 1"
            result = self.task_agent.complete_task(task_id)
            return self._format_result(result)

        elif intent == "task_status_todo":
            result = self.task_agent.list_tasks_by_status("待办")
            return self._format_task_list(result)

        elif intent == "task_status_done":
            result = self.task_agent.list_tasks_by_status("已完成")
            return self._format_task_list(result)

        # 未知意图
        return f"【提示】未能理解您的指令: '{user_input}'\n输入 '帮助' 查看可用指令列表。"

    def _format_result(self, result: Dict[str, Any]) -> str:
        """
        格式化单条结果
        :param result: 业务结果字典
        :return: 格式化文本
        """
        if not result.get("success"):
            return f"【失败】{result.get('message', '操作失败')}"

        msg = result.get("message", "操作成功")
        data = result.get("data")

        if data is None:
            return f"【成功】{msg}"

        if isinstance(data, dict):
            lines = [f"【成功】{msg}", "---"]
            for key, value in data.items():
                if value is not None:
                    lines.append(f"  {key}: {value}")
            return "\n".join(lines)

        return f"【成功】{msg}\n  数据: {data}"

    def _format_person_list(self, result: Dict[str, Any]) -> str:
        """
        格式化人员列表
        :param result: 业务结果字典
        :return: 格式化文本
        """
        if not result.get("success"):
            return f"【失败】{result.get('message', '查询失败')}"

        data = result.get("data", [])
        msg = result.get("message", "")

        if not data:
            return f"【提示】{msg}\n  暂无人员记录"

        lines = [f"【成功】{msg}", "=" * 60]
        lines.append(f"{'编号':<6}{'姓名':<10}{'关系':<10}{'电话':<15}{'紧急联系人':<10}")
        lines.append("-" * 60)

        for person in data:
            emergency = "是" if person.get("is_emergency_contact") else "否"
            lines.append(
                f"{str(person.get('id', '-')):<6}"
                f"{str(person.get('name', '-')):<10}"
                f"{str(person.get('relation_type', '-')):<10}"
                f"{str(person.get('phone', '-')):<15}"
                f"{emergency:<10}"
            )

        lines.append("=" * 60)
        return "\n".join(lines)

    def _format_task_list(self, result: Dict[str, Any]) -> str:
        """
        格式化任务列表
        :param result: 业务结果字典
        :return: 格式化文本
        """
        if not result.get("success"):
            return f"【失败】{result.get('message', '查询失败')}"

        data = result.get("data", [])
        msg = result.get("message", "")

        if not data:
            return f"【提示】{msg}\n  暂无任务记录"

        lines = [f"【成功】{msg}", "=" * 70]
        lines.append(f"{'编号':<6}{'标题':<20}{'优先级':<8}{'状态':<8}{'截止时间':<20}")
        lines.append("-" * 70)

        for task in data:
            end_time = task.get('end_time') or '-'
            lines.append(
                f"{str(task.get('id', '-')):<6}"
                f"{str(task.get('title', '-'))[:18]:<20}"
                f"{str(task.get('priority', '-')):<8}"
                f"{str(task.get('status', '-')):<8}"
                f"{str(end_time):<20}"
            )

        lines.append("=" * 70)
        return "\n".join(lines)

    def _get_help_text(self) -> str:
        """
        获取帮助文本
        :return: 帮助信息
        """
        return """
╔══════════════════════════════════════════════════════════════╗
║                    Personal Brain 帮助菜单                    ║
╠══════════════════════════════════════════════════════════════╣
║  【人员管理】                                                 ║
║    添加人员 姓名:张三 关系:父亲 电话:13800138000              ║
║    查询人员 [编号]                                            ║
║    人员列表 / 所有人员                                        ║
║    修改人员 [编号] [字段:新值]                                ║
║    删除人员 [编号]                                            ║
║    搜索人员 [姓名关键字]                                      ║
╠══════════════════════════════════════════════════════════════╣
║  【任务管理】                                                 ║
║    添加任务 标题:买牛奶 优先级:普通 截止:2025-01-01           ║
║    查询任务 [编号]                                            ║
║    任务列表 / 所有任务                                        ║
║    今日任务                                                   ║
║    修改任务 [编号] [字段:新值]                                ║
║    删除任务 [编号]                                            ║
║    完成任务 [编号]                                            ║
║    待办任务 / 已完成任务                                      ║
╠══════════════════════════════════════════════════════════════╣
║  【其他】                                                     ║
║    帮助 / help / ?  -- 显示本帮助菜单                        ║
║    退出 / quit / q   -- 退出程序                             ║
╚══════════════════════════════════════════════════════════════╝
""".strip()

    def start(self):
        """
        启动人机交互循环
        """
        self.running = True
        print("\n" + "=" * 60)
        print("     欢迎使用 Personal Brain 个人大脑事务管理系统")
        print("=" * 60)
        print("输入 '帮助' 查看可用指令，输入 '退出' 关闭程序\n")

        while self.running:
            try:
                user_input = input("\n🧠 您想做什么？> ").strip()
                if not user_input:
                    continue

                # 意图识别
                intent_result = self._parse_intent(user_input)

                # 路由分发并执行
                response = self._route_and_execute(intent_result, user_input)

                # 输出结果
                print(f"\n{response}")

            except KeyboardInterrupt:
                print("\n\n【提示】程序被中断，正在退出...")
                self.running = False
            except Exception as e:
                print(f"\n【错误】系统异常: {e}")
                import traceback
                traceback.print_exc()

        print("\n【系统】Personal Brain 已安全退出，再见！")
