def validate_column(rows, column, min_val=0, max_val=100):
    """验证列数据是否在范围内"""
    issues = []
    for i, row in enumerate(rows):
        val = float(row.get(column, 0))
        if val < min_val or val > max_val:
            issues.append({"row":i+1,"val":val})  # <= 修复
    return issues
