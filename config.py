"""
config.py v0.7 — Paladin 配置系统

三层优先级（高→低）:
  1. CLI --config 指定文件
  2. 项目根目录 paladin.toml
  3. dataclass 内置默认值

Usage:
    from paladin.config import load_config
    cfg = load_config("/path/to/paladin.toml")
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional

# ── tomllib: Python 3.11+ 标准库, <3.11 需 pip install tomli ──
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # 无 TOML 解析器时仅用默认值


# ═══════════════════════════════════════════════════════════════
# Dataclass 配置结构（默认值 = 最低优先级）
# ═══════════════════════════════════════════════════════════════

@dataclass
class CoreConfig:
    max_iterations: int = 3
    default_model: str = "deepseek"


@dataclass
class PlannerConfig:
    backend: str = "mock"       # "mock" | "deepseek" | "qwen" | "glm"
    model: str = ""             # 为空时 fallback 到 core.default_model


@dataclass
class ToolsConfig:
    enable_search: bool = True
    enable_calculate: bool = True
    enable_memory: bool = True
    enable_report: bool = True


@dataclass
class DemoConfig:
    auto_mode: bool = False
    scenes: List[str] = field(default_factory=lambda: ["chain", "parallel", "branch"])


@dataclass
class LoggingConfig:
    level: str = "info"


@dataclass
class ModelsConfig:
    """模型 API 配置（占位，v0.8 后生效）"""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"


@dataclass
class PaladinConfig:
    core: CoreConfig = field(default_factory=CoreConfig)
    planner: PlannerConfig = field(default_factory=PlannerConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    demo: DemoConfig = field(default_factory=DemoConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    models: ModelsConfig = field(default_factory=ModelsConfig)


# ═══════════════════════════════════════════════════════════════
# 加载器
# ═══════════════════════════════════════════════════════════════

def load_config(config_path: Optional[str] = None) -> PaladinConfig:
    """加载配置：CLI 指定 > 项目根目录 paladin.toml > 默认值"""
    config = PaladinConfig()

    if tomllib is None:
        return config  # 无 TOML 解析器，仅使用默认值

    # 搜索路径（按优先级）
    paths = []
    if config_path:
        paths.append(config_path)
    paths.append(os.path.join(os.getcwd(), "paladin.toml"))

    for path in paths:
        if path and os.path.isfile(path):
            with open(path, "rb") as f:
                data = tomllib.load(f)
            _merge_config(config, data)
            break  # 只加载最高优先级的

    return config


def _merge_config(config, data: dict):
    """递归合并 TOML dict → dataclass（只覆盖存在的字段）"""
    for key, value in data.items():
        if not hasattr(config, key):
            continue
        attr = getattr(config, key)
        if hasattr(attr, "__dataclass_fields__") and isinstance(value, dict):
            _merge_config(attr, value)
        elif type(attr) == type(value) or isinstance(value, type(attr)):
            setattr(config, key, value)
        elif isinstance(attr, list) and isinstance(value, list):
            setattr(config, key, value)
