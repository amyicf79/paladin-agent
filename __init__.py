"""
Paladin — 自进化 AI 智能体框架 v1.2
"""
import os
import sys

# shim: 部分内部模块使用顶层导入（from semantic_search import ...），
# 将本包目录加入 sys.path 以兼容该模式（pip 安装后同样可用）。
_PALADIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _PALADIN_DIR not in sys.path:
    sys.path.insert(0, _PALADIN_DIR)

from paladin.app import Paladin
from paladin.semantic_search import SemanticSearch, semantic_search, get_engine
from paladin.experience_graph import ExperienceGraph, get_graph, rebuild_graph
from paladin.experience_store import ExperienceStore, Experience
from paladin.strategy_optimizer import StrategyOptimizer

__version__ = "1.3.0"
__all__ = [
    "Paladin", "SemanticSearch", "semantic_search", "get_engine",
    "ExperienceGraph", "get_graph", "rebuild_graph",
    "ExperienceStore", "Experience", "StrategyOptimizer",
]
