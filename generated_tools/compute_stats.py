def compute_stats(values):
    """计算数值列表的统计量"""
    n = len(values)
    if n == 0: return {}
    s = sum(values)
    m = s / n
    var = sum((x-m)**2 for x in values) / n
    return {"count":n,"sum":round(s,2),"mean":round(m,2),"std":round(var**0.5,2)}
