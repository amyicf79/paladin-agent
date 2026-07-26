
<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License">
  <img src="https://img.shields.io/badge/status-v1.1.0--stable-brightgreen" alt="Version">
</p>

# Paladin

> 🌱 会执行 → 会创作 → 会进化
> 自进化 AI 智能体框架 | Python + DeepSeek | 零外部依赖

---

## 这是什么？

Paladin 让 LLM 在需要时**自动生成工具、验证它、注册它、下次复用它**，然后把整个过程记进经验库——越用越聪明。

---

## 核心能力

⚡ **自动工具合成**：发现能力缺口 → LLM 生成代码 → 验证 → 注册
🧠 **经验闭环**：每次执行都被记录，strategy_optimizer 基于经验做推荐
📦 **极简工具原则**：单文件、零分层，Token 消耗降低 70%+
🔧 **零依赖**：240 行跑通全闭环

---

## 实测数据

| 指标 | 传统模式 | Paladin 极简模式 | 提升 |
|------|---------|----------------|:----:|
| 代码质量分 | 60 | 80 | **+20** |
| 注释率 | 1.6% | 17.2% | **+15.6%** |
| Token 消耗（CSV 工具） | ~1200 | ~350 | **-71%** |
| 长函数数 | 1 (66行) | 0 | **清零** |

*测试项目：disabilities-employment (NestJS)*

---

## 快速开始

```python
from paladin import Paladin

paladin = Paladin()
paladin.run("提取这个网页的标题: https://example.com")
# 1. 发现缺工具 → 2. 生成 extract_title.py
# 3. 验证通过 → 4. 注册到工具库 → 5. 下次复用
```

### 安装

```bash
# 方式一：pip 安装（推荐）
pip install paladin

# 方式二：源码安装
git clone https://gitee.com/gz2026/paladin-agent.git
cd paladin-agent
pip install -e .
```

---

## 适用场景

- 快速构建 AI Agent 的工具库
- 遗留系统的 AI 化改造（自动生成适配工具）
- 代码库的自进化重构（AutoCodebase）
- 跨项目的经验复用与策略优化

---

## 架构概览

```
用户输入 → Planner → MetaAction → Executor → 工具注册 → 执行
                          ↓                          ↓
                     experience_store ← ← ← ← ← ← ← ←
                          ↓
                    strategy_optimizer → 下一次更聪明
```

---

## 路线图

- [x] **v1.0** — 跑通"生成→验证→修复→持久化"闭环
- [x] **v1.1** — 极简工具原则落地，Token 消耗降低 70%+
- [ ] **v1.2** — 语义检索（经验库升级）
- [ ] **v1.3** — 压力测试（连续 3-5 个工具生成）
- [ ] **v1.4** — 多 LLM 后端支持（Ollama / Qwen）

---

## 贡献

Issues 和 PR 请提交至 [Gitee](https://gitee.com/gz2026/paladin-agent/issues)

---

## 许可证

Apache 2.0
