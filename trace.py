"""
trace.py v0.1 — 执行追踪契约（可观测性基建）

Paladin 执行从黑盒变透明：每一步记录 {step, tool, args, result, duration_ms, status}，
synthesize 环节汇总为执行树。零依赖，纯数据契约。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class TraceNode:
    """单步执行追踪"""
    step: int                  # 步骤序号
    tool: str                  # 工具名
    args: Dict[str, Any] = field(default_factory=dict)   # 输入快照
    result: Any = None         # 输出快照
    duration_ms: float = 0.0   # 耗时
    status: str = "ok"         # ok | fail
    error: Optional[str] = None  # 失败原因（失败时填充）
    context_delta: str = ""    # 上下文变化描述（为什么失败/关键变化）
    ts: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TraceTree:
    """完整执行树：一次 execute(plan) 的所有步骤"""
    plan_mode: str = ""        # chain | parallel | branch
    nodes: List[TraceNode] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str = ""

    def add(self, node: TraceNode) -> None:
        self.nodes.append(node)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_mode": self.plan_mode,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_steps": len(self.nodes),
            "failed_steps": sum(1 for n in self.nodes if n.status == "fail"),
            "total_duration_ms": round(sum(n.duration_ms for n in self.nodes), 2),
            "nodes": [
                {
                    "step": n.step, "tool": n.tool, "args": n.args,
                    "result": str(n.result)[:200], "duration_ms": n.duration_ms,
                    "status": n.status, "error": n.error, "context_delta": n.context_delta,
                }
                for n in self.nodes
            ],
        }
