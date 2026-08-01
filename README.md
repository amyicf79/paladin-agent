# Paladin — AI-Native Application Scaffolding

> **零依赖脚手架 · 工具合成 · 沙箱验证** / *Zero-dependency scaffolding · Tool synthesis · Sandbox validation*

Paladin is the open-source engineering core behind [IXNO](https://ixno.com) — a gene-pool powered AI orchestration framework. It treats the **model as a first-class citizen** and provides a scaffolding + validation toolchain for building robust AI agents.

Paladin 是 IXNO 基因池背后的开源工程内核。它把**模型作为第一等公民**，为构建健壮的 AI Agent 提供脚手架 + 验证工具链。

---

## ✨ Features / 特性

| English | 中文 |
|---|---|
| Zero-dependency scaffolding (stdlib only) | 零依赖脚手架（仅标准库） |
| Tool synthesis via LLM codegen | 基于 LLM 代码生成的工具合成 |
| Sandboxed tool validation | 沙箱工具验证 |
| Multi-model adapters (DeepSeek / Ollama / Qwen) | 多模型适配器 |
| Entropy budget & metacognition gating | 熵预算与元认知门控 |
| Strategy marketplace & experience graph | 策略市场与经验图谱 |

## 🚀 Quick Start / 快速开始

### Installation / 安装

```bash
git clone https://github.com/your-org/paladin.git
cd paladin
pip install -e .
```

### Minimal usage / 最小用法

```python
from paladin import create_app
app = create_app()
# ... then register tools, run validation
```

### CLI

```bash
paladin --help        # view available commands
paladin validate <tool_path>   # sandbox-validate a synthesized tool
```

## 🧩 Architecture / 架构

```
paladin/
├── codegen.py          # LLM-driven tool synthesis / 工具合成
├── validator.py        # sandbox validation / 沙箱验证
├── loader.py           # zero-dependency loader / 零依赖加载器
├── cli.py              # command-line interface
├── adapters/           # model adapters (deepseek/ollama/qwen)
├── commander/          # planner + protocol
├── dispatcher/         # executor
├── models/             # cache, router, watch
└── docs/               # ARCHITECTURE, ECOSYSTEM, TREE_METHODOLOGY
```

## 🔧 Configuration / 配置

Model keys are read from **environment variables** — never hardcoded:

```bash
export DEEPSEEK_API_KEY="your-key-here"   # optional, for DeepSeek adapter
```

Or via `paladin.toml`:

```toml
[models]
deepseek_api_key = ""   # leave empty to read from env
```

## 🤝 Ecosystem / 生态

- **IXNO Cloud** — the private gene pool API (search/push) that Paladin connects to. Register at [ixno.com](https://ixno.com). / 私有基因池 API，Paladin 连接的数据层。
- **ixno-sdk** (Python) — thin client for the IXNO Cloud API. / IXNO 云端 API 的 Python 轻客户端。
- **ixno-sdk-ts** (TypeScript) — same client for the TS ecosystem.

## 📄 License / 许可

See [LICENSE](LICENSE).

---

*Paladin · AI-Native Scaffolding · model as first-class citizen*
