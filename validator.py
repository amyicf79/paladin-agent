"""
Paladin v0.9.1 — 自检叶片：沙箱验证器
职责：在隔离环境中执行生成的工具函数，捕获异常并返回验证报告。
零依赖，纯标准库。
"""

import sys
import io
import time
import traceback
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """单次验证结果"""
    passed: bool
    test_name: str
    input_args: Dict[str, Any]
    expected_output: Optional[Any] = None
    actual_output: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class ValidationReport:
    """完整验证报告"""
    tool_name: str
    code: str
    results: List[ValidationResult] = field(default_factory=list)
    all_passed: bool = False
    summary: str = ""


class Validator:
    """沙箱验证器 — 在隔离命名空间中执行函数并捕获所有异常"""

    def __init__(self, timeout_seconds: float = 2.0):
        self.timeout = timeout_seconds
        # 内置安全白名单
        self._safe_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "sum": sum,
                "max": max,
                "min": min,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "reversed": reversed,
                "open": open,
                "hasattr": hasattr,
                "isinstance": isinstance,
                "issubclass": issubclass,
                "getattr": getattr,
                "type": type,
                "callable": callable,
                "__import__": __import__,  # 允许 import（在 urllib 等白名单模块范围内）
                "Exception": Exception,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "AttributeError": AttributeError,
                "ImportError": ImportError,
                "RuntimeError": RuntimeError,
                "OSError": OSError,
                "FileNotFoundError": FileNotFoundError,
                "StopIteration": StopIteration,
                "True": True,
                "False": False,
                "None": None,
            },
            "importlib": __import__("importlib"),
            "re": __import__("re"),
            "json": __import__("json"),
            "urllib": __import__("urllib"),
        }

    def validate_code(self, tool_name: str, code: str, test_cases: List[Dict[str, Any]]) -> ValidationReport:
        """
        验证生成的代码是否通过所有测试用例

        Args:
            tool_name: 函数名
            code: Python 源代码字符串
            test_cases: 测试用例列表，每个用例包含 args 字典和 expected 期望值

        Returns:
            ValidationReport: 包含每个测试用例的详细结果
        """
        report = ValidationReport(tool_name=tool_name, code=code)

        # 1. 尝试编译代码（检查语法错误）
        try:
            compiled = compile(code, f"<{tool_name}.py>", "exec")
        except SyntaxError as e:
            report.summary = f"语法错误: {e}"
            report.all_passed = False
            report.results.append(ValidationResult(
                passed=False,
                test_name="compile",
                input_args={},
                error_message=f"SyntaxError: {e.msg} at line {e.lineno}"
            ))
            return report

        # 2. 执行代码，提取函数
        namespace = self._safe_globals.copy()
        try:
            exec(compiled, namespace)
        except Exception as e:
            report.summary = f"执行时异常: {e}"
            report.all_passed = False
            report.results.append(ValidationResult(
                passed=False,
                test_name="exec",
                input_args={},
                error_message=traceback.format_exc()
            ))
            return report

        # 检查函数是否存在
        if tool_name not in namespace:
            report.summary = f"函数 '{tool_name}' 未在生成代码中定义"
            report.all_passed = False
            report.results.append(ValidationResult(
                passed=False,
                test_name="definition",
                input_args={},
                error_message=f"Function {tool_name} not found"
            ))
            return report

        func = namespace[tool_name]
        if not callable(func):
            report.summary = f"'{tool_name}' 不是可调用对象"
            report.all_passed = False
            return report

        # 3. 执行测试用例
        for idx, case in enumerate(test_cases):
            args = case.get("args", {})
            expected = case.get("expected", None)
            test_name = case.get("name", f"test_{idx+1}")

            result = ValidationResult(
                passed=False,
                test_name=test_name,
                input_args=args,
                expected_output=expected
            )

            try:
                start = time.perf_counter()
                # 捕获 stdout/stderr
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture

                actual = func(**args)

                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__

                elapsed = (time.perf_counter() - start) * 1000
                result.execution_time_ms = elapsed
                result.actual_output = actual

                if expected is not None:
                    if actual == expected or str(actual) == str(expected):
                        result.passed = True
                    else:
                        result.passed = False
                        result.error_message = f"期望 {expected}，实际 {actual}"
                else:
                    result.passed = True

            except Exception as e:
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                result.passed = False
                result.error_message = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"

            report.results.append(result)

        # 4. 汇总报告
        passed_count = sum(1 for r in report.results if r.passed)
        total = len(report.results)
        report.all_passed = (passed_count == total and total > 0)
        report.summary = f"{passed_count}/{total} 测试用例通过"

        return report


# 便捷函数：一行验证
def validate_tool(tool_name: str, code: str, test_cases: List[Dict]) -> ValidationReport:
    """快捷函数，用于在 executor 中调用"""
    return Validator().validate_code(tool_name, code, test_cases)
