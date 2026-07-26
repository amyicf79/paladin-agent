def read_csv_column(filepath: str) -> str:
    """读取文件内容（自动生成）"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取失败: {e}"
