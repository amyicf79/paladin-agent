"""
v0.9.2 — 自修复叶片
职责：根据 ValidationReport 中的失败信息，调用 LLM 生成修正后的代码。
零依赖，仅依赖标准库 + 外部注入的 adapter。
"""

import ast
from dataclasses import dataclass, field
from typing import Optional, List, Any

from .validator import ValidationReport


@dataclass
class RepairResult:
    original_code: str
    repaired_code: Optional[str] = None
    success: bool = False
    attempts: int = 0
    error_message: Optional[str] = None
    patch_notes: List[str] = field(default_factory=list)


class Repairer:
    def __init__(self, adapter=None, max_attempts: int = 2):
        self.adapter = adapter
        self.max_attempts = max_attempts

    def repair(self, tool_name: str, code: str, report: ValidationReport) -> RepairResult:
        result = RepairResult(original_code=code)

        if report.all_passed:
            result.success = True
            result.repaired_code = code
            result.patch_notes.append("验证已通过，无需修复")
            return result

        if self.adapter is None:
            result.error_message = "无 LLM 适配器，无法自动修复"
            return result

        failed_cases = [r for r in report.results if not r.passed]
        error_context = "\n".join([
            f"测试 '{r.test_name}': 期望 {r.expected_output}, "
            f"实际 {r.actual_output}, 错误: {r.error_message}"
            for r in failed_cases[:3]
        ]) if failed_cases else report.summary or "未知验证错误"

        for attempt in range(1, self.max_attempts + 1):
            result.attempts = attempt
            try:
                repaired = self._call_repair_llm(tool_name, code, error_context, attempt)
                if self._is_valid_python(repaired):
                    result.repaired_code = repaired
                    result.success = True
                    result.patch_notes.append(f"第 {attempt} 次修复成功")
                    break
                result.patch_notes.append(f"第 {attempt} 次修复的代码仍包含语法错误")
            except Exception as e:
                result.patch_notes.append(f"第 {attempt} 次修复异常: {e}")

        if not result.success:
            result.error_message = f"经过 {self.max_attempts} 次尝试，自动修复失败"
        return result

    def _call_repair_llm(self, tool_name: str, code: str, error_context: str, attempt: int) -> str:
        prompt = f"""修复以下 Python 函数的错误。

函数名: {tool_name}
原始代码:
```python
{code}
```
失败信息:
{error_context}

只返回修复后的完整 Python 代码，不要解释。"""
        response = self.adapter.chat([
            {"role": "system", "content": "你是 Python 代码修复专家，只输出修复后的代码。"},
            {"role": "user", "content": prompt}
        ])
        content = response.get("content", "")
        # 提取代码块（如果有）
        if "```python" in content:
            content = content.split("```python")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return content.strip()

    @staticmethod
    def _is_valid_python(code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False


def repair_tool(tool_name: str, code: str, report: ValidationReport, adapter=None) -> RepairResult:
    """快捷函数：一行修复"""
    return Repairer(adapter).repair(tool_name, code, report)
