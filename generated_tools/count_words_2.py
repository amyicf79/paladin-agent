def count_words(expr: str) -> str:
    """执行数学计算（自动生成）"""
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算失败: {e}"
