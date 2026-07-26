def parse_csv_column(csv_path, column_name="value"):
    """解析CSV文件并提取某列数据"""
    import csv
    values = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if column_name in row:
                values.append(row[column_name])
    return {"column": column_name, "count": len(values), "values": values[:10]}
