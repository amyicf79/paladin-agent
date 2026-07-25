"""
protocol.py — Commander ↔ Dispatcher 接口协议（零框架依赖，纯dataclass）

Planner 输出的计划 → Executor 按模式执行 → 结果回传 Planner 反思
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class PlanStep:
    """单个工具调用步骤"""
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None  # 仅 branch 模式使用


@dataclass
class ExecutionPlan:
    """Planner 输出的完整计划"""
    mode: str = "chain"  # "chain" | "parallel" | "branch"
    steps: List[PlanStep] = field(default_factory=list)
    reason: Optional[str] = None


@dataclass
class ExecutionResult:
    """Executor 返回的单步结果

    context_updates: 工具返回的上下文更新，chain 模式中自动传递给后续步骤
    """
    step: PlanStep
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    context_updates: Dict[str, Any] = field(default_factory=dict)
