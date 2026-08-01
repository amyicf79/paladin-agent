# Paladin v1.3 — 小世界拓扑

> 更新日期: 2026-07-27 21:15+
> 思维模型: 🌐 **系统思维** — 看一件事不看它本身，而看它所在的系统

## 📌 概述
v1.3 将经验库从扁平列表重构为小世界网络，引入社区检测和捷径路由。这是"系统思维"模型的工程落地——不优化单个经验，而优化经验之间的关系结构。

## 🚀 核心升级

### 1. 小世界网络引擎 — `experience_graph.py`（新建）
| 组件 | 说明 |
|------|------|
| `ExperienceNode` | 图节点（工具名、社区归属、捷径标记、度数） |
| `ExperienceGraph` | 主引擎（建图、社区检测、捷径发现、拓扑检索） |
| `get_graph()` / `rebuild_graph()` | 便捷接口 |

### 2. 社区检测（Louvain-like 贪心）
- 基于语义相似度建边（阈值 0.15）
- 自动聚类：同工具变体、同类功能归入同一社区
- v1.3 基线: 18节点 / 14边 / 17社区 / 1捷径

### 3. 捷径发现（跨社区桥梁）
- 跨社区边按权重排序，top 3% 标记为"桥梁"
- 桥梁经验在检索中获得 +0.10 加成
- 作用：连接不同功能模块，实现跨域推理

### 4. 拓扑感知检索 — `topo_search(query)`
排序规则：
```
同社区 + 高相似度  >  桥梁经验  >  同社区低相似度  >  跨社区
     +0.15                 +0.10                +0.05 (高连通节点)
```

### 5. 集成到 ExperienceStore
- `topo_find_similar()` — 拓扑排序的相似经验查找
- `get_stats()` 增加图状态: nodes/edges/communities/shortcuts/clustering

### 6. StrategyOptimizer 拓扑洞察
新增两项洞察：
- `[topology]` 小世界网络结构（节点/边/社区/捷径/聚类系数）
- `[community]` 跨功能社区（多工具类型的混合社区，经验可交叉复用）

## 📊 验证数据

```

topo_find_similar("parse CSV column"):
  🔀[1.102 comm=6] parse_csv_column  (捷径节点)
  🔀[0.849 comm=14] parse_csv_column (捷径节点)
    [0.131 comm=16] csv_row_count     (同社区外推)
    [0.121 comm=7]  read_csv_file     (跨社区)
    [0.111 comm=11] extract_title     (跨社区)

ExperienceGraph: 18N 14E 17C 1S
  平均度=1.56, 聚类系数=0.287, 边密度=0.0915

StrategyOptimizer 新增:
  [topology ] 18节点 14边 17社区 | 捷径1条(7.1%) | 聚类系数0.287
  [community] 社区8(read_json_file,write_file) — 跨功能社区
```

## 📋 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `experience_graph.py` | 🆕 新建 | 小世界网络引擎 (~300行) |
| `experience_store.py` | 🔧 修改 | +topo_find_similar, 路径绝对化, get_stats增强 |
| `strategy_optimizer.py` | 🔧 修改 | +topology/community 洞察 |
| `__init__.py` | 🔧 修改 | 导出 v1.3 接口 |
| `pyproject.toml` | 🔧 修改 | 1.2.1→1.3.0 |

## 🧠 与思维模型的关系

| 思维模型 | 工程对应 | 状态 |
|----------|----------|------|
| 🪒 奥卡姆剃刀 | 最小工具原则 + 工具清理 | ✅ v1.0~v1.2.1 |
| 🔬 第一性原理 | 反事实增益 + 语义检索 | ✅ v1.2~v1.2.1 |
| 🌐 **系统思维** | **小世界拓扑** | **✅ v1.3** |
| 🧭 能力圈 | 认知分区 | 🔜 v1.4 |
| 🔄 逆向思维 | 元认知门控 | 🔜 v1.5 |
| 📈 复利思维 | 熵预算与耗散 | 🔜 v1.6 |