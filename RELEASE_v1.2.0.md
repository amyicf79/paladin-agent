# v1.2.0 — 语义检索 + 经验库去重

## 📌 概述
本次更新将 Paladin 经验库从"关键词标签匹配"跃迁至"语义理解"时代，同时偿还了 generated_tools 的技术债务。

## 🚀 核心升级

### 1. 语义检索引擎 — `semantic_search.py`（全新重写）
- **算法**: 字n-gram TF-IDF + 余弦相似度（纯标准库，零外部依赖）
- **能力**: 中英文混合查询、自动构建/增量更新索引
- **对比**:
  - 旧版: `_INTENT_MAP` 标签匹配（"分析"→["parse","extract"...] 硬编码映射）
  - v1.2: 字符级bigram/trigram TF-IDF向量化，语义相似度排序
- **效果**:
  - `读取CSV文件` → `read_csv_file` (0.75) `csv_row_count` (0.13)
  - `检查URL状态` → `check_url_status` (0.26) `extract_title` (0.16)

### 2. generated_tools 去重 — 技术债务偿还
- **清理前**: 60 个工具文件（13 组重复，`extract_email_domain` x5）
- **清理后**: 37 个唯一工具（保留每个工具的最新版本）
- **index.json**: 32→23 条目（移除 9 个失效引用 + 1 个孤立文件）

### 3. ExperienceStore 集成
- `find_similar()` 改用 SemanticSearch 引擎
- 构建查询: `error_type + error_message` → 语义检索 top-k 召回

### 4. StrategyOptimizer 增强
- `analyze()` 报告新增两项洞察:
  - `[semantic]` 语义检索能力（引擎类型、词汇量、索引数）
  - `[coverage]` 语义覆盖密度（平均每条经验的语义关联数）

## 🔧 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `semantic_search.py` | 🔄 重写 | 38行→200行+，标签匹配→TF-IDF语义检索 |
| `experience_store.py` | 🔧 修改 | find_similar() 接入语义引擎 |
| `strategy_optimizer.py` | 🔧 修改 | 报告增加2项语义洞察 |
| `__init__.py` | 📄 创建 | 导出 v1.2 接口 |
| `pyproject.toml` | 🔧 修改 | 1.1.0→1.2.0 |
| `generated_tools/` | 🧹 清理 | 60→37 文件（-23重复） |
| `experience_store/` | 🧹 清理 | index.json 32→23 |

## 📊 性能基线
- 索引构建: 18 条经验 / 1606 词汇量 / ~0.01s
- 单次检索: ~0.005s（18条规模 / O(n) 线性扩展）
- 内存占用: ~500KB（18条 / 词汇表+文档向量）

## 🔜 下一站
- v1.3: 压力测试（连续 3-5 个工具生成）
- v1.4: 多 LLM 后端支持（Ollama / Qwen）
