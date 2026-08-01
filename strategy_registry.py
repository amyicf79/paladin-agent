# -*- coding: utf-8 -*-
"""
strategy_registry.py — 策略注册表

功能:
  - register(name, env_match, fn, description)
  - unregister(name)
  - get(env) → 匹配的策略函数
  - list() → 所有注册策略
  - register_unknown(description) → 为未知环境占位
"""

from __future__ import annotations
from typing import List, Optional, Callable, Dict


class StrategyEntry:
    """单条策略注册条目"""
    def __init__(self, name: str, env_match: List[str],
                 fn: Callable, description: str = ""):
        self.name = name
        self.env_match = env_match
        self.fn = fn
        self.description = description

    def matches(self, env: str) -> bool:
        return env in self.env_match


class StrategyRegistry:
    """运行时策略注册表"""

    def __init__(self):
        self._entries: Dict[str, StrategyEntry] = {}

    def register(self, name: str, env_match: List[str],
                 fn: Callable, description: str = "") -> None:
        self._entries[name] = StrategyEntry(name, env_match, fn, description)

    def unregister(self, name: str) -> bool:
        return self._entries.pop(name, None) is not None

    def get(self, env: str) -> Optional[StrategyEntry]:
        """返回匹配环境的第一个策略"""
        for entry in self._entries.values():
            if entry.matches(env):
                return entry
        return None

    def list(self) -> List[str]:
        return list(self._entries.keys())

    def register_unknown(self, description: str = "占位") -> str:
        """注册未知环境占位策略"""
        name = f"unknown_{len(self._entries) + 1}"
        self.register(name, ["unknown"], lambda r, _name=name: 0.5,
                      description=description)
        return name

    def get_stats(self) -> dict:
        return {
            "total": len(self._entries),
            "strategies": list(self._entries.keys()),
            "env_coverage": list(set(
                e for entry in self._entries.values() for e in entry.env_match
            )),
        }


_default_registry: Optional[StrategyRegistry] = None


def get_registry() -> StrategyRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = StrategyRegistry()
    return _default_registry
