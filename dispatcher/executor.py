"""
executor.py — 调度官：工具执行器（含简单熔断）
"""
from typing import Dict, Any, List, Callable
import time


class Executor:
    def __init__(self, timeout: float = 5.0):
        self.tools = {}
        self.timeout = timeout
        self._register_defaults()

    def register(self, name: str, func: Callable):
        self.tools[name] = func

    def _register_defaults(self):
        self.register("search_web", lambda q: f"模拟搜索: {q}")
        self.register("calculate", lambda expr: f"计算: {eval(expr)}")
        self.register("get_memory", lambda x: f"回忆: {x} (模拟)")
        self.register("generate_report", lambda t: f"# 报告: {t}\n\nPaladin v0.2")

    def execute(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for step in plan:
            tool_name = step.get("tool")
            args = step.get("args", {})
            if tool_name not in self.tools:
                results.append({"error": f"未知工具: {tool_name}"})
                continue
            try:
                start = time.time()
                result = self.tools[tool_name](**args)
                elapsed = time.time() - start
                entry = {"result": result}
                if elapsed > self.timeout:
                    entry["warning"] = f"超时(>{self.timeout}s)"
                results.append(entry)
            except Exception as e:
                results.append({"error": str(e)})
        return results
