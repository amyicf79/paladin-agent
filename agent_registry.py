# -*- coding: utf-8 -*-
"""
agent_registry.py — v2.5 Agent 角色注册表

功能:
  - 角色定义 (职责白名单 + 动作黑名单)
  - 动作校验 (执行前熔断)
  - 接入 Trace 审计链路
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from pathlib import Path


@dataclass
class AgentRole:
    """Agent 角色定义"""
    name: str
    allowed_tools: List[str] = field(default_factory=list)
    forbidden_actions: List[str] = field(default_factory=list)
    max_token_budget: int = 10000
    required_confidence: float = 0.5


_REGISTRY: Optional["AgentRegistry"] = None
_REGISTRY_FILE: Optional[Path] = None


def _get_registry_path() -> Path:
    global _REGISTRY_FILE
    if _REGISTRY_FILE is None:
        _REGISTRY_FILE = Path(__file__).resolve().parent / "agent_registry.json"
    return _REGISTRY_FILE


class AgentRegistry:
    """Agent 注册表"""

    def __init__(self):
        self.roles: dict[str, AgentRole] = {}
        self._load()

    def register(self, role: AgentRole) -> None:
        self.roles[role.name] = role
        self._save()

    def unregister(self, name: str) -> bool:
        if name in self.roles:
            del self.roles[name]
            self._save()
            return True
        return False

    def verify_action(self, agent_name: str, action: str) -> bool:
        """执行前校验：是否在白名单内"""
        role = self.roles.get(agent_name)
        if not role:
            return False
        if action in role.forbidden_actions:
            return False
        if role.allowed_tools and action not in role.allowed_tools:
            return False
        return True

    def get_role(self, name: str) -> Optional[AgentRole]:
        return self.roles.get(name)

    def list_roles(self) -> List[str]:
        return list(self.roles.keys())

    def _save(self) -> None:
        path = _get_registry_path()
        data = {}
        for name, role in self.roles.items():
            data[name] = {
                "name": role.name,
                "allowed_tools": role.allowed_tools,
                "forbidden_actions": role.forbidden_actions,
                "max_token_budget": role.max_token_budget,
                "required_confidence": role.required_confidence,
            }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        path = _get_registry_path()
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for name, item in data.items():
                self.roles[name] = AgentRole(**item)

    def get_stats(self) -> dict:
        stats = {
            "total_roles": len(self.roles),
            "roles": list(self.roles.keys()),
        }
        # 从 Trace 获取每个角色的实际行为数据
        try:
            from trace import get_trace
            trace = get_trace()
            audit = trace.get_stats()
            stats["audit"] = audit
        except ImportError:
            pass
        return stats


def get_registry() -> AgentRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = AgentRegistry()
    return _REGISTRY


def verify(agent_name: str, action: str) -> bool:
    """便捷校验接口"""
    return get_registry().verify_action(agent_name, action)
