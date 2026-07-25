"""
executor.py v0.4 — 调度官：支持 chain / parallel / branch 三种执行模式

- chain（链式）：A → B → C，顺序执行（默认）
- parallel（并行）：同时调用多个工具
- branch（条件分支）：根据上一步结果决定下一步调什么
"""
from typing import Dict, Any, List, Callable, Optional
import time, concurrent.futures


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
        self.register("generate_report", lambda t: f"# 报告: {t}\n\nPaladin v0.4")

    def execute(self, plan: List[Dict[str, Any]], mode: str = "chain") -> List[Dict[str, Any]]:
        if mode == "chain":
            return self._execute_chain(plan)
        elif mode == "parallel":
            return self._execute_parallel(plan)
        elif mode == "branch":
            return self._execute_branch(plan)
        return self._execute_chain(plan)

    def _run_step(self, step: Dict) -> Dict:
        tool_name = step.get("tool")
        args = step.get("args", {})
        if tool_name not in self.tools:
            return {"error": f"未知工具: {tool_name}"}
        try:
            start = time.time()
            result = self.tools[tool_name](**args)
            elapsed = time.time() - start
            entry = {"result": result, "tool": tool_name}
            if elapsed > self.timeout:
                entry["warning"] = f"超时(>{self.timeout}s)"
            return entry
        except Exception as e:
            return {"error": str(e), "tool": tool_name}

    def _execute_chain(self, plan: List[Dict]) -> List[Dict]:
        return [self._run_step(s) for s in plan]

    def _execute_parallel(self, plan: List[Dict]) -> List[Dict]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(plan)) as pool:
            return list(pool.map(self._run_step, plan))

    def _execute_branch(self, plan: List[Dict]) -> List[Dict]:
        """条件分支：上一步结果可影响后续步骤"""
        results = []
        for step in plan:
            cond = step.get("condition")
            if cond and results:
                last = results[-1].get("result", "")
                if cond not in str(last):
                    results.append({"skipped": f"条件不满足: {cond}", "tool": step.get("tool")})
                    continue
            results.append(self._run_step(step))
        return results
