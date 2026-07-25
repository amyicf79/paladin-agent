"""
planner.py v0.4 — 指挥官：支持协议输出的上下文感知规划器

返回 ExecutionPlan（含 mode + steps），非裸列表
"""
import json
from typing import List, Dict, Any, Optional, Union
from dataclasses import asdict
from .protocol import ExecutionPlan, PlanStep

SYSTEM_PROMPT = """你是任务规划专家。根据用户查询和执行历史，自主选择执行策略并生成计划。

**规则**：
1. 已有足够信息则输出 {"mode":"chain","steps":[],"reason":"已回答"}
2. 需调用工具时，分析任务特征自主选择模式：
   - parallel: 步骤间无依赖 → 并行执行（推荐搜索+计算等独立任务）
   - chain: 步骤有依赖 → 顺序执行（每步依赖上一步结果）
   - branch: 需要条件判断 → 带condition过滤
3. 输出格式严格 JSON：{"mode":"chain|parallel|branch","steps":[{"tool":"","args":{},"condition":""}],"reason":"选择理由"}
4. 可用工具：search_web, calculate, get_memory, generate_report
5. 根据执行历史调整策略：如果上轮结果不理想，换一种模式重试"""


class Planner:
    def __init__(self, model_adapter=None, backend: str = "mock"):
        self.adapter = model_adapter
        self.backend = backend

    def _format_history(self, history):
        if not history: return "无"
        lines = []
        for idx, item in enumerate(history, 1):
            plan = item.get("plan", ExecutionPlan())
            results = item.get("results", [])
            p = json.dumps(plan.__dict__ if hasattr(plan, '__dict__') else plan, ensure_ascii=False, default=str)
            r = json.dumps([asdict(r) if hasattr(r, '__dict__') else r for r in results], ensure_ascii=False, default=str)
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
        plan = history[-1].get("plan")
        if isinstance(plan, ExecutionPlan):
            return not plan.steps
        if isinstance(plan, dict):
            return not plan.get("steps")
        return False

    def synthesize(self, context: Dict) -> str:
        query = context.get("query", "")
        shared = context.get("shared", {})
        if not self.adapter: return "完成。"
        h = self._format_history(context.get("history", []))
        extra = f"\n累积上下文：{json.dumps(shared, ensure_ascii=False)}" if shared else ""
        return "".join(self.adapter.chat([
            {"role": "system", "content": "基于查询和执行结果生成最终回复。"},
            {"role": "user", "content": f"查询：{query}\n历史：{h}{extra}"}
        ]))
