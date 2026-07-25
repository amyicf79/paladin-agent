"""
planner.py v0.8 — 指挥官：支持协议输出的上下文感知规划器
                   v0.8 扩展: mock 模式工具缺位检测 → 自动触发工具合成

返回 ExecutionPlan（含 mode + steps + meta_actions），非裸列表
"""
import json
from typing import List, Dict, Any, Optional, Set, Union, Tuple
from dataclasses import asdict
from .protocol import ExecutionPlan, PlanStep, MetaAction

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

    def plan(self, context: Union[str, Dict], tool_registry: Optional[Set[str]] = None) -> ExecutionPlan:
        if isinstance(context, str):
            context = {"query": context, "history": []}
        query = context.get("query", "")
        history = context.get("history", [])

        # Mock 模式：工具缺位检测 + 自主生成
        if not self.adapter and tool_registry is not None:
            return self._mock_plan(query, tool_registry)

        # Real LLM 模式（原逻辑）
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

    def _mock_plan(self, query: str, tool_registry: Set[str]) -> ExecutionPlan:
        """Mock 模式：解析用户意图，检测工具缺位，自动生成 MetaAction"""
        tool_name, description = self._parse_tool_intent(query)
        if tool_name is None:
            return ExecutionPlan()  # 匹配不到任何已知模式

        meta_actions = []
        steps = []

        if tool_name not in tool_registry:
            # 工具不存在 → 构造 MetaAction 触发合成
            meta_actions.append(MetaAction(
                action_type="generate_tool",
                description=description,
                target_name=tool_name,
            ))

        # 构造一个占位 step（工具合成后会被 executor 执行）
        default_args = self._infer_args(tool_name, query)
        steps.append(PlanStep(tool=tool_name, args=default_args))

        return ExecutionPlan(
            mode="chain",
            steps=steps,
            meta_actions=meta_actions,
            reason=f"检测到工具 '{tool_name}' {'不存在，已触发合成' if meta_actions else '已存在，直接执行'}",
        )

    @staticmethod
    def _parse_tool_intent(query: str) -> Tuple[Optional[str], Optional[str]]:
        """关键词→工具名映射（零依赖，纯字符串匹配）"""
        q = query.lower()
        if "提取" in q and "标题" in q:
            return ("extract_title", "从 URL 提取标题")
        if "搜索" in q and "新闻" in q:
            return ("search_news", "搜索相关新闻")
        if "搜索" in q:
            return ("search_web", "搜索信息")
        if "计算" in q:
            return ("calculate", "执行数学计算")
        if ("读" in q or "文件" in q) and ("内容" in q or "读" in q):
            return ("read_file", "读取文件内容")
        return (None, None)

    @staticmethod
    def _infer_args(tool_name: str, query: str) -> Dict[str, Any]:
        """根据工具名和 query 推断默认参数"""
        if tool_name == "extract_title":
            return {"url": "https://www.python.org"}
        if tool_name in ("search_web", "search_news"):
            # 从 query 中提取搜索关键词（去掉动词）
            q = query
            for kw in ["搜索", "新闻", "关于", "的"]:
                q = q.replace(kw, "")
            return {"q": q.strip() or query}
        if tool_name == "calculate":
            return {"expr": query}
        if tool_name == "read_file":
            return {"filepath": "/tmp/data.txt"}
        return {}

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
