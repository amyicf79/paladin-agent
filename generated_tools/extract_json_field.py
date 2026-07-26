def extract_json_field(json_data, field_path):
    """从JSON数据中提取指定字段"""
    import json
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data
    keys = field_path.split(".")
    result = data
    for k in keys:
        if isinstance(result, dict):
            result = result.get(k, {})
        else:
            return None
    return result if result != {} else None
