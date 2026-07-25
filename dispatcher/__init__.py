"""dispatcher — 确定性路由层

调度官负责：
- 动态路由：根据任务类型选择正确的模型/处理器
- 负载均衡：在多个模型端点间分配请求
- 状态监控：追踪每个请求的执行状态

用法：
    from paladin.dispatcher import Dispatcher
    dp = Dispatcher()
    result = dp.route("chat", user_input)
"""
