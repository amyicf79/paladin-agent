"""commander — LLM 驱动决策层

指挥官负责：
- 意图识别：将用户输入翻译为结构化任务
- 任务拆解：将复杂任务分解为子任务
- 编排：决定子任务执行顺序和依赖

用法：
    from paladin.commander import Commander
    cmd = Commander(model="deepseek-chat")
    plan = cmd.decompose("分析这份数据并生成图表")
"""
