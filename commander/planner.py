"""
planner.py v0.3 — 指挥官：支持 ReAct 循环的上下文感知规划器

- plan(context) → 接受查询+历史，输出下一步计划
- is_complete(context) → 判断任务是否完成
- synthesize(context) → 生成最终回复
"""
import json
from typing import List, Dict, Any, Optional, Union

SYSTEM_PROMPT = """你是一个任务规划专家。
根据用户查询和已执行步骤的历史，决定下一步要调用的工具。

**规则**：
1. 如果已有足够信息可回答用户，返回 []
2. 如需调用工具，输出 JSON：[{"tool":"工具名","args":{"参数":"值"}}]
3. 可用工具：search_web, calculate, get_memory, generate_report
4. 每次只输出当前这一步的计划（最多2步）"""


class Planner:
    def __init__(self, model_adapter=None):
        self.adapter = model_adapter

    def _format_history(self, history: List[Dict]) -> str:
        if not history:
            return "（暂无）"
        lines = []
        for idx, item in enumerate(history, 1):
            p = json.dumps(item.get("plan", []), ensure_ascii=False)
            r = json.dumps(item.get("results", []), ensure_ascii=False)
            lines.append(f"第{idx}轮 计划:{p} 结果:{r}")
        return "\n".join(lines)

    def plan(self, context: Union[str, Dict]) -> List[Dict]:
        if isinstance(context, str):
            context = {"query": context, "history": []}
        query = context.get("query", "")
        history = context.get("history", [])
        if not self.adapter:
            return []
        history_str = self._format_history(history)
        prompt = f"用户查询：{query}\n\n执行历史：\n{history_str}\n\n输出下一步计划（JSON）："
        raw = "".join(self.adapter.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]))
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            return json.loads(raw.strip()) if raw.strip() else []
        except:
            return []

    def is_complete(self, context: Dict) -> bool:
        history = context.get("history", [])
        if not history:
            return False
        last = history[-1]
        if not last.get("plan"):
            return True
        return False

    def synthesize(self, context: Dict) -> str:
        query = context.get("query", "")
        if not self.adapter:
            return "完成。"
        history_str = self._format_history(context.get("history", []))
        raw = "".join(self.adapter.chat([
            {"role": "system", "content": "基于用户查询和执行结果，生成最终回复。"},
            {"role": "user", "content": f"查询：{query}\n历史：{history_str}\n请回复。"}
        ]))
        return raw
