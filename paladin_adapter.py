# -*- coding: utf-8 -*-
"""
paladin_adapter.py — Paladin 通用适配器

将 Paladin 的元认知能力暴露为标准Python接口：
  - gate_assess(task) → GateDecision
  - arbitrate(proposals) → ArbitrationResult
  - trace_query(trace_id) → List[Event]
  - market_contribute(tool, code) → exp_id

用法:
    from paladin_adapter import PaladinAdapter
    paladin = PaladinAdapter()
    decision = paladin.gate_assess("analyze stock AAPL")
"""

from __future__ import annotations
from typing import List, Optional, Any, Dict


class PaladinAdapter:
    """Paladin 通用适配器（所有依赖可选注入）"""

    def __init__(self, registry=None, reputation=None, arbiter=None,
                 scheduler=None, market=None, governance=None):
        self._registry = registry
        self._reputation = reputation
        self._arbiter = arbiter
        self._scheduler = scheduler
        self._market = market
        self._governance = governance
        self._lazy_loaded = False

    def _lazy_load(self) -> None:
        if self._lazy_loaded:
            return
        try:
            if self._registry is None:
                from agent_registry import get_registry
                self._registry = get_registry()
            if self._reputation is None:
                from reputation_tracker import get_reputation
                self._reputation = get_reputation()
            if self._arbiter is None:
                from multi_agent_arbiter import get_arbiter
                self._arbiter = get_arbiter()
            if self._scheduler is None:
                from market_scheduler import get_scheduler
                self._scheduler = get_scheduler()
            if self._market is None:
                from experience_market import get_market
                self._market = get_market()
            if self._governance is None:
                from adaptive_governance import get_governance
                self._governance = get_governance()
        except ImportError:
            pass
        self._lazy_loaded = True

    def get_accuracy(self, recent_n: int = 100) -> dict:
        """门控自校准: 统计近 N 次放行任务的成功率"""
        self._lazy_load()
        try:
            from trace import get_trace
            events = get_trace().query(limit=recent_n)
            allowed = [e for e in events if e.get("decision") == "allow"]
            if not allowed:
                return {"accuracy": None, "total": 0, "msg": "暂无放行记录"}
            succeeded = [e for e in allowed if e.get("outcome", {}).get("status") == "success"]
            return {"accuracy": round(len(succeeded)/len(allowed), 3), "total": len(allowed), "succeeded": len(succeeded)}
        except Exception:
            return {"accuracy": None, "total": 0, "msg": "查询失败"}

    def gate_assess(self, task_signature: str, risk_level: str = "normal") -> dict:
        self._lazy_load()
        try:
            from metacognition_gate import assess_task
            gd = assess_task(task_signature, risk_level).to_dict()
            zone = gd.get("zone", "missing")
            conf = gd.get("confidence", 0.0)
            # 三级风险映射
            if zone == "proficient":
                risk_out = "low"
            elif zone == "perplexed" and conf > 0.4:
                risk_out = "low"
            elif zone == "perplexed":
                risk_out = "medium"
            elif zone == "missing" and risk_level == "low":
                risk_out = "low"
            else:
                risk_out = "high"
            gd["risk_level"] = risk_out
            gd["suggested_action"] = {"low": "直接放行",
                                       "medium": "人工确认",
                                       "high": "拒绝"}.get(risk_out, "拒绝")
            # risk_level 覆盖 allow: low → 放行
            if risk_out == "low":
                gd["allow"] = True
            return gd
        except Exception as e:
            return {"allow": False, "error": str(e), "zone": "error",
                    "risk_level": "high", "suggested_action": "拒绝"}

    def arbitrate(self, proposals: List[dict]) -> dict:
        self._lazy_load()
        try:
            from multi_agent_arbiter import AgentProposal, arbitrate
            parsed = [AgentProposal(**p) for p in proposals]
            result = arbitrate(parsed)
            return {
                "winner": result.winner,
                "confidence": result.confidence,
                "escalate_to_human": result.escalate_to_human,
                "details": result.details,
            }
        except Exception as e:
            return {"winner": None, "error": str(e), "escalate_to_human": True}

    def trace_query(self, trace_id: Optional[str] = None,
                    agent: Optional[str] = None, limit: int = 50) -> List[dict]:
        self._lazy_load()
        try:
            from trace import get_trace
            return get_trace().query(trace_id=trace_id, agent=agent, limit=limit)
        except Exception as e:
            return [{"error": str(e)}]

    def market_contribute(self, tool_name: str, code: str,
                          agent: str, gain: float = 0.5, trust: float = 0.5) -> str:
        self._lazy_load()
        try:
            from experience_market import contribute
            return contribute(tool_name, code, agent, gain, trust)
        except Exception as e:
            return f"error:{e}"

    def get_health(self) -> dict:
        self._lazy_load()
        status = {}
        for name, mod, fn in [
            ("registry", self._registry, "list_roles"),
            ("arbiter", self._arbiter, "get_stats"),
            ("governance", self._governance, "get_health"),
        ]:
            try:
                method = getattr(mod, fn, None)
                status[name] = method() if method else "inactive"
            except Exception:
                status[name] = "error"
        return status
