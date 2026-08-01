"""
protocol.py — Commander ↔ Dispatcher 接口协议（零框架依赖，纯dataclass）

Planner 输出的计划 → Executor 按模式执行 → 结果回传 Planner 反思

v0.8 扩展: MetaAction 元操作（工具合成），让 Planner 不仅能编排工具，还能生成工具。
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
class MetaAction:
    """元操作：不调用工具，而是生成/修改工具本身"""
    action_type: str  # "generate_tool" | "patch_config" | "register_alias"
    description: str  # 自然语言描述要什么
    target_name: str  # 生成后的工具名（如果是 generate_tool）


@dataclass
class ExecutionPlan:
    """Planner 输出的完整计划——扩展支持元操作"""
    mode: str = "chain"  # "chain" | "parallel" | "branch"
    steps: List[PlanStep] = field(default_factory=list)
    meta_actions: List[MetaAction] = field(default_factory=list)  # 新增：元操作
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
