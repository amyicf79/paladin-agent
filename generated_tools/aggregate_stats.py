def aggregate_stats(datasets):
    """聚合多个数据集的统计结果"""
    results = []
    for name, values in datasets.items():
        n = len(values)
        if n == 0: continue
        s = sum(values)
        m = s / n
        results.append({"name":name,"count":n,"sum":round(s,2),"mean":round(m,2)})
    return results
