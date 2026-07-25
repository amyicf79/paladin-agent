"""
planner.py v0.4 — 指挥官：支持协议输出的上下文感知规划器

返回 ExecutionPlan（含 mode + steps），非裸列表
"""
import json
from typing import List, Dict, Any, Optional, Union
from .protocol import ExecutionPlan, PlanStep

SYSTEM_PROMPT = """你是任务规划专家。根据用户查询和执行历史，决定下一步。
**规则**：
1. 已有足够信息则返回 {"mode":"chain","steps":[],"reason":"已回答"}
2. 需调用工具时，输出 JSON：{"mode":"chain|parallel|branch","steps":[{"tool":"","args":{},"condition":""}]}
   - chain: 顺序执行（默认）
   - parallel: 互不依赖，可同时执行
   - branch: 带 condition，条件满足才执行
3. 可用工具：search_web, calculate, get_memory, generate_report"""


class Planner:
    def __init__(self, model_adapter=None):
        self.adapter = model_adapter

    def _format_history(self, history):
        if not history: return "无"
        lines = []
        for idx, item in enumerate(history, 1):
            p = json.dumps(item.get("plan", {}), ensure_ascii=False)
            r = json.dumps(item.get("results", []), ensure_ascii=False)
            lines.append(f"第{idx}轮 计划:{p} 结果:{r}")
        return "\n".join(lines)

    def plan(self, context: Union[str, Dict]) -> ExecutionPlan:
        if isinstance(context, str):
            context = {"query": context, "history": []}
        query = context.get("query", "")
        history = context.get("history", [])
        if not self.adapter:
            return ExecutionPlan()
        h = self._format_history(history)
        raw = "".join(self.adapter.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"查询：{query}\n历史：{h}\n输出JSON："}
        ]))
        try:
            if "```json" in raw: raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw: raw = raw.split("```")[1].split("```")[0]
            data = json.loads(raw.strip()) if raw.strip() else {}
            return ExecutionPlan(
                mode=data.get("mode", "chain"),
                steps=[PlanStep(**s) for s in data.get("steps", [])],
                reason=data.get("reason")
            )
        except:
            return ExecutionPlan()

    def is_complete(self, context: Dict) -> bool:
        history = context.get("history", [])
        if not history: return False
        return not history[-1].get("plan", {}).get("steps")

    def synthesize(self, context: Dict) -> str:
        query = context.get("query", "")
        if not self.adapter: return "完成。"
        h = self._format_history(context.get("history", []))
        return "".join(self.adapter.chat([
            {"role": "system", "content": "基于查询和执行结果生成最终回复。"},
            {"role": "user", "content": f"查询：{query}\n历史：{h}"}
        ]))
