"""
executor.py v0.8 — 调度官：接受协议输入，输出协议结果
                   chain 模式支持上下文传递（context_updates）
                   集成 Tool Synthesis：元操作 → 代码生成 → 热加载 → 执行
"""
from typing import Dict, Any, List, Callable, Optional
import time, concurrent.futures
from ..commander.protocol import ExecutionPlan, PlanStep, ExecutionResult
from ..codegen import CodeGenerator
from ..loader import ToolLoader


class Executor:
    def __init__(self, timeout: float = 5.0, tools_config=None, codegen_backend: str = "mock"):
        self.tools = {}
        self.timeout = timeout
        self.codegen = CodeGenerator(backend=codegen_backend)
        self.loader = ToolLoader()
        self._register_defaults(tools_config)

    def register(self, name: str, func: Callable):
        self.tools[name] = func

    def _register_defaults(self, tools_config=None):
        # (tool_name → config attribute name, callable)
        # 所有工具统一接受 **kwargs 以兼容上下文注入
        all_tools = {
            "search_web":       ("enable_search",
                                 lambda q, **kw: (f"模拟搜索: {q}", {"search_result": f"{q}"})),
            "calculate":        ("enable_calculate",
                                 lambda expr, **kw: f"计算: {eval(expr)}"),
            "get_memory":       ("enable_memory",
                                 lambda x, **kw: f"回忆: {x} (模拟)"),
            "generate_report":  ("enable_report",
                                 lambda title="", **kw: f"# 报告: {title}\n\nPaladin v0.8"),
        }

        for name, (cfg_key, func) in all_tools.items():
            if tools_config is not None:
                enabled = getattr(tools_config, cfg_key, True)
                if not enabled:
                    continue
            self.register(name, func)

    def execute(self, plan: ExecutionPlan) -> List[ExecutionResult]:
        """执行计划：先处理元操作（工具生成），再按模式执行步骤"""
        meta_results = []

        # 1) 处理元操作：生成并加载新工具
        if plan.meta_actions:
            for meta in plan.meta_actions:
                if meta.action_type == "generate_tool":
                    result = self._handle_generate_tool(meta)
                    meta_results.append(result)
                else:
                    meta_results.append(
                        ExecutionResult(step=PlanStep(tool="meta"),
                                        error=f"不支持的操作类型: {meta.action_type}")
                    )

        # 2) 按模式执行步骤
        mode = plan.mode
        if mode == "chain":
            step_results = self._chain(plan.steps)
        elif mode == "parallel":
            step_results = self._parallel(plan.steps)
        elif mode == "branch":
            step_results = self._branch(plan.steps)
        else:
            step_results = self._chain(plan.steps)

        return meta_results + step_results

    def _handle_generate_tool(self, meta) -> ExecutionResult:
        """处理生成工具元操作：codegen → save → load → register"""
        step = PlanStep(tool=f"codegen:{meta.target_name}")
        try:
            code = self.codegen.generate(meta)
            filepath = self.codegen.save_to_file(code, meta.target_name,
                                                  directory=str(self.loader.tool_dir))
            func = self.loader.load_tool(meta.target_name)
            self.register(meta.target_name, func)
            return ExecutionResult(
                step=step,
                result=f"✅ 工具 '{meta.target_name}' 已生成并注册",
                duration_ms=0,
                context_updates={f"tool_{meta.target_name}_ready": True}
            )
        except Exception as e:
            return ExecutionResult(step=step, error=f"工具生成失败: {e}")

    def should_continue(self, results: List[ExecutionResult]) -> bool:
        """判断是否要继续下一轮规划"""
        for r in results:
            if r.error:
                return True  # 有错误，可重试
        return bool(results)  # 有结果则继续

    def _run_step(self, step: PlanStep, context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """执行单步，context 为 chain 模式累积的上下文（key 来自上一步 context_updates）

        工具返回值约定：
        - 普通值 → 直接作为 result
        - (result, {k:v,...}) 元组 → 拆分为 result + context_updates
        """
        name = step.tool
        args = dict(step.args or {})  # 浅拷贝，不修改原始 PlanStep
        if context:
            # 1) 解析 $key 变量引用（如 args: {"q": "$search_result"} → 从 context 取值）
            for k, v in list(args.items()):
                if isinstance(v, str) and v.startswith("$") and v[1:] in context:
                    args[k] = context[v[1:]]
            # 2) 将上下文作为额外 kwargs 注入（工具 lambda 通过 **kw 吸收）
            for k, v in context.items():
                if k not in args:
                    args[k] = v
        if name not in self.tools:
            return ExecutionResult(step=step, error=f"未知工具: {name}")
        try:
            start = time.time()
            raw = self.tools[name](**args)
            elapsed = time.time() - start

            # 支持工具返回 (result, context_updates) 元组
            ctx_updates: Dict[str, Any] = {}
            if isinstance(raw, tuple) and len(raw) == 2 and isinstance(raw[1], dict):
                result, ctx_updates = raw
            else:
                result = raw

            return ExecutionResult(
                step=step, result=result,
                duration_ms=elapsed * 1000,
                context_updates=ctx_updates,
            )
        except Exception as e:
            return ExecutionResult(step=step, error=str(e))

    def _chain(self, steps: List[PlanStep]) -> List[ExecutionResult]:
        """顺序执行，上一步的 context_updates 作为下一步的额外参数"""
        results = []
        ctx: Dict[str, Any] = {}
        for s in steps:
            res = self._run_step(s, context=ctx)
            results.append(res)
            if res.context_updates:
                ctx.update(res.context_updates)
        return results

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
