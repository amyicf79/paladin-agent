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
        self.path = Path(self.storage_dir)
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
        results = []
        candidates = []
        for entry in self.index:
            if entry["error_type"] == error_type:
                candidates.append(entry["file"])
        if tool_name:
            candidates = [f for f in candidates if f.startswith(tool_name)]

        for filename in candidates[:5]:
            filepath = self.path / filename
            if not filepath.exists():
                continue
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                msg_words = set(error_message.lower().split())
                exp_words = set(data.get("error_message", "").lower().split())
                overlap = len(msg_words & exp_words)
                if overlap > 0:
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

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self.index),
            "storage_dir": str(self.path),
            "max_entries": self.max_entries
        }


_default_store = None
def get_store() -> ExperienceStore:
    global _default_store
    if _default_store is None:
        _default_store = ExperienceStore()
    return _default_store
