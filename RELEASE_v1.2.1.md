# Paladin v1.2.1 — 阈值调优 + 信号确认 + ATR稳定性

> 更新日期: 2026-07-27 21:00+

## 📌 概述
针对 v1.2 线上运行的三个关键补丁：语义检索假阳性防控、事件信号抖动抑制、ATR仓位跳变保护。

## 🔧 Patch 1: 语义检索阈值调优 — `semantic_search.py`

### 新增: `get_score_distribution(query)` 
返回查询的全量相似度分布，用于监控和阈值调优：

| 指标 | 示例值 | 含义 |
|------|--------|------|
| `top1` | 0.2647 | 最高分 |
| `mean` | 0.0556 | 平均分（基线噪声） |
| `median` | 0.0 | 中位数（多数不相关） |
| `std` | 0.0870 | 分数离散度 |
| `significant_gaps` | [...] | 分数组间明显跳跃（用于选阈值） |
| `suggested_threshold` | 0.1 | 建议最低阈值 |

**效果**: `find_similar()` 可根据分布动态调整 min_score，避免"语义相近但功能不同"的误召回。

## 🔧 Patch 2: 事件信号确认机制 — `paladin_event_trigger.py`

### 新增: 信号确认状态机
```python
_confirm_signal(key, detected, confirm_count=2)
```

- **问题**: sector_rotation 和 analyst_upgrade 的 API 数据可能单次抖动
- **解决**: 连续2次检测到同一信号才输出 `signal=True`
- **验证**: 
  - 第1次调用 → `signal=False, confirmed=False` ✅ 被抑制
  - 第2次调用 → `signal=True, confirmed=True` ✅ 确认后触发
- 新增 `_reset_all_confirmations()` / `get_confirmation_stats()` 接口

## 🔧 Patch 3: ATR滚动窗口 + 稳定性监控 — `paladin_core.py`

### 新增: 滚动窗口 + 稳定性检测
| 场景 | 仓位上限 | 逻辑 |
|------|----------|------|
| 稳定低波(ATR<1%) | 0.1500 (满配) | 正常 |
| ATR突然跳升>50% | 0.0675 (降级) | 额外强制降档到≤0.45系数 |

- `atr_window` 参数可配（默认14）
- `_compute_atr_values()` 辅助函数可供外部调用
- 前后半窗口ATR对比：跳升>50% → `vol_factor = min(vol_factor, 0.45)`

## 📊 验证汇总

```
Patch1: get_score_distribution("读取CSV文件") -> top1=0.2647, suggested_threshold=0.1
Patch2: 第1次signal=False → 第2次signal=True (连续确认生效)
Patch3: 稳定场景limit=0.15 → 跳升场景limit=0.0675 (稳定性降级生效)
```

## 📋 文件变更

| 文件 | 影响 | 说明 |
|------|------|------|
| `paladin/semantic_search.py` | 根 | +get_score_distribution(), v1.2.1 |
| `hs_next/paladin/event_trigger.py` | HS | +确认状态机, 2个检测函数更新 |
| `hs_next/paladin/paladin_core.py` | HS | +滚动窗口+稳定性监控 |
| `hs_next/paladin/__init__.py` | HS | 导出新接口 |
