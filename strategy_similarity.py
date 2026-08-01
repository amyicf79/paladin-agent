# -*- coding: utf-8 -*-
"""
strategy_similarity.py — v1.6 策略相似度校验

行为级监督：比较参考路径与探索路径的策略语义相似度，
低于阈值时丢弃探索路径的新经验并重新采样。
"""

import math
from typing import Dict, Set, Any


def _char_ngram_similarity(text_a: str, text_b: str, n: int = 3) -> float:
    """基于字符n-gram的文本相似度"""
    a_grams = set(text_a[i:i+n] for i in range(len(text_a)-n+1))
    b_grams = set(text_b[i:i+n] for i in range(len(text_b)-n+1))
    if not a_grams or not b_grams:
        return 0.0
    intersection = a_grams & b_grams
    union = a_grams | b_grams
    return len(intersection) / len(union)


def _jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Jaccard相似度"""
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def strategy_similarity_check(
    ref_tool: str,
    exp_tool: str,
    ref_code: str = "",
    exp_code: str = "",
    threshold: float = 0.7,
) -> tuple:
    """比较参考路径与探索路径的策略相似度
    
    Returns:
        (passed: bool, similarity: float, details: dict)
    """
    # 工具名称相似度（语义）
    name_sim = _char_ngram_similarity(ref_tool, exp_tool, n=2)
    
    # 代码内容相似度（结构）
    code_sim = _char_ngram_similarity(ref_code, exp_code, n=5) if ref_code and exp_code else 0.0
    
    # 工具名关键词重叠
    ref_keys = set(ref_tool.replace('_', ' ').split())
    exp_keys = set(exp_tool.replace('_', ' ').split())
    struct_sim = _jaccard_similarity(ref_keys, exp_keys)
    
    # 综合相似度
    similarity = 0.5 * name_sim + 0.3 * struct_sim + 0.2 * code_sim
    
    passed = similarity >= threshold
    
    return passed, round(similarity, 4), {
        "name_similarity": round(name_sim, 4),
        "code_similarity": round(code_sim, 4),
        "structural_similarity": round(struct_sim, 4),
        "threshold": threshold,
    }
