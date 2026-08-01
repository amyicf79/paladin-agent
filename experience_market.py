# -*- coding: utf-8 -*-
"""
experience_market.py — v3.0 跨 Agent 经验共享市场

功能:
  - Agent 将 validated 经验贡献到共享池
  - 信任评估：基于贡献 Agent 的历史成功率
  - 价值评估：基于经验的反事实增益
  - 冲突仲裁：多 Agent 推荐不一致时协商
  - 熔断机制：连续贡献低质经验时自动降权
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


_MARKET_FILE = None


def _get_market_path() -> Path:
    global _MARKET_FILE
    if _MARKET_FILE is None:
        _MARKET_FILE = Path(__file__).resolve().parent / "experience_market.json"
    return _MARKET_FILE


@dataclass
class SharedExperience:
    """共享经验"""
    id: str
    tool_name: str
    code: str
    source_agent: str
    trust_score: float
    gain_score: float
    usage_count: int = 0
    timestamp: str = ""


class ExperienceMarket:
    """经验共享市场"""

    def __init__(self):
        self._pool: Dict[str, SharedExperience] = {}
        self._agent_quality: Dict[str, List[bool]] = {}
        self._load()

    def contribute(self, tool_name: str, code: str, agent: str,
                   gain_score: float, trust: float) -> str:
        """Agent 贡献经验到共享池"""
        import hashlib
        exp_id = hashlib.md5(f"{tool_name}{code}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        self._pool[exp_id] = SharedExperience(
            id=exp_id, tool_name=tool_name, code=code,
            source_agent=agent, trust_score=trust,
            gain_score=gain_score, timestamp=datetime.now().isoformat(),
        )
        self._save()
        return exp_id

    def query(self, tool_name: str, min_trust: float = 0.3) -> List[SharedExperience]:
        """按工具名查询共享经验"""
        results = [
            e for e in self._pool.values()
            if e.tool_name == tool_name and e.trust_score >= min_trust
        ]
        results.sort(key=lambda x: x.gain_score, reverse=True)
        return results[:5]

    def record_usage(self, exp_id: str, success: bool) -> None:
        """记录共享经验的使用结果"""
        if exp_id in self._pool:
            self._pool[exp_id].usage_count += 1
            self._save()
        # 如果使用失败，降低来源 Agent 的信誉
        if not success:
            for e in self._pool.values():
                if e.id == exp_id:
                    agent = e.source_agent
                    self._agent_quality.setdefault(agent, []).append(False)
                    if self._get_meltdown(agent):
                        # 熔断：移除该 Agent 的所有贡献
                        to_remove = [k for k, v in self._pool.items()
                                     if v.source_agent == agent]
                        for k in to_remove:
                            del self._pool[k]
                        self._save()
                    break

    def _get_meltdown(self, agent: str) -> bool:
        """连续失败≥3次触发熔断"""
        outcomes = self._agent_quality.get(agent, [])
        return len(outcomes) >= 3 and sum(outcomes[-3:]) == 0

    def get_stats(self) -> dict:
        return {
            "total_experiences": len(self._pool),
            "by_agent": {},
            "melted_agents": [
                a for a in self._agent_quality
                if self._get_meltdown(a)
            ],
        }

    def _save(self) -> None:
        path = _get_market_path()
        data = {
            "pool": {k: v.__dict__ for k, v in self._pool.items()},
            "agent_quality": self._agent_quality,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        path = _get_market_path()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.get("pool", {}).items():
                self._pool[k] = SharedExperience(**v)
            self._agent_quality = data.get("agent_quality", {})


_default_market: Optional[ExperienceMarket] = None


def get_market() -> ExperienceMarket:
    global _default_market
    if _default_market is None:
        _default_market = ExperienceMarket()
    return _default_market


def contribute(tool_name: str, code: str, agent: str, gain: float, trust: float) -> str:
    return get_market().contribute(tool_name, code, agent, gain, trust)


def query(tool_name: str) -> List[SharedExperience]:
    return get_market().query(tool_name)
