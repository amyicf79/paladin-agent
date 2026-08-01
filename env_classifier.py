# -*- coding: utf-8 -*-
"""
env_classifier.py — 环境分类器

输入: 最近30步误差序列 [{"correct": True/False}, ...]
特征: 波动率(std) / 趋势斜率(线性回归) / 突变频率(符号翻转率)
输出: (env_type, confidence, is_confident)
"""

from __future__ import annotations
import math
from typing import List, Tuple


class EnvironmentClassifier:
    """基于3个统计特征的环境类型分类器"""

    @staticmethod
    def _to_errors(recent: List[dict]) -> List[float]:
        """提取误差序列: 正确→1.0, 错误→0.0"""
        return [1.0 if d.get("correct", False) else 0.0 for d in recent]

    @staticmethod
    def _autocorr(errors: List[float], lag: int = 3) -> float:
        """自相关系数: 检测周期性/振荡模式（dual_scale 有短周期波）"""
        n = len(errors)
        if n < lag + 2:
            return 0.0
        mean = sum(errors) / n
        num = sum((errors[i] - mean) * (errors[i + lag] - mean) for i in range(n - lag))
        den = sum((e - mean) ** 2 for e in errors)
        return num / den if den != 0 else 0.0

    @staticmethod
    def _volatility(errors: List[float]) -> float:
        """波动率: 滑动窗口标准差"""
        n = len(errors)
        if n < 3:
            return 0.0
        mean = sum(errors) / n
        variance = sum((e - mean) ** 2 for e in errors) / n
        return math.sqrt(variance)

    @staticmethod
    def _trend_slope(errors: List[float]) -> float:
        """趋势斜率: 最小二乘法线性回归"""
        n = len(errors)
        if n < 3:
            return 0.0
        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = sum(errors) / n
        num = sum((xs[i] - mean_x) * (errors[i] - mean_y) for i in range(n))
        den = sum((x - mean_x) ** 2 for x in xs)
        return num / den if den != 0 else 0.0

    @staticmethod
    def _shock_freq(errors: List[float]) -> float:
        """突变频率: 连续正确→错误的符号翻转率"""
        if len(errors) < 2:
            return 0.0
        flips = sum(1 for i in range(1, len(errors))
                     if (errors[i] - errors[i - 1]) < -0.5)
        return flips / max(len(errors) - 1, 1)

    def classify(self, recent: List[dict],
                 min_steps: int = 10) -> Tuple[str, float]:
        """环境分类
        
        Returns:
            (env_type, confidence, is_confident)
            env_type: "stable" | "trend" | "shock" | "dual_scale"
        """
        if len(recent) < min_steps:
            return ("stable", 0.3)  # 数据不足时保守返回stable

        errors = self._to_errors(recent)
        vol = self._volatility(errors)
        slope = self._trend_slope(errors)
        shock = self._shock_freq(errors)
        ac = self._autocorr(errors, lag=2)

        # 阈值判定规则（基于基准数据校准，30步下≈50%准确率可接受）
        # shock: 高突变频率优先判定
        if shock > 0.12:
            conf = round(min(0.7, shock * 2), 2)
            return ("shock", conf, conf >= 0.4)
        # trend: 明显斜率 + 中等波动
        if abs(slope) > 0.008 and vol > 0.20:
            conf = round(min(0.6, abs(slope) * 30), 2)
            return ("trend", conf, conf >= 0.4)
        # dual_scale: 高波动 + 振荡模式
        if vol >= 0.25 and ac < 0:
            conf = round(min(0.6, (vol + abs(ac)) * 1.5), 2)
            return ("dual_scale", conf, conf >= 0.4)
        # stable: 低波动兜底
        conf = round(max(0.3, 1.0 - vol), 2)
        return ("stable", conf, conf >= 0.4)

    def classify_batch(self, datasets: dict) -> dict:
        """批量分类并统计准确率"""
        results = {}
        correct = 0
        total = 0
        for env_name, data in datasets.items():
            pred, conf = self.classify(data)
            match = pred == env_name
            results[env_name] = {"predicted": pred, "confidence": conf, "correct": match}
            if match:
                correct += 1
            total += 1
        results["accuracy"] = f"{correct}/{total}"
        return results
