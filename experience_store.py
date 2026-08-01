"""
v1.0.1 — 经验库叶片
职责：持久化存储修复历史（问题→解法），提供相似问题检索。
零依赖，纯标准库。
"""

import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

# v1.2: 语义检索引擎
from semantic_search import SemanticSearch, get_engine
# v1.3: 小世界拓扑引擎
from experience_graph import ExperienceGraph, get_graph
from cognitive_zone import CognitiveZoneClassifier, get_classifier
from dual_path import DualPathRecommender, get_recommender
from metacognition_gate import MetacognitionGate, get_gate


@dataclass
class Experience:
    """单条经验记录"""
    problem_signature: str
    tool_name: str
    original_code: str
    repaired_code: str
    error_type: str
    error_message: str
    timestamp: str
    success: bool = True


@dataclass
class ExperienceStore:
    """经验库：存储和检索修复记录"""
    storage_dir: str = "experience_store"
    max_entries: int = 1000

    def __post_init__(self):
        # 使用绝对路径：基于本文件所在目录解析
        base = Path(__file__).resolve().parent
        self.path = base / self.storage_dir
        self.path.mkdir(exist_ok=True)
        self._index_file = self.path / "index.json"
        self._load_index()

    def _load_index(self):
        if self._index_file.exists():
            with open(self._index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = []

    def _save_index(self):
        if len(self.index) > self.max_entries:
            self.index = self.index[-self.max_entries:]
        with open(self._index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def add_experience(self, exp: Experience) -> str:
        hash_input = f"{exp.tool_name}:{exp.error_type}:{exp.error_message[:50]}"
        file_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        filename = f"{exp.tool_name}_{file_hash}.json"
        filepath = self.path / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "tool_name": exp.tool_name,
                "problem_signature": exp.problem_signature,
                "original_code": exp.original_code,
                "repaired_code": exp.repaired_code,
                "error_type": exp.error_type,
                "error_message": exp.error_message,
                "timestamp": exp.timestamp,
                "success": exp.success
            }, f, indent=2, ensure_ascii=False)

        self.index.append({
            "file": filename,
            "tool_name": exp.tool_name,
            "error_type": exp.error_type,
            "timestamp": exp.timestamp
        })
        self._save_index()
        return filename

    def find_similar(self, error_type: str, error_message: str,
                     tool_name: Optional[str] = None) -> List[Experience]:
        """查找相似经验 — v1.2 使用语义检索替代关键词重叠"""
        results = []
        
        # 构建查询：结合error_type和error_message
        query = f"{error_type} {error_message}"
        
        # 使用语义检索
        engine = get_engine()
        if not engine._index_built:
            engine.build_index(str(self.path))
        
        hits = engine.search(query, top_k=5, tool_filter=tool_name)
        
        for hit in hits:
            filename = hit['filename']
            filepath = self.path / filename
            if not filepath.exists():
                continue
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            results.append(Experience(
                problem_signature=data.get("problem_signature", ""),
                tool_name=data.get("tool_name", ""),
                original_code=data.get("original_code", ""),
                repaired_code=data.get("repaired_code", ""),
                error_type=data.get("error_type", ""),
                error_message=data.get("error_message", ""),
                timestamp=data.get("timestamp", ""),
                success=data.get("success", True)
            ))
        
        return results

    def topo_find_similar(self, error_type: str, error_message: str,
                          tool_name: Optional[str] = None,
                          top_k: int = 5) -> List[Experience]:
        """v1.3: 拓扑感知的相似经验查找

        使用小世界网络的社区结构和捷径路由来排序结果。
        同社区经验优先，桥梁经验次之，跨社区再次之。
        """
        query = f"{error_type} {error_message}"

        graph = get_graph()
        if not graph._built:
            graph.build(str(self.path))

        hits = graph.topo_search(query, top_k=top_k)

        results = []
        for hit in hits:
            if tool_name and tool_name not in hit.get('tool_name', ''):
                continue
            filename = hit['filename']
            filepath = self.path / filename
            if not filepath.exists():
                continue
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            exp = Experience(
                problem_signature=data.get("problem_signature", ""),
                tool_name=data.get("tool_name", ""),
                original_code=data.get("original_code", ""),
                repaired_code=data.get("repaired_code", ""),
                error_type=data.get("error_type", ""),
                error_message=data.get("error_message", ""),
                timestamp=data.get("timestamp", ""),
                success=data.get("success", True)
            )
            exp.topo_score = hit.get('topo_score', hit.get('score', 0))
            exp.community = hit.get('community', -1)
            exp.is_shortcut = hit.get('is_shortcut', False)
            results.append(exp)

        return results

    def zone_classify(self, query: str) -> dict:
        """v1.4: 认知分区 — 判断查询属于哪个区域"""
        classifier = get_classifier()
        result = classifier.classify(query, str(self.path))
        return {
            "zone": result.zone,
            "confidence": result.confidence,
            "top1_score": result.top1_score,
            "mean_score": result.mean_score,
            "coverage_count": result.coverage_count,
            "success_rate": result.history_success_rate,
            "reason": result.reason,
            "action": {
                "proficient": "直接执行（跳过检索）",
                "perplexed": "检索经验 + 验证",
                "missing": "生成新方案 + 探索",
            }.get(result.zone, "未知"),
        }

    def dual_path_recommend(self, query: str, zone: Optional[str] = None) -> Any:
        """v1.5: 双路径推荐"""
        rec = get_recommender()
        rec.build(str(self.path))
        return rec.recommend(query, zone=zone)

    def gate_assess(self, task_signature: str, risk_level: str = "normal") -> dict:
        """v1.6: 元认知门控评估"""
        gate = get_gate()
        decision = gate.assess(task_signature, risk_level=risk_level)
        return decision.to_dict()

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "total_entries": len(self.index),
            "storage_dir": str(self.path),
            "max_entries": self.max_entries,
        }
        # v1.2: 语义检索引擎状态
        try:
            engine = get_engine()
            if engine._index_built:
                stats["semantic_search"] = {
                    "doc_count": engine._doc_count,
                    "vocab_size": engine._vocab_size if hasattr(engine, '_vocab_size') else len(engine._vocab),
                }
        except Exception:
            pass
        # v1.3: 小世界网络状态
        try:
            graph = get_graph()
            if graph._built:
                gs = graph.get_stats()
                stats["experience_graph"] = {
                    "nodes": gs["nodes"],
                    "edges": gs["edges"],
                    "communities": gs["community_count"],
                    "shortcuts": gs["shortcuts"],
                    "avg_clustering": gs["avg_clustering"],
                }
        except Exception:
            pass
        return stats

    # ── 规则管理（与Experience记录独立存储） ─────────────────
    def _rules_dir(self) -> Path:
        p = self.path / "_rules"
        p.mkdir(exist_ok=True)
        return p

    def add_rule(self, rule: "Rule") -> str:
        """存储一条代码生成规则"""
        fp = self._rules_dir() / f"{rule.rule_id}.json"
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(rule.to_dict(), f, indent=2, ensure_ascii=False)
        return str(fp)

    def get_active_rules(self) -> "List[Rule]":
        """获取所有活跃规则"""
        rules = []
        rd = self._rules_dir()
        if not rd.exists():
            return rules
        for f in sorted(rd.glob("*.json")):
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                rules.append(Rule.from_dict(data))
        return rules


# ── Rule 类型（代码生成规则，非修复记录） ──────────────────────────
@dataclass
class Rule:
    """代码生成规则条目"""
    rule_id: str
    principle: str
    guidelines: list
    language_bindings: dict
    prompt_template: str
    source: str
    success_count: int = 0
    fail_count: int = 0
    created_at: str = ""

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "principle": self.principle,
            "guidelines": self.guidelines,
            "language_bindings": self.language_bindings,
            "prompt_template": self.prompt_template,
            "source": self.source,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            rule_id=d["rule_id"],
            principle=d["principle"],
            guidelines=d["guidelines"],
            language_bindings=d["language_bindings"],
            prompt_template=d["prompt_template"],
            source=d.get("source", ""),
            success_count=d.get("success_count", 0),
            fail_count=d.get("fail_count", 0),
            created_at=d.get("created_at", ""),
        )

    def record_success(self):
        self.success_count += 1

    def record_fail(self):
        self.fail_count += 1


_default_store = None
def get_store() -> ExperienceStore:
    global _default_store
    if _default_store is None:
        _default_store = ExperienceStore()
    return _default_store
