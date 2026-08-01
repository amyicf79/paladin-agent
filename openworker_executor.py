# -*- coding: utf-8 -*-
"""
openworker_executor.py — OpenWorker 真实执行钩子

将 Paladin 门控放行的 action 转化为真实桌面操作：
  - 文件操作: 创建/读取/写入/删除文件
  - 日历操作: (占位)
  - 邮件操作: (占位)
"""

from __future__ import annotations
import os, json, datetime, shutil, tempfile
from typing import Dict, Any, Optional

# 注册命令映射
COMMAND_REGISTRY = {
    "write_file": "写入文件",
    "read_file": "读取文件", 
    "list_dir": "列出目录",
    "create_dir": "创建目录",
    "backup_file": "备份文件",
    "clean_dir": "清理目录",
}

def execute(action: str, params: dict) -> dict:
    """执行真实桌面操作"""
    result = {"action": action, "status": "pending", "output": "", "error": ""}
    try:
        if action == "write_file":
            path = params.get("path", os.path.join(tempfile.gettempdir(), "paladin_output.txt"))
            content = params.get("content", "")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            result.update({"status": "success", "output": f"已写入 {len(content)} 字符到 {path}"})

        elif action == "read_file":
            path = params.get("path", "")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            result.update({"status": "success", "output": content[:500]})

        elif action == "list_dir":
            path = params.get("path", os.path.expanduser("~"))
            files = [f for f in os.listdir(path) if not f.startswith(".")][:20]
            result.update({"status": "success", "output": f"共 {len(files)} 项: {', '.join(files[:10])}"})

        elif action == "create_dir":
            path = params.get("path", "")
            os.makedirs(path, exist_ok=True)
            result.update({"status": "success", "output": f"目录已创建: {path}"})

        elif action == "backup_file":
            path = params.get("path", "")
            if os.path.exists(path):
                backup = path + ".bak." + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                shutil.copy2(path, backup)
                result.update({"status": "success", "output": f"已备份到: {backup}"})
            else:
                result.update({"status": "error", "error": f"文件不存在: {path}"})

        elif action == "clean_dir":
            path = params.get("path", tempfile.gettempdir())
            pattern = params.get("pattern", "")
            count = 0
            for f in os.listdir(path):
                if pattern in f:
                    try:
                        os.remove(os.path.join(path, f))
                        count += 1
                    except: pass
            result.update({"status": "success", "output": f"已清理 {count} 个文件"})

        else:
            result.update({"status": "error", "error": f"未知动作: {action}"})
    except Exception as e:
        result.update({"status": "error", "error": str(e)})
    return result


def get_available_actions() -> list:
    return list(COMMAND_REGISTRY.keys())
