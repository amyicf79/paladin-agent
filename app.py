"""
app.py — Paladin 应用入口

指挥官(Planner) + 调度官(Executor) + 三篱笆(Cache/Router/Watch)

用法：
    python app.py "查询今天的天气并生成报告"
"""
import sys
import shutil
import time
from typing import Dict, Any, List
from paladin.models.cache import cache
from paladin.models.router import ModelRouter
from paladin.models.watch import CostWatch
from paladin.adapters.deepseek import DeepSeekAdapter
from paladin.commander import Planner
from paladin.dispatcher import Executor
from paladin.commander.protocol import ExecutionPlan, PlanStep, ExecutionResult


class Paladin:
    def __init__(self):
        self.adapter = DeepSeekAdapter()
        self.planner = Planner(self.adapter)
        self.executor = Executor()
        self.router = ModelRouter()
        self.watch = CostWatch()

    def run(self, query: str, max_iterations: int = 3) -> str:
        context = {"query": query, "history": []}
        for i in range(max_iterations):
            plan = self.planner.plan(context)
            if not plan:
                break
            results = self.executor.execute(plan)
            context["history"].append({"plan": plan, "results": results})
            if self.planner.is_complete(context):
                break
        return self.planner.synthesize(context)

    # ════════════════════════════════════════════════════════════
    # v0.6 — 内置演示靶场（零依赖终端可视化）
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def demo(auto: bool = False):
        """运行内置 3 个演示场景，展示 v0.6 的自主编排能力

        Args:
            auto: True 时跳过 Enter 等待，直接连续播放（适合测试/自动化场景）
        """
        scenarios = [
            {
                "name": "场景 1: 多步推理 (Chain)",
                "query": "计算 25 * 4 + 10，然后告诉我结果是否大于 50。",
                "desc": "Planner 选择 chain 模式，先算乘法，再比较。",
                "mode": "chain",
                "steps": [
                    {"tool": "calculate", "args": {"expr": "25 * 4"}},
                    {"tool": "calculate", "args": {"expr": "100 + 10"}},
                    {"tool": "calculate", "args": {"expr": "110 > 50"}},
                ],
            },
            {
                "name": "场景 2: 并行信息检索 (Parallel)",
                "query": "搜索 'Python 3.11 新特性' 和 'Gitee 2026 趋势'。",
                "desc": "Planner 选择 parallel 模式，同时调用两个 search_web。",
                "mode": "parallel",
                "steps": [
                    {"tool": "search_web", "args": {"q": "Python 3.11 新特性"}},
                    {"tool": "search_web", "args": {"q": "Gitee 2026 趋势"}},
                ],
            },
            {
                "name": "场景 3: 条件分支 (Branch)",
                "query": "如果 3 大于 5，就计算 10/2，否则生成一个报告叫'默认方案'。",
                "desc": "Planner 选择 branch 模式，条件不满足时跳过计算步。",
                "mode": "branch",
                "steps": [
                    {"tool": "calculate", "args": {"expr": "3 > 5"}},
                    {"tool": "calculate", "args": {"expr": "10 / 2"}, "condition": "True"},
                    {"tool": "generate_report", "args": {"title": "默认方案"}},
                ],
            },
        ]

        term_width = min(shutil.get_terminal_size().columns, 100)
        print("\033[95m" + "=" * term_width + "\033[0m")
        print("\033[1m  ⚔️  Paladin v0.6 演示靶场 (零依赖终端可视化)\033[0m")
        print("  展示: 多步推理 / 并行检索 / 条件分支\n")

        for idx, sc in enumerate(scenarios, 1):
            if not auto:
                input(f"\033[92m  按 Enter 执行 {sc['name']}\033[0m")
            print(f"\n\033[94m  📌 {sc['name']}\033[0m")
            print(f"     {sc['desc']}")
            print("     " + "-" * 40)
            result = Paladin._run_demo(sc["query"], sc["mode"], sc["steps"])
            Paladin._render_tree(sc["query"], result, term_width)
            print("\n" + "─" * term_width)

        print(f"\n\033[95m  {'=' * (term_width - 4)}\033[0m")
        print("\033[95m  ✅ 演示完成。Planner 自主决策能力已就绪。\033[0m")

    @staticmethod
    def _run_demo(query: str, mode: str, step_dicts: List[Dict]) -> Dict[str, Any]:
        """用硬编码计划执行单场景（绕过 LLM 适配器依赖）"""
        executor = Executor()
        steps = [PlanStep(**s) for s in step_dicts]
        plan = ExecutionPlan(mode=mode, steps=steps, reason=f"Demo: {mode} mode")
        results = executor.execute(plan)
        return {"history": [{"plan": plan, "results": results}], "final": f"✅ {mode} 模式演示完成。"}

    @staticmethod
    def _render_tree(query: str, result: Dict[str, Any], term_width: int = 80):
        """零依赖终端树形渲染器 (ANSI 颜色码 + Unicode 框线)"""
        history = result.get("history", [])
        final = result.get("final", "")

        # 1. 用户查询
        print(f"  \033[1m💬 用户: \033[0m{query}")
        print("  \033[90m" + "─" * term_width + "\033[0m")

        # 2. 遍历历史绘制树
        for idx, item in enumerate(history):
            plan: ExecutionPlan = item["plan"]
            results: List[ExecutionResult] = item["results"]

            print(f"  \033[93m├── [第 {idx+1} 轮] 模式: {plan.mode.upper()}\033[0m")

            for step_idx, res in enumerate(results):
                is_last = step_idx == len(results) - 1
                prefix = "  │   " if not is_last else "      "
                connector = "└──" if is_last else "├──"

                tool_name = res.step.tool
                print(f"  {prefix}{connector} \033[94m工具\033[0m: {tool_name}")

                if res.step.args:
                    args_str = ", ".join(f"{k}={v}" for k, v in res.step.args.items())
                    print(f"  {prefix}    \033[90m参数\033[0m: {args_str}")

                # 结果 / 错误 / 跳过
                if res.error:
                    status = f"\033[91m❌ 错误: {res.error}\033[0m"
                elif hasattr(res, 'result') and res.result == "skipped":
                    status = f"\033[93m⏭️  跳过 (条件不满足)\033[0m"
                else:
                    r = str(res.result)
                    if len(r) > 60:
                        r = r[:60] + "..."
                    status = f"\033[92m✅ {r}\033[0m"

                print(f"  {prefix}    \033[90m耗时\033[0m: {res.duration_ms:.1f}ms")
                print(f"  {prefix}    {status}")

        # 3. 最终答案
        print(f"  \033[1m🤖 最终回答:\033[0m")
        print(f"     {final}")
        print("  \033[90m" + "─" * term_width + "\033[0m")


def main():
    app = Paladin()
    if len(sys.argv) > 1:
        print(app.run(" ".join(sys.argv[1:])))
    else:
        print("Paladin — AI-Native 脚手架 (Ctrl+C 退出)")
        while True:
            try:
                q = input("\n> ")
                if q.strip():
                    print(app.run(q))
            except KeyboardInterrupt:
                print("\nbye.")
                break


if __name__ == "__main__":
    main()

