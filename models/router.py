"""
router.py — 模型路由（AI-Native 卓越性的体现）

Flash → Pro 质量路由：低分自动升档，高分保持低成本。
"""
from typing import Callable, Tuple, Any, Optional
import re


def quality_score(text: str) -> float:
    """0~1 质量分"""
    score = 0.5
    if len(text) > 50: score += 0.15
    if len(text) > 200: score += 0.10
    if re.search(r'[。！？\n]', text): score += 0.10
    if re.search(r'因此|所以|因为|综上|首先|其次|最后', text): score += 0.10
    return min(score, 1.0)


class ModelRouter:
    def __init__(self, quality_threshold: float = 0.6):
        self.threshold = quality_threshold
        self.stats = {"flash": 0, "upgraded": 0, "pro_direct": 0, "total": 0}

    def route(self, flash_fn: Callable, pro_fn: Callable, force_pro: bool = False) -> Tuple[Any, str]:
        self.stats["total"] += 1
        if force_pro:
            self.stats["pro_direct"] += 1
            return pro_fn(), "pro"
        result = flash_fn()
        if quality_score(str(result)) < self.threshold:
            self.stats["upgraded"] += 1
            return pro_fn(), "pro"
        self.stats["flash"] += 1
        return result, "flash"
