"""
watch.py — 成本监控（AI-Native 自给自足的保障）

记录每次 LLM 调用的 token 消耗和预估成本。
单日超阈值自动告警。
"""
import json, os
from datetime import date
from typing import Optional

MODEL_PRICING = {
    "flash":   {"input": 0.00000015, "output": 0.00000200},
    "pro":     {"input": 0.00000030, "output": 0.00000600},
    "deepseek-chat": {"input": 0.00000015, "output": 0.00000200},
}


class CostWatch:
    def __init__(self, threshold: float = 40.0, filepath: Optional[str] = None):
        self.threshold = threshold
        self._fp = filepath or os.path.join(os.path.dirname(__file__), "..", "costs.json")

    def record(self, model: str, input_tokens: int, output_tokens: int):
        pricing = MODEL_PRICING.get(model, {"input": 0.0000005, "output": 0.000002})
        cost = input_tokens * pricing["input"] + output_tokens * pricing["output"]
        today = str(date.today())
        data = self._load()
        data.setdefault(today, {"cost": 0.0, "calls": 0})
        data[today]["cost"] += cost
        data[today]["calls"] += 1
        self._save(data)

    def check(self) -> dict:
        data = self._load()
        today = str(date.today())
        td = data.get(today, {"cost": 0.0, "calls": 0})
        return {"date": today, "cost": round(td["cost"], 2), "calls": td["calls"],
                "threshold": self.threshold, "over_limit": td["cost"] > self.threshold}

    def _load(self) -> dict:
        if os.path.exists(self._fp):
            try: return json.load(open(self._fp, 'r'))
            except: return {}
        return {}

    def _save(self, data: dict):
        os.makedirs(os.path.dirname(self._fp) or '.', exist_ok=True)
        json.dump(data, open(self._fp, 'w'), indent=2)
