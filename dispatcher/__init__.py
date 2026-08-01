"""
dispatcher — 执行层（调度官）
接收计划 → 注册工具 → 执行 → 返回结果
"""
from .executor import Executor

__all__ = ["Executor"]
