# -*- coding: utf-8 -*-
"""
semantic_search.py — v1.2 语义检索引擎

升级内容:
  - 从关键词标签匹配 → 字n-gram TF-IDF + 余弦相似度
  - 支持中英文混合查询
  - 自动构建/增量更新索引
  - 零外部依赖（纯标准库）
"""

import json
import os
import math
import re
from collections import Counter
from typing import List, Dict, Tuple, Optional


# ── 字符级分词 ─────────────────────────────────────────

def _char_ngrams(text: str, ngram_range: Tuple[int, int] = (2, 3)) -> List[str]:
    """将文本拆分为字符n-gram（中英文通用）"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', text)
    tokens = []
    for n in range(ngram_range[0], ngram_range[1] + 1):
        for i in range(len(text) - n + 1):
            tokens.append(text[i:i + n])
    return tokens


def _build_search_text(data: dict) -> str:
    """从经验条目构建搜索文本（含代码内容，丰富n-gram特征）"""
    parts = [
        data.get('tool_name', ''),
        data.get('error_type', ''),
        data.get('error_message', ''),
        data.get('problem_signature', ''),
        data.get('action', ''),
        data.get('tool', ''),
        # 加入代码内容以丰富n-gram特征
        data.get('original_code', '')[:500],
        data.get('repaired_code', '')[:500],
    ]
    return ' '.join(parts)


def _compute_idf(term_doc_count: Counter, n_docs: int) -> Dict[str, float]:
    """计算IDF值"""
    return {
        term: math.log((n_docs + 1) / (count + 1)) + 1
        for term, count in term_doc_count.items()
    }


def _l2_normalize(vec: List[float]) -> List[float]:
    """L2归一化"""
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        return [v / norm for v in vec]
    return vec


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """余弦相似度"""
    return sum(a * b for a, b in zip(v1, v2))


# ── 语义检索引擎 ─────────────────────────────────────

class SemanticSearch:
    """基于字n-gram TF-IDF的语义检索引擎

    用法:
        ss = SemanticSearch()
        ss.build_index("experience_store")
        results = ss.search("读取CSV文件并统计行数")
    """

    def __init__(
        self,
        ngram_range: Tuple[int, int] = (2, 3),
        max_features: int = 5000,
    ):
        self.ngram_range = ngram_range
        self.max_features = max_features
        self._index_built = False

        # 索引数据
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._doc_vectors: List[List[float]] = []
        self._doc_meta: List[dict] = []
        self._doc_count: int = 0

    def build_index(self, store_path: str) -> int:
        """从经验库目录构建检索索引，返回索引条目数"""
        base = os.path.dirname(os.path.abspath(__file__))
        store_dir = store_path if os.path.isabs(store_path) else os.path.join(base, store_path)

        if not os.path.isdir(store_dir):
            return 0

        # 加载所有经验条目（去重）
        docs: List[Tuple[str, dict]] = []
        seen_hashes: set = set()

        for fname in sorted(os.listdir(store_dir)):
            if not fname.endswith('.json') or fname == 'index.json':
                continue
            fp = os.path.join(store_dir, fname)
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                dedup_key = f"{data.get('tool_name','')}:{data.get('error_message','')[:50]}"
                if dedup_key in seen_hashes:
                    continue
                seen_hashes.add(dedup_key)
                docs.append((fname, data))
            except (json.JSONDecodeError, IOError):
                continue

        if not docs:
            return 0

        # Step 1: 统计词频与文档频率
        doc_term_freqs: List[Tuple[str, dict, Counter]] = []
        term_doc_count: Counter = Counter()

        for fname, data in docs:
            text = _build_search_text(data)
            tokens = _char_ngrams(text, self.ngram_range)
            tf = Counter(tokens)
            doc_term_freqs.append((fname, data, tf))
            for term in set(tokens):
                term_doc_count[term] += 1

        # Step 2: 构建词汇表
        n_docs = len(docs)
        sorted_terms = [t for t, _ in term_doc_count.most_common(self.max_features)]
        self._vocab = {term: idx for idx, term in enumerate(sorted_terms)}
        self._idf = _compute_idf(term_doc_count, n_docs)

        # Step 3: 构建文档向量
        self._doc_vectors = []
        self._doc_meta = []

        for fname, data, tf in doc_term_freqs:
            vec = [0.0] * len(self._vocab)
            for term, freq in tf.items():
                if term in self._vocab:
                    vec[self._vocab[term]] = freq * self._idf.get(term, 1.0)
            self._doc_vectors.append(_l2_normalize(vec))
            self._doc_meta.append({
                'filename': fname,
                'tool_name': data.get('tool_name', ''),
                'error_type': data.get('error_type', ''),
                'error_message': data.get('error_message', '')[:200],
                'action': data.get('action', ''),
                'success': data.get('success', True),
            })

        self._doc_count = len(docs)
        self._index_built = True
        return self._doc_count

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        tool_filter: Optional[str] = None,
    ) -> List[Dict]:
        """语义检索"""
        if not self._index_built or not self._doc_vectors:
            return []

        q_tokens = _char_ngrams(query, self.ngram_range)
        q_tf = Counter(q_tokens)
        q_vec = [0.0] * len(self._vocab)
        for term, freq in q_tf.items():
            if term in self._vocab:
                q_vec[self._vocab[term]] = freq * self._idf.get(term, 1.0)
        q_vec = _l2_normalize(q_vec)

        if not any(q_vec):
            return []

        results = []
        for idx, doc_vec in enumerate(self._doc_vectors):
            sim = _cosine_similarity(q_vec, doc_vec)
            if sim < min_score:
                continue
            meta = self._doc_meta[idx]
            if tool_filter and tool_filter not in meta.get('tool_name', ''):
                continue
            results.append({
                'filename': meta['filename'],
                'score': round(sim, 4),
                'tool_name': meta['tool_name'],
                'error_type': meta['error_type'],
                'error_message': meta['error_message'],
                'action': meta['action'],
                'success': meta['success'],
            })

        results.sort(key=lambda x: -x['score'])
        return results[:top_k]

    def get_score_distribution(self, query: str) -> dict:
        """v1.2.1: 查询相似度分布监控 — 返回全量分数分布用于调优"""
        if not self._index_built or not self._doc_vectors:
            return {"count": 0, "scores": [], "mean": 0, "median": 0, "std": 0}
        
        q_tokens = _char_ngrams(query, self.ngram_range)
        q_tf = Counter(q_tokens)
        q_vec = [0.0] * len(self._vocab)
        for term, freq in q_tf.items():
            if term in self._vocab:
                q_vec[self._vocab[term]] = freq * self._idf.get(term, 1.0)
        q_vec = _l2_normalize(q_vec)
        
        if not any(q_vec):
            return {"count": 0, "scores": [], "mean": 0, "median": 0, "std": 0}
        
        scores = []
        for doc_vec in self._doc_vectors:
            sim = _cosine_similarity(q_vec, doc_vec)
            scores.append(round(sim, 4))
        
        scores.sort(reverse=True)
        n = len(scores)
        mean = sum(scores) / n
        median = scores[n // 2] if n % 2 else (scores[n // 2 - 1] + scores[n // 2]) / 2
        variance = sum((s - mean) ** 2 for s in scores) / n
        std = round(variance ** 0.5, 4)
        
        # 找到明显的相似度间隙（用于建议阈值）
        gaps = []
        for i in range(1, min(10, n)):
            gap = scores[i - 1] - scores[i]
            if gap > 0.1:
                gaps.append({"rank": i - 1, "gap": round(gap, 4), 
                             "above": scores[i - 1], "below": scores[i]})
        
        return {
            "count": n,
            "top1": scores[0] if scores else 0,
            "top5": scores[:5] if len(scores) >= 5 else scores,
            "mean": round(mean, 4),
            "median": round(median, 4),
            "std": std,
            "significant_gaps": gaps[:3],  # 前3个明显间隙
            "suggested_threshold": max(0.1, scores[0] * 0.3) if scores else 0.1,
        }

    def get_stats(self) -> dict:
        """获取索引统计（v1.2.1: 含相似度分布基线）"""
        return {
            'engine': 'char_ngram_tfidf',
            'version': '1.2.1',
            'index_built': self._index_built,
            'doc_count': self._doc_count,
            'vocab_size': len(self._vocab),
            'ngram_range': list(self.ngram_range),
            'monitoring': {
                'has_score_distribution': True,
                'suggested_min_score': 0.1,
            }
        }


# ── 便捷函数（兼容旧接口） ─────────────────────────

_default_engine: Optional[SemanticSearch] = None


def get_engine() -> SemanticSearch:
    """获取默认检索引擎（单例）"""
    global _default_engine
    if _default_engine is None:
        _default_engine = SemanticSearch()
    return _default_engine


def semantic_search(query: str, store_path: str = "experience_store", top_k: int = 5) -> List[Dict]:
    """便捷检索函数（兼容旧接口）"""
    engine = get_engine()
    if not engine._index_built:
        engine.build_index(store_path)
    return engine.search(query, top_k=top_k)


# ── CLI 快速测试 ──────────────────────────────────────

if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "读取CSV文件"
    ss = SemanticSearch()
    n = ss.build_index("experience_store")
    print(f"索引构建完成: {n} 条经验, 词汇量 {len(ss._vocab)}")
    results = ss.search(q, top_k=5)
    print(f"\n查询: {q}")
    print(f"结果: {len(results)} 条")
    for r in results:
        print(f"  [{r['score']:.3f}] {r['tool_name']} | {r['error_message'][:60]}")
