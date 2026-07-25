"""
executor.py v0.4 — 调度官：接受协议输入，输出协议结果
"""
from typing import Dict, Any, List, Callable
import time, concurrent.futures
from ..commander.protocol import ExecutionPlan, PlanStep, ExecutionResult


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

    def execute(self, plan: ExecutionPlan) -> List[ExecutionResult]:
        mode = plan.mode
        if mode == "chain":
            return self._chain(plan.steps)
        elif mode == "parallel":
            return self._parallel(plan.steps)
        elif mode == "branch":
            return self._branch(plan.steps)
        return self._chain(plan.steps)

    def _run_step(self, step: PlanStep) -> ExecutionResult:
        name = step.tool
        args = step.args or {}
        if name not in self.tools:
            return ExecutionResult(step=step, error=f"未知工具: {name}")
        try:
            start = time.time()
            result = self.tools[name](**args)
            elapsed = time.time() - start
            return ExecutionResult(step=step, result=result, duration_ms=elapsed * 1000)
        except Exception as e:
            return ExecutionResult(step=step, error=str(e))

    def _chain(self, steps: List[PlanStep]) -> List[ExecutionResult]:
        return [self._run_step(s) for s in steps]

    def _parallel(self, steps: List[PlanStep]) -> List[ExecutionResult]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(steps)) as pool:
            return list(pool.map(self._run_step, steps))

    def _branch(self, steps: List[PlanStep]) -> List[ExecutionResult]:
        results = []
        for s in steps:
            if s.condition and results:
                last = results[-1].result or ""
                if s.condition not in str(last):
                    results.append(ExecutionResult(step=s, result="skipped"))
                    continue
            results.append(self._run_step(s))
        return results
