"""
planner.py — 指挥官：思维链任务拆解

用户输入 → LLM拆解为 [{tool, args}] 计划
"""
import json, re
from typing import List, Dict, Any, Optional

SYSTEM_PROMPT = """你是一个任务规划专家。
将用户输入拆解为最多3个步骤的工具调用链。
输出严格为JSON数组：[{"tool":"工具名","args":{"参数":"值"}}]
可用工具：search_web, calculate, get_memory, generate_report
无工具可调用时返回 []"""


class Planner:
    def __init__(self, model_adapter=None):
        self.adapter = model_adapter

    def plan(self, user_query: str) -> List[Dict[str, Any]]:
        if not self.adapter:
            return []
        # 收集 generator 输出
        raw = "".join(self.adapter.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ]))
        # 提取 JSON
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            return json.loads(raw.strip()) if raw.strip() else []
        except:
            return []
