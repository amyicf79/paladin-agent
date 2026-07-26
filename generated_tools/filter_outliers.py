def filter_outliers(values, threshold=2.0):
    """用标准差过滤异常值"""
    n = len(values)
    if n == 0: return []
    m = sum(values)/n
    v = sum((x-m)**2 for x in values)/n
    s = v**0.5
    return [x for x in values if abs(x-m) <= threshold*s]
