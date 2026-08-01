# -*- coding: utf-8 -*-
"""
agent_bid.py — v3.0 Agent 报价协议

每个 Agent 在接到任务时输出一份报价：
  - 能力描述（我能做什么）
  - 置信度（我有多确定）
  - 成本估计（我需要多少资源）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AgentBid:
    """Agent 单次报价"""
    agent_name: str
    task_type: str
    confidence: float          # 0.0~1.0
    zone: str = "unknown"      # proficient / perplexed / missing
    estimated_cost: float = 1.0
    capability_description: str = ""
    source: str = "auto"       # auto / manual

    def score(self, reputation: float = 0.5) -> float:
        """加权评分 = 置信度 × 信誉分 / 成本"""
        return round(self.confidence * reputation / max(self.estimated_cost, 0.01), 3)


def collect_bids(registry, task_signature: str, agents: Optional[List[str]] = None,
                 zone_map: Optional[dict] = None) -> List[AgentBid]:
    """收集 Agent 报价

    Args:
        registry: AgentRegistry 实例 (含 allow_action / get_role)
        task_signature: 任务描述
        agents: 指定收集哪些 Agent（None=全部）
        zone_map: 可选的 Agent→Zone 映射

    Returns:
        [AgentBid, ...]
    """
    bids = []
    target_agents = agents or registry.list_roles()
    for a_name in target_agents:
        role = registry.get_role(a_name)
        if not role:
            continue
        # 检查 Agent 是否具备该任务所需的能力（简化版：允许所有白名单工具视为+1）
        capability = f"可用 {len(role.allowed_tools)} 个工具: {', '.join(role.allowed_tools[:3])}"
        zone = (zone_map or {}).get(a_name, "perplexed")
        confidence = role.required_confidence if hasattr(role, 'required_confidence') else 0.5
        # T3: 能力匹配——任务关键词与 allowed_tools 子串匹配，命中加成取代纯成本惩罚
        # 中文任务词 → 工具核心词映射（Paladin 支持中文任务描述）
        _ZH_HINT = {
            "审查": "validate", "修复": "repair", "代码": "code", "测试": "validate",
            "统计": "compute", "过滤": "filter", "异常": "outlier", "排序": "sort",
            "读取": "read", "抓取": "fetch", "网页": "web", "标题": "title",
            "解析": "parse", "计算": "calc", "搜索": "search", "总结": "summary",
        }
        match = 0
        task_lower = task_signature.lower()
        zh_keys = [k for k in _ZH_HINT if k in task_signature]
        for tool in role.allowed_tools:
            core = tool.split(':')[-1].split('_')[0].lower()
            if core in task_lower or tool.lower() in task_lower:
                match += 1
            elif any(_ZH_HINT[k].lower() in core for k in zh_keys):
                match += 1
        if match > 0:
            confidence = min(1.0, confidence + 0.15 * match)
            zone = "proficient"
        bids.append(AgentBid(
            agent_name=a_name,
            task_type=task_signature,
            confidence=confidence,
            zone=zone,
            estimated_cost=max(1.0, len(role.allowed_tools) - match * 2),  # 匹配工具不再计为成本
            capability_description=capability,
        ))
    return bids
