# Paladin 架构文档

> AI-Native 应用脚手架 — 模型是第一等公民

---

## 🛡️ 核心：三篱笆闭环（已锁死，永不重构）

```
用户输入 → [Cache] → 命中? → 直接返回
                ↓ 未命中
           [Router] → 质量分 < 阈值? → 升Pro模型
                ↓                    
           [Watch] → 记录成本 → 写入 costs.json
```

三篱笆作为 Paladin 的"神圣光环（Divine Aura）"，未来只允许配置化调参，不允许逻辑重构。

## 📡 触角：指挥官 + 调度官（Phase 2）

| 模块 | 职责 | 扩展方向 |
|------|------|---------|
| Commander | 决策层 — LLM驱动的意图识别/任务拆解/编排 | 思维链(CoT)编排器 + YAML任务树 |
| Dispatcher | 执行层 — 确定性代码逻辑的路由/负载均衡 | 多智能体调度池 + 熔断降级 |

**扩展点：** 实现 `TaskPlanner` 和 `ToolRegistry` 接口即可扩展。

## 🏗️ 纵深

### 适配器层（横向）
- `adapters/deepseek.py` ✅ 已有
- `adapters/ollama.py`, `adapters/qwen.py`, `adapters/vision.py` ⬜

### 数据飞轮（纵向）
- watch.py 成本监控 → 质量回溯 → Bad Case 数据集 → SFT 数据沉淀

### 部署形态
- CLI 模式：`paladin init` ✅ 已有
- Server 模式：`paladin serve` → FastAPI 网关 ⬜
- Sidecar 模式：`paladin sidecar --attach PID` ⬜

---

## 🚀 三阶跃迁（v0.1 → v1.0 路线图）

```
┌─────────────────────────────────────────────────────────────────┐
│                       Paladin 三阶跃迁                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  第一阶段          第二阶段                第三阶段             │
│  (v0.1-v0.7)      (v0.8 当前)             (v1.0 目标)          │
│  "会执行"          "会创作"                "会进化"             │
│                                                                  │
│  ┌──────────┐     ┌──────────────┐       ┌─────────────────┐    │
│  │ 调用工具  │  →  │ 生成工具     │   →   │ 优化工具        │    │
│  │ 编排任务  │     │ 热加载工具   │       │ 自我迭代        │    │
│  │ 成本篱笆  │     │ 持久化工具   │       │ 架构即运行时    │    │
│  └──────────┘     └──────────────┘       └─────────────────┘    │
│        ↑                  ↑                      ↑               │
│   人类写工具          AI 写工具              AI 优化自身         │
└─────────────────────────────────────────────────────────────────┘
```

### 第一阶段：会执行（v0.1-v0.7 ✅ 已锁定）

| 版本 | 核心能力 | 状态 |
|------|---------|:----:|
| v0.1-v0.5 | 三篱笆（Cache/Router/Watch）+ 指挥官/调度官 + 自主编排 | ✅ |
| v0.6 | 演示靶场：零依赖终端可视化（Chain/Parallel/Branch） | ✅ |
| v0.7 | 配置系统：paladin.toml 三层优先级 + planner.backend 桥接 | ✅ |

### 第二阶段：会创作（v0.8 🏗️ 当前）

| 模块 | 职责 | 状态 |
|------|------|:----:|
| `commander/protocol.py` | `MetaAction` 元操作协议 + `ExecutionPlan.meta_actions` | ✅ |
| `codegen.py` | 工具代码生成器（mock 模板 + real LLM 双模式，零依赖） | ✅ |
| `loader.py` | 动态模块加载器（`importlib.util`，零依赖热加载） | ✅ |
| `dispatcher/executor.py` | `execute()` 先处理 meta_actions → 生成 → 加载 → 注册 → 执行 | ✅ |
| `generated_tools/` | 持久化目录，新工具永久保存 | ✅ |
| 场景 5: 工具合成 | demo 覆盖 codegen → save → load → register → execute 全流程 | ✅ |

**用户视角变化：**
```
v0.7:  人类写工具 → Paladin 编排 → 执行
v0.8:  人类描述需求 → Paladin 生成工具 → 执行 → 持久化
```

### 第三阶段：会进化（v1.0 🎯 目标）

- **工具优化**：Planner 检测到低频/低效工具 → 自动合并或重构
- **自我迭代**：Planner 修改自己的规划策略（`planner.backend` 热切换）
- **架构即运行时**：运行时动态调整篱笆参数（Cache TTL / Router 阈值 / Watch 告警规则）
- **多智能体**：Executor 调度多个 Planner 实例协作

---

## 🔌 架构扩展性

> Paladin 的核心扩展点只有两个：**Commander 的 TaskPlanner 接口** 和 **Dispatcher 的 ToolRegistry 接口**。只要实现这两个接口，你可以让 Paladin 控制无人机、操作工业机器人、或对接任何内部 ERP 系统——而三篱笆（Cache/Router/Watch）始终在背后守护成本与质量。
