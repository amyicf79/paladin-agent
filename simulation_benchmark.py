# -*- coding: utf-8 -*-
"""
simulation_benchmark.py — 模拟数据生成 + 策略基准对比

功能:
  1. 四种模拟环境: stable/trend/shock/dual_scale
  2. 四种策略互相对比: pid/ema/window/hybrid
  3. 四维指标输出: MSE/MAE/稳定性/响应延迟
"""

from __future__ import annotations
import json
import math
import random
from typing import List, Dict, Callable, Optional


class SimulationDataset:
    """模拟数据生成器（带标签的决策样本）"""

    @staticmethod
    def stable(n: int = 30, seed: int = 42) -> List[dict]:
        """稳定环境: ~90% 正确率"""
        rng = random.Random(seed)
        data = []
        for i in range(n):
            data.append({"step": i, "correct": rng.random() < 0.9})
        return data

    @staticmethod
    def trend(n: int = 30, seed: int = 42) -> List[dict]:
        """趋势环境: 正确率从 0.9 递减到 0.6"""
        rng = random.Random(seed)
        data = []
        for i in range(n):
            acc = 0.9 - (i / n) * 0.3  # 0.9 → 0.6
            data.append({"step": i, "correct": rng.random() < acc})
        return data

    @staticmethod
    def shock(n: int = 30, seed: int = 42) -> List[dict]:
        """突变环境: 三段突变（高→中→低→高）"""
        rng = random.Random(seed)
        phases = [(0, 0.9), (n//4, 0.6), (n//2, 0.9), (3*n//4, 0.5)]
        data = []
        for i in range(n):
            acc = 0.7
            for start, rate in reversed(phases):
                if i >= start:
                    acc = rate
                    break
            data.append({"step": i, "correct": rng.random() < acc})
        return data

    @staticmethod
    def dual_scale(n: int = 50, seed: int = 42) -> List[dict]:
        """双时间尺度: 长期漂移+短期波动（为级联策略备数据）"""
        rng = random.Random(seed)
        data = []
        for i in range(n):
            base = 0.8 - (i / n) * 0.2          # 长期漂移 0.8→0.6
            wave = 0.1 * math.sin(i * 0.5)       # 短期波动 ±0.1
            acc = base + wave
            data.append({"step": i, "correct": rng.random() < acc})
        return data

    @staticmethod
    def all(n_per_env: int = 30) -> Dict[str, List[dict]]:
        """生成全部四种环境"""
        return {
            "stable": SimulationDataset.stable(n_per_env),
            "trend": SimulationDataset.trend(n_per_env),
            "shock": SimulationDataset.shock(n_per_env),
            "dual_scale": SimulationDataset.dual_scale(n_per_env),
        }


class StrategyBenchmark:
    """策略基准测试"""

    @staticmethod
    def run(strategies: Dict[str, Callable], dataset: List[dict]) -> List[dict]:
        """跑基准: 对每个策略, 在数据集上滚动模拟调优

        Args:
            strategies: {"pid": fn, ...}
            dataset: [{"step": 0, "correct": True}, ...]

        Returns:
            [{"strategy": "pid", "MSE": 0.04, "MAE": 0.18, "stability": 0.02, "delay": 3}, ...]
        """
        results = []
        for sname, sfunc in strategies.items():
            threshold = 0.5
            predictions = []
            errors = []
            stability_changes = []
            delay = 0

            for i, sample in enumerate(dataset):
                prev = threshold
                # 策略需要至少3步数据
                if i >= 3:
                    recent = dataset[max(0, i-6):i+1]
                    try:
                        threshold = sfunc(recent)
                    except Exception:
                        threshold = prev
                else:
                    threshold = 0.5

                delta = abs(threshold - prev)
                stability_changes.append(delta)

                # 预测: 阈值决策是否正确
                correct = sample["correct"]
                predicted_correct = threshold >= 0.5
                actual = 1.0 if correct else 0.0
                predictions.append(predicted_correct)
                errors.append(actual - threshold)

                delay += 1

            n = len(errors)
            mse = sum(e*e for e in errors) / max(n, 1)
            mae = sum(abs(e) for e in errors) / max(n, 1)
            stability = sum(stability_changes) / max(len(stability_changes), 1)
            first_lag = max(1, n // 10) if n > 10 else 1

            results.append({
                "strategy": sname,
                "MSE": round(mse, 4),
                "MAE": round(mae, 4),
                "stability": round(stability, 4),
                "delay": delay,
                "data_points": n,
            })

        return results

    @staticmethod
    def report(results: List[dict]) -> str:
        """输出 Markdown 报告"""
        lines = [
            "| 策略 | MSE | MAE | 稳定性(Δ) | 延迟(步) | 数据点 |",
            "|------|:---:|:---:|:---------:|:--------:|:------:|",
        ]
        for r in sorted(results, key=lambda x: x["MAE"]):
            lines.append(
                f"| {r['strategy']:8s} | {r['MSE']:.4f} | {r['MAE']:.4f} | "
                f"{r['stability']:.4f} | {r['delay']} | {r['data_points']} |"
            )
        return "\n".join(lines)
