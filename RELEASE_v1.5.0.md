# Paladin v1.5 — 双路径推荐

> 更新日期: 2026-07-27 21:30
> 思维模型: 🌐 **系统思维** + 🧭 **能力圈** — 参考与探索的平衡

## 🚀 新增

### 双路径推荐引擎 — dual_path.py
| 组件 | 说明 |
|------|------|
| 参考路径 | 只使用 validated 高置信经验，保守可靠 |
| 探索路径 | 结合新经验/捷径/低分经验，发现潜力方案 |
| ε-greedy 平衡 | 熟练区 ε=0.05，困惑区 ε=0.20，缺失区 ε=0.40 |
| 策略对齐 | 计算双路径重叠工具的分数差异，对齐度 >0.7 可安全混合 |
| merge() | 参考优先+探索补充的去重合并 |

## 📦 变更
- `dual_path.py` 🆕 — 双路径推荐引擎
- `experience_store.py` 🔧 — +dual_path_recommend
- `strategy_optimizer.py` 🔧 — +dual_path 洞察
- `experience_graph.py` 🔧 — +get_node_community/is_shortcut
- `pyproject.toml` — 1.4.0→1.5.0
