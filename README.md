# Paladin — AI-Native 应用脚手架

> **AI-Native, not AI-Powered.**
> 模型是第一等公民，就像数据库在传统架构中的地位一样。

---

## 哲学

AI-Powered 是在现有系统上外挂 AI。AI-Native 是从零开始，为 AI 而建。

| AI-Powered | AI-Native |
|-----------|-----------|
| 在现有架构上加一个 AI 层 | 架构以模型为核心设计 |
| 开发者写逻辑，模型做补丁 | 开发者调度能力，模型做决策 |
| 多仓库，人类工程师友好 | Monorepo，AI 编程助手友好 |
| 手动管理 Prompt | 内建 Prompt 编排与路由 |

Paladin 属于后者。

## 五支柱设计

| 支柱 | Paladin 的对应 |
|------|-------------|
| 可靠性 | 内建模型篱笆（缓存/路由/监控），生产级默认 |
| 卓越性 | 指挥官-调度官架构，决策与执行分离 |
| 可进化性 | 模型适配器可插拔，新增模型零改动 |
| 自给自足 | 零外部框架依赖（无 LangChain / LlamaIndex） |
| 可验证性 | 脚手架生成的每个文件都有独立测试入口 |

## 架构

```
┌──────────┐
│ commander/  │  ← LLM 驱动决策层（意图识别→任务拆解→编排）
├──────────┤
│ dispatcher/ │  ← 确定性路由层（动态路由→负载均衡→状态监控）
├──────────┤
│ models/     │  ← 模型篱笆（缓存→路由→监控，三层防护）
├──────────┤
│ adapters/   │  ← 模型适配器（DeepSeek / OpenAI / 国产大模型）
├──────────┤
│ app.py      │  ← 入口 (AIApp 实例)
└──────────┘
```

## 快速开始

```bash
# 安装
pip install paladin-ai

# 初始化项目
paladin init my_project
cd my_project

# 启动
python app.py
```

## 原则

1. GenAI-Native：五大设计支柱贯穿整个脚手架
2. 指挥官-调度官：思考与执行分离，永不意图漂移
3. Monorepo：AI 编程助手（Cursor 等）打开项目即见全貌
4. 零框架依赖：不 import langchain / llamaindex，内建替代
