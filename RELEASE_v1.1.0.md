# v1.1.0 — CLI 入口补全 + 压力测试通过

## 📌 概述
本次更新补全了 Paladin 最关键的"门面"入口——`paladin run` 命令，并完成了首次压力测试验证。自此，Paladin 可以从一条自然语言命令出发，完整跑通"规划 → 生成 → 验证 → 修复 → 持久化"全链路。

## 🚀 新增功能

### `paladin run` CLI 命令
支持直接输入自然语言任务描述，触发完整的 Planner → Executor → Codegen → Validator → Repair → ExperienceStore 端到端闭环。

示例：
```bash
paladin run "生成一个随机密码生成器"
```

支持参数：
- `--max-iterations N` — 最大迭代轮次（默认 3）
- `--mock` — 使用内置 mock 后端（无需 API Key）
- `--quiet` — 简约输出模式

### `paladin optimize` 命令增强
新增动作类型覆盖度分析，可识别经验库中已覆盖的 action 类型（如 generate/parse），帮助判断能力缺口。
```bash
paladin optimize --store experience_store
```

## 🧰 新增自动生成工具（12 个）
经验库从 22 条扩展至 32 条，新增工具包括：
- `generate_ai_commentary` — AI 治理短评生成
- `parse_csv_column` — CSV 列解析
- `count_word_frequency` — 词频统计
- `extract_json_field` — JSON 字段提取
- `generate_random_token` — 随机 Token 生成
- `validate_column` — 列数据校验
- `compute_stats` — 统计计算
- `filter_outliers` — 异常值过滤
- `aggregate_stats` — 聚合统计
- 以及其他 3 个辅助工具

## ✅ 压力测试通过
首次复合任务压力测试完成：
"抓取页面标题 → 提取摘要 → 保存为 CSV" 三个工具连续生成，依赖链完整，全部通过验证。

## 🔧 修复
- 经验库 Schema 字段统一：`tool` → `tool_name`
- `load_experiences()` 兼容旧格式，避免 KeyError
- schema 修复后 optimizer 统计正确：19 条经验 / 18 个工具
- StrategyInsight 参数补全 `recommendation` 字段
