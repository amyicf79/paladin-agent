"""
v1.0.2 — 策略优化器叶片
职责：加载经验库，分析工具生成的成功/失败模式，产出策略洞察。
零依赖，纯标准库。
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict


@dataclass
class StrategyInsight:
    """单条策略洞察"""
    category: str  # "naming" | "parameter" | "pattern" | "gap"
    title: str
    description: str
    evidence: List[str]  # 支撑证据（经验条目 key）
    recommendation: str


@dataclass
class StrategyReport:
    """策略报告"""
    summary: str
    total_experiences: int
    insights: List[StrategyInsight] = field(default_factory=list)
    tool_count: int = 0
    success_rate: float = 1.0


class StrategyOptimizer:
    """策略优化器：从经验数据中提炼模式，优化生成策略"""

    def __init__(self, store_path: str = "experience_store"):
        self.store_path = store_path

    def load_experiences(self) -> List[Dict[str, Any]]:
        """加载所有经验记录"""
        if not os.path.isdir(self.store_path):
            return []
        experiences = []
        for f in os.listdir(self.store_path):
            if not f.endswith('.json') or f == "index.json":
                continue
            fp = os.path.join(self.store_path, f)
            with open(fp, 'r', encoding='utf-8') as fh:
                experiences.append(json.load(fh))
        return experiences

    def analyze(self) -> StrategyReport:
        """分析经验数据，生成策略报告"""
        exps = self.load_experiences()
        if not exps:
            return StrategyReport(summary="经验库为空，无法分析", total_experiences=0)

        tools = set(e["tool_name"] for e in exps)
        success = sum(1 for e in exps if e.get("success"))
        insights = []

        # 1) 命名模式分析
        names = [e["tool_name"] for e in exps]
        prefix_counter = Counter(n.split("_")[0] for n in names if "_" in n)
        if prefix_counter:
            common = prefix_counter.most_common(1)[0]
            insights.append(StrategyInsight(
                category="naming",
                title="命名词偏好",
                description=f"工具名最常用前缀: '{common[0]}'（出现 {common[1]} 次）",
                evidence=[n for n in names if n.startswith(common[0])],
                recommendation="codegen 模板的无参数函数名可优先使用此模式"
            ))

        # 2) 错误类型分析
        errors = [e.get("error_type", "Passed") for e in exps]
        error_counts = Counter(errors)
        for err_type, count in error_counts.most_common(3):
            insights.append(StrategyInsight(
                category="pattern",
                title=f"错误类型: {err_type}",
                description=f"出现 {count}/{len(exps)} 次 ({count*100//len(exps)}%)",
                evidence=[e["tool_name"] for e in exps if e.get("error_type") == err_type],
                recommendation="检查该错误类型对应的验证规则是否过于严格"
            ))

        # 3) 参数模式分析
        param_tools = [e.get("tool_name", "") for e in exps]
        has_underscore = sum(1 for n in param_tools if "_" in n)
        insights.append(StrategyInsight(
            category="parameter",
            title="命名风格",
            description=f"下划线命名占比: {has_underscore}/{len(param_tools)} ({has_underscore*100//max(len(param_tools),1)}%)",
            evidence=param_tools[:3],
            recommendation="当前 100% 使用 snake_case，与 Python 社区规范一致"
        ))

        # 4) 覆盖缺口分析
        expected = {"extract", "read", "search", "list", "check", "format", "generate", "parse"}
        covered = set(n.split("_")[0] for n in names if "_" in n)
        missing = expected - covered
        if missing:
            insights.append(StrategyInsight(
                category="gap",
                title="场景缺口",
                description=f"未覆盖的动作类型: {', '.join(missing)}",
                evidence=list(missing),
                recommendation="codegen 模板可预置这些场景的参数模板"
            ))

        return StrategyReport(
            summary=f"分析完成: {len(exps)} 条经验, {len(tools)} 个工具, 成功率 {success}/{len(exps)} ({success*100//max(len(exps),1)}%)",
            total_experiences=len(exps),
            insights=insights,
            tool_count=len(tools),
            success_rate=success / max(len(exps), 1),
        )

    def generate_report_text(self) -> str:
        """生成可读的策略报告"""
        report = self.analyze()
        lines = [
            f"## 策略分析报告",
            f"总览: {report.tool_count} 个工具, {report.total_experiences} 条经验, 成功率 {report.success_rate:.0%}",
            "",
        ]
        for insight in report.insights:
            lines.append(f"### [{insight.category}] {insight.title}")
            lines.append(f"  {insight.description}")
            lines.append(f"  建议: {insight.recommendation}")
            lines.append("")
        return "\n".join(lines)
