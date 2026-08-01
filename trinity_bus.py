# -*- coding: utf-8 -*-
"""trinity_bus.py — GA <-> Paladin <-> OpenWorker 通信总线

三步事件注入: pre_gate -> post_gate -> exec_done
所有事件自动附 Trace ID
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Dict, List, Callable, Optional


class TrinityBus:
    def __init__(self):
        self._trace_id: Optional[str] = None
        self._events: List[dict] = []
        self._callbacks: Dict[str, List[Callable]] = {}

    def new_trace(self) -> str:
        self._trace_id = uuid.uuid4().hex[:12]
        return self._trace_id

    def publish(self, event_type: str, data: dict, trace_id: Optional[str] = None) -> dict:
        tid = trace_id or self._trace_id or self.new_trace()
        event = {
            "trace_id": tid,
            "event": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        self._events.append(event)
        for cb in self._callbacks.get(event_type, []):
            try:
                cb(event)
            except Exception:
                pass
        return event

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self._callbacks.setdefault(event_type, []).append(callback)

    def trace(self, event_type: str, data: dict) -> dict:
        return self.publish(event_type, data)

    def get_events(self, trace_id: Optional[str] = None) -> List[dict]:
        if trace_id:
            return [e for e in self._events if e["trace_id"] == trace_id]
        return self._events


_default_bus: Optional[TrinityBus] = None


def get_bus() -> TrinityBus:
    global _default_bus
    if _default_bus is None:
        _default_bus = TrinityBus()
    return _default_bus
