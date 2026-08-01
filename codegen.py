"""
codegen.py v0.8 — 工具代码生成器（Tool Synthesis）

让 Planner 不仅能编排工具，还能在运行时生成工具代码。
mock 模式用模板生成（零依赖）；real 模式由 LLM 生成（v1.0 增强）。

Paladin 零依赖约束：所有模板使用 Python 标准库，不引入 requests/bs4 等第三方包。
"""
import os
import re
from typing import Optional, Dict, Any
from .commander.protocol import MetaAction


class CodeGenerator:
    """工具代码生成器：根据自然语言描述生成 Python 函数代码"""

    def __init__(self, backend: str = "mock", adapter=None):
        self.backend = backend
        self.adapter = adapter  # 当 backend == "real" 时使用

    def generate(self, meta: MetaAction) -> str:
        """根据 MetaAction 生成 Python 函数代码"""
        if meta.action_type != "generate_tool":
            raise ValueError(f"不支持的操作类型: {meta.action_type}")

        if self.backend == "mock":
            return self._mock_generate(meta)
        else:
            return self._llm_generate(meta)

    def _mock_generate(self, meta: MetaAction) -> str:
        """Mock 模式：模板生成（使用标准库，零额外依赖）"""
        func_name = self._sanitize_name(meta.target_name)
        desc = meta.description

        if "标题" in desc or "title" in desc.lower():
            code = f'''def {func_name}(url: str) -> str:
    """从 URL 提取标题（自动生成，零依赖）"""
    from urllib.request import urlopen
    from html.parser import HTMLParser

    class _TitleParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self._in_title = False
            self._title = ""

        def handle_starttag(self, tag, attrs):
            if tag == "title":
                self._in_title = True

        def handle_endtag(self, tag):
            if tag == "title":
                self._in_title = False

        def handle_data(self, data):
            if self._in_title:
                self._title += data

    try:
        resp = urlopen(url, timeout=5)
        html = resp.read().decode("utf-8", errors="ignore")
        parser = _TitleParser()
        parser.feed(html)
        return parser._title.strip() or "无标题"
    except Exception as e:
        return f"提取失败: {{e}}"
'''
        elif "新闻" in desc or "news" in desc.lower() or "搜索" in desc:
            code = f'''def {func_name}(query: str) -> str:
    """搜索相关新闻（自动生成）"""
    return f"搜索 '{{query}}' 的结果：模拟新闻1，模拟新闻2"
'''
        elif "计算" in desc or "calc" in desc.lower():
            code = f'''def {func_name}(expr: str) -> str:
    """执行数学计算（自动生成）"""
    try:
        result = eval(expr, {{"__builtins__": {{}}}}, {{}})
        return f"计算结果: {{result}}"
    except Exception as e:
        return f"计算失败: {{e}}"
'''
        elif "文件" in desc or "file" in desc.lower() or "读" in desc:
            code = f'''def {func_name}(filepath: str) -> str:
    """读取文件内容（自动生成）"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取失败: {{e}}"
'''
        else:
            code = f'''def {func_name}(**kwargs) -> str:
    """{desc}（自动生成占位）"""
    return f"执行 {{kwargs}}：功能待实现"
'''
        return self._with_principle(code)

    def _with_principle(self, body: str) -> str:
        """前置【极简工具原则】注释"""
        try:
            from .experience_store import get_store
            rules = get_store().get_active_rules()
            for r in rules:
                if r.guidelines:
                    header = "# 极简工具原则: " + r.guidelines[0] + "\n"
                    if header not in body:
                        body = header + body
            return body
        except Exception:
            return body

    def _llm_generate(self, meta: MetaAction) -> str:
        """Real 模式：由 LLM 生成代码（adapter 注入，零依赖标准库）"""
        if self.adapter is None:
            return self._mock_generate(meta)
        # 核调壳：注入宿主可调用工具清单，让生成的代码优先用宿主生态
        host_tools = getattr(self.adapter, "host_tools", None)
        host_hint = ""
        if host_tools:
            tools_desc = "\n".join(f"- {t}" for t in host_tools)
            host_hint = f"""宿主环境已提供以下工具，若任务需要，优先在生成的代码中调用它们(而非自己实现):
{host_tools}

"""
        prompt = f"""生成一个 Python 函数。

函数名: {meta.target_name}
功能: {meta.description}
{host_hint}
要求:
- 只返回完整可运行的 Python 代码，不要解释
- 用标准库或宿主提供的工具，不引入第三方包
- 函数签名清晰，参数有默认值"""
        try:
            response = self.adapter.chat([
                {"role": "system", "content": "你是 Python 代码生成专家，只输出代码。"},
                {"role": "user", "content": prompt}
            ])
            content = response.get("content", "")
            if "```python" in content:
                content = content.split("```python")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return self._with_principle(content.strip() or self._mock_generate(meta))
        except Exception:
            return self._mock_generate(meta)

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """将自然语言名称转为合法的 Python 函数名"""
        name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]', '_', name)
        if name and name[0].isdigit():
            name = "tool_" + name
        return name or "generated_tool"

    def save_to_file(self, code: str, tool_name: str, directory: str = "generated_tools") -> str:
        """将生成的代码保存到文件，返回文件路径"""
        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, f"{tool_name}.py")
        # 检查是否已有同名文件，避免覆盖用户修改
        if os.path.exists(filepath):
            base, ext = os.path.splitext(filepath)
            i = 1
            while os.path.exists(f"{base}_{i}{ext}"):
                i += 1
            filepath = f"{base}_{i}{ext}"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        return filepath
