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

## 🔌 架构扩展性

> Paladin 的核心扩展点只有两个：**Commander 的 TaskPlanner 接口** 和 **Dispatcher 的 ToolRegistry 接口**。只要实现这两个接口，你可以让 Paladin 控制无人机、操作工业机器人、或对接任何内部 ERP 系统——而三篱笆（Cache/Router/Watch）始终在背后守护成本与质量。
