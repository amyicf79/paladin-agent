"""
executor.py v0.9 — 调度官：接受协议输入，输出协议结果
                   chain 模式支持上下文传递（context_updates）
                   集成 Tool Synthesis：元操作 → 代码生成 → 热加载 → 执行
                   v0.9.3 新增: 工具生成后自动验证→修复→重试闭环
"""
from typing import Dict, Any, List, Callable, Optional
import time, concurrent.futures
from ..commander.protocol import ExecutionPlan, PlanStep, ExecutionResult
from ..codegen import CodeGenerator
from ..loader import ToolLoader
from ..validator import validate_tool
from ..repair import repair_tool


class Executor:
    def __init__(self, timeout: float = 5.0, tools_config=None, codegen_backend: str = "mock",
                 adapter=None):
        self.tools = {}
        self.timeout = timeout
        self.codegen = CodeGenerator(backend=codegen_backend)
        self.loader = ToolLoader()
        self._tool_metadata: Dict[str, Dict] = {}
        self.adapter = adapter
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
        """处理生成工具元操作：codegen → save → load → register → 记录元数据"""
        step = PlanStep(tool=f"codegen:{meta.target_name}")
        try:
            code = self.codegen.generate(meta)
            filepath = self.codegen.save_to_file(code, meta.target_name,
                                                  directory=str(self.loader.tool_dir))
            func = self.loader.load_tool(meta.target_name)
            self.register(meta.target_name, func)
            # v0.9.3: 记录生成工具的元数据供验证→修复闭环使用
            self._tool_metadata[meta.target_name] = {
                "code": code,
                "test_cases": self._infer_test_cases(meta.target_name, meta.description),
                "validated": False,
            }
            return ExecutionResult(
                step=step,
                result=f"✅ 工具 '{meta.target_name}' 已生成并注册",
                duration_ms=0,
                context_updates={f"tool_{meta.target_name}_ready": True}
            )
        except Exception as e:
            return ExecutionResult(step=step, error=f"工具生成失败: {e}")

    def _infer_test_cases(self, tool_name: str, description: str) -> list:
        """从描述中推断测试用例（可扩展）"""
        desc_lower = description.lower()
        if "标题" in description or "title" in desc_lower:
            return [{"name": "basic", "args": {"url": "https://example.com"}, "expected": "Example Domain"}]
        if "新闻" in description or "news" in desc_lower or "搜索" in description:
            return [{"name": "basic", "args": {"q": "latest news"}, "expected": "模拟搜索: latest news"}]
        if "计算" in description or "calc" in desc_lower or "数学" in description:
            return [{"name": "basic", "args": {"expr": "42+1"}, "expected": "计算: 43"}]
        if "文件" in description or "file" in desc_lower or "读" in description:
            return [{"name": "basic", "args": {"filepath": "/tmp/test.txt"}, "expected": None}]
        if "网络" in description or "网络" in description or "http" in desc_lower:
            return [{"name": "basic", "args": {"url": "https://httpbin.org/get"}, "expected": None}]
        if "时间" in description or "time" in desc_lower or "日期" in description:
            return [{"name": "basic", "args": {}, "expected": None}]
        return [{"name": "basic", "args": {}, "expected": None}]

    def _validate_and_repair(self, tool_name: str) -> bool:
        """验证→修复→重载闭环。返回 True 表示通过或已修复。"""
        meta = self._tool_metadata.get(tool_name)
        if not meta:
            return True
        if meta.get("validated"):
            return True
        code = meta["code"]
        test_cases = meta["test_cases"]
        report = validate_tool(tool_name, code, test_cases)
        adapter = getattr(self, "adapter", None)
        if report.all_passed:
            meta["validated"] = True
            # 生成工具验证通过也记录经验（不论是否有 adapter）
            try:
                from ..experience_store import Experience, get_store
                from datetime import datetime
                import hashlib
                store = get_store()
                store.add_experience(Experience(
                    tool_name=tool_name,
                    original_code=code,
                    repaired_code=code,
                    error_type="Passed" if adapter else "PassedInMock",
                    error_message=report.summary or "验证通过",
                    success=True,
                    timestamp=datetime.now().isoformat(),
                    problem_signature=hashlib.md5(
                        (tool_name + "passed").encode()
                    ).hexdigest()
                ))
            except Exception:
                pass
            return True
        # 修复（仅当有 adapter 时）
        adapter = getattr(self, "adapter", None)
        if adapter is None:
            meta["validated"] = True
            # v1.0.1: 无 adapter 时也记录验证失败经验
            try:
                from ..experience_store import Experience, get_store
                from datetime import datetime
                import hashlib
                store = get_store()
                store.add_experience(Experience(
                    tool_name=tool_name,
                    original_code=code,
                    repaired_code=code,
                    error_type="ValidationError",
                    error_message=report.summary or "验证失败（无修复）",
                    success=False,
                    timestamp=datetime.now().isoformat(),
                    problem_signature=hashlib.md5(
                        (tool_name + (report.summary or "")).encode()
                    ).hexdigest()
                ))
            except Exception:
                pass
            return False
        result = repair_tool(tool_name, code, report, adapter)
        if result.success and result.repaired_code:
            # 重新加载修复后的代码
            try:
                from ..loader import load_tool_from_code
                func = load_tool_from_code(result.repaired_code, tool_name)
                self.tools[tool_name] = func
                meta["code"] = result.repaired_code
                meta["validated"] = True
                # v1.0.1: 记录修复经验
                try:
                    from ..experience_store import Experience, get_store
                    from datetime import datetime
                    import hashlib
                    store = get_store()
                    store.add_experience(Experience(
                        tool_name=tool_name,
                        original_code=code,
                        repaired_code=result.repaired_code,
                        error_type="ValidationError",
                        error_message=report.summary or "",
                        timestamp=datetime.now().isoformat(),
                        problem_signature=hashlib.md5(
                            (tool_name + (report.summary or "")).encode()
                        ).hexdigest()
                    ))
                except Exception:
                    pass  # 经验记录失败不影响主流程
                return True
            except Exception:
                pass
        meta["validated"] = True
        return False

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
        finally:
            # v0.9.3: 生成工具首次执行后自动验证→修复闭环
            if name in self._tool_metadata:
                self._validate_and_repair(name)

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
