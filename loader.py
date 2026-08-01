"""
loader.py v0.8 — 动态模块加载器（Tool Synthesis）

基于 importlib.util 零依赖热加载生成的工具代码。
支持单工具加载、批量加载、已加载缓存。
"""
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Callable


class ToolLoader:
    """动态加载生成的工具模块，零外部依赖"""

    def __init__(self, tool_dir: str = "generated_tools"):
        self.tool_dir = Path(tool_dir)
        self.tool_dir.mkdir(exist_ok=True)
        self._loaded_tools: Dict[str, Callable] = {}

    def load_tool(self, tool_name: str) -> Callable:
        """从文件加载单个工具，返回可调用函数"""
        # 检查是否已加载
        if tool_name in self._loaded_tools:
            return self._loaded_tools[tool_name]

        filepath = self.tool_dir / f"{tool_name}.py"
        if not filepath.exists():
            # 检查带序号的变体（codegen.py 生成时如果有同名会加 _1, _2）
            candidates = sorted(self.tool_dir.glob(f"{tool_name}_*.py"))
            if not candidates:
                raise FileNotFoundError(
                    f"工具文件不存在: {filepath}（及 {tool_name}_*.py 变体）"
                )
            filepath = candidates[-1]  # 取最新编号

        # 动态导入
        spec = importlib.util.spec_from_file_location(tool_name, filepath)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载模块 spec: {filepath}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[tool_name] = module
        spec.loader.exec_module(module)

        # 获取函数：优先同名函数，其次第一个非下划线开头的可调用对象
        if hasattr(module, tool_name):
            func = getattr(module, tool_name)
        else:
            func = None
            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(module, attr_name)
                if callable(attr):
                    func = attr
                    break
            if func is None:
                raise AttributeError(f"模块 {tool_name} 中未找到可调用函数")

        self._loaded_tools[tool_name] = func
        return func

    def load_all_tools(self) -> Dict[str, Callable]:
        """加载 generated_tools 目录下的所有工具"""
        tools = {}
        for filepath in sorted(self.tool_dir.glob("*.py")):
            if filepath.stem.startswith("_"):
                continue
            # 跳过带编号的变体（只加载主文件）
            if re.search(r"_\d+$", filepath.stem):
                continue
            try:
                tools[filepath.stem] = self.load_tool(filepath.stem)
            except Exception as e:
                print(f"加载 {filepath.stem} 失败: {e}")
        return tools

    def list_tools(self) -> list:
        """列出已生成的所有工具名称"""
        seen = set()
        result = []
        for f in sorted(self.tool_dir.glob("*.py")):
            if f.stem.startswith("_"):
                continue
            # 去重：只保留主文件名（去掉 _1, _2 后缀）
            base = re.sub(r"_\d+$", "", f.stem)
            if base not in seen:
                seen.add(base)
                result.append(base)
        return result

    def clear_cache(self):
        """清空已加载缓存（下次调用会重新从文件加载）"""
        self._loaded_tools.clear()


# 延迟导入 re（仅 load_all_tools / list_tools 使用）
import re
