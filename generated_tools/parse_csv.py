def parse_csv(csv_text):
    """解析CSV文本为列表[dict]"""
    import csv, io
    reader = csv.DictReader(io.StringIO(csv_text))
    return [row for row in reader]
