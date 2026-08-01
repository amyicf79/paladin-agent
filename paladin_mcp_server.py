#!/usr/bin/env python3
"""Paladin MCP Server v0.1 — Model Context Protocol stdio server
暴露 Paladin 三个可移植能力给任何 MCP Host (Qoder/Cursor/GA)
协议: JSON-RPC 2.0 over stdin/stdout (同 IXNO mcp_server 模式, 零依赖)

工具:
  1. paladin_generate_tool  — 运行时工具合成 (codegen.py CodeGenerator)
  2. paladin_sop_validate   — 执行前 schema 校验 (validator.py validate_tool)
  3. paladin_learn          — 经验记录 (experience_store.py get_store)

启动: python paladin_mcp_server.py
MCP 配置:
  {"mcpServers": {"paladin": {"command": "python",
    "args": ["H:/GA/GenericAgent/paladin/paladin_mcp_server.py"]}}}
"""
import json, os, sys, traceback

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_SCRIPT_DIR)
# Paladin 是包（内部相对导入），需把父目录加入 path 以 from paladin.* 导入
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

SERVER_INFO = {"name": "paladin", "version": "0.1.0"}


def _tools_list():
    return [
        {
            "name": "paladin_generate_tool",
            "description": "运行时生成工具代码: 描述需要的能力→CodeGenerator 生成 Python 工具→保存",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "工具名(小写下划线)"},
                    "description": {"type": "string", "description": "工具要做什么"},
                    "params": {"type": "object", "description": "参数schema {名:类型}"},
                },
                "required": ["name", "description"],
            },
        },
        {
            "name": "paladin_sop_validate",
            "description": "执行前校验工具代码: 跑测试用例验证生成代码正确性(含repair提示)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"},
                    "code": {"type": "string", "description": "待校验的Python代码"},
                    "test_cases": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["tool_name", "code"],
            },
        },
        {
            "name": "paladin_learn",
            "description": "记录经验到经验商店: 成功/失败事件，积累修复模式库",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "event_type": {"type": "string", "description": "success|failure|repair"},
                    "detail": {"type": "object", "description": "事件详情(错误类型/修复模式等)"},
                },
                "required": ["event_type", "detail"],
            },
        },
        {
            "name": "paladin_synthesize",
            "description": "端到端工具合成闭环: 描述→生成→校验→自动修复→热加载→经验记录, 返回生产级工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "工具名"},
                    "description": {"type": "string", "description": "工具要做什么"},
                    "test_cases": {"type": "array", "items": {"type": "object"}, "description": "测试用例(可选,缺省自动推断)"},
                    "max_attempts": {"type": "number", "description": "修复循环上限(默认3)"},
                },
                "required": ["name", "description"],
            },
        },
    ]


def _make_adapter(host_tools=None):
    """从环境变量构造 LLM adapter（DeepSeek 兼容 OpenAI 协议，零第三方依赖）
    host_tools: 宿主可调用工具清单（核调壳），传给 codegen 让生成代码优先用宿主生态"""
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        return None
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    class _Adapter:
        def __init__(self):
            self.host_tools = host_tools or []  # 方法/实例作用域可闭包，类体不行

        def chat(self, messages):
            import urllib.request
            payload = json.dumps({"model": model, "messages": messages, "max_tokens": 800}).encode("utf-8")
            req = urllib.request.Request(
                base_url.rstrip("/") + "/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return {"content": data["choices"][0]["message"]["content"]}

    return _Adapter()


def _call_tool(name, args):
    if name == "paladin_generate_tool":
        from paladin.codegen import CodeGenerator
        from paladin.commander.protocol import MetaAction
        meta = MetaAction(
            action_type="generate_tool",
            description=args.get("description", ""),
            target_name=args.get("name", "generated_tool"),
        )
        gen = CodeGenerator(backend="mock")
        code = gen.generate(meta)
        saved = gen.save_to_file(code, meta.target_name, directory=os.path.join(_SCRIPT_DIR, "generated_tools"))
        return {"ok": True, "code": code[:4000], "saved_to": str(saved)}

    if name == "paladin_sop_validate":
        from paladin.validator import validate_tool
        result = validate_tool(args["tool_name"], args["code"], args.get("test_cases", []))
        # ValidationReport 等 dataclass → dict
        if hasattr(result, "__dict__"):
            result = result.__dict__
        return {"ok": True, "result": result}

    if name == "paladin_learn":
        from datetime import datetime
        from paladin.experience_store import get_store
        from paladin.experience_store import Experience
        store = get_store()
        detail = args.get("detail", {})
        exp = Experience(
            problem_signature=detail.get("problem_signature", args.get("event_type", "unknown")),
            tool_name=detail.get("tool_name", ""),
            original_code=detail.get("original_code", ""),
            repaired_code=detail.get("repaired_code", ""),
            error_type=detail.get("error_type", ""),
            error_message=detail.get("error_message", ""),
            timestamp=datetime.now().isoformat(),
            success=args.get("event_type") != "failure",
        )
        store.add_experience(exp)
        return {"ok": True, "learned": args.get("event_type"), "exp_id": exp.problem_signature}

    if name == "paladin_synthesize":
        # 完整闭环: generate → validate → repair → retry → save → load → learn
        from datetime import datetime
        from paladin.codegen import CodeGenerator
        from paladin.commander.protocol import MetaAction
        from paladin.validator import validate_tool
        from paladin.repair import repair_tool
        from paladin.loader import ToolLoader
        from paladin.experience_store import get_store
        from paladin.experience_store import Experience

        target = args.get("name", "synthesized_tool")
        desc = args.get("description", "")
        test_cases = args.get("test_cases", [])
        max_attempts = int(args.get("max_attempts", 3))
        adapter = _make_adapter(host_tools=args.get("host_tools") or [])

        meta = MetaAction(action_type="generate_tool", description=desc, target_name=target)
        gen = CodeGenerator(backend="real" if adapter else "mock", adapter=adapter)
        code = gen.generate(meta)

        history = []
        report = None
        for attempt in range(1, max_attempts + 1):
            report = validate_tool(target, code, test_cases)
            passed = getattr(report, "all_passed", False)
            history.append({"attempt": attempt, "passed": passed,
                            "error": getattr(report, "summary", None)})
            if passed:
                break
            if attempt < max_attempts:
                rr = repair_tool(target, code, report, adapter=adapter)
                if rr and getattr(rr, "repaired_code", None):
                    code = rr.repaired_code
                    history[-1]["repaired"] = True

        tool_dir = os.path.join(_SCRIPT_DIR, "generated_tools")
        saved = None
        loaded = False
        try:
            saved = str(CodeGenerator(backend="mock").save_to_file(code, target, directory=tool_dir))
        except Exception as e:
            saved = f"save_error: {e}"
        try:
            loader = ToolLoader(tool_dir=tool_dir)
            loader.clear_cache()
            loaded = loader.load_tool(target) is not None
        except Exception as e:
            loaded = False

        # 记录经验（无论成败）
        try:
            store = get_store()
            store.add_experience(Experience(
                problem_signature=f"synth_{target}",
                tool_name=target,
                original_code="",
                repaired_code=code,
                error_type="" if history[-1]["passed"] else "synth_failed",
                error_message="" if history[-1]["passed"] else history[-1].get("error", ""),
                timestamp=datetime.now().isoformat(),
                success=history[-1]["passed"],
            ))
        except Exception:
            pass

        return {"ok": history[-1]["passed"], "tool": target, "tool_path": saved,
                "loaded": loaded, "history": history, "final_code": code[:4000]}

    return {"ok": False, "error": f"未知工具: {name}"}


# ── stdio JSON-RPC 协议 ─────────────────────────
def read_json():
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line)


def send_json(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def handle_request(req):
    method = req.get("method", "")
    rid = req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {"serverInfo": SERVER_INFO}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": _tools_list()}}
    if method == "tools/call":
        params = req.get("params", {})
        try:
            result = _call_tool(params.get("name", ""), params.get("arguments", {}))
            # 安全序列化：dict→尝试json，否则 str 兜底
            if isinstance(result, dict):
                try:
                    text = json.dumps(result, ensure_ascii=False)
                except (TypeError, ValueError):
                    text = json.dumps({k: str(v) for k, v in result.items()}, ensure_ascii=False)
            else:
                text = str(result)
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": text}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": f"ERROR: {e}\n{traceback.format_exc()[:800]}"}]}}
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main():
    while True:
        try:
            req = read_json()
            if req is None:
                break
            resp = handle_request(req)
            if resp:
                send_json(resp)
        except Exception as e:
            send_json({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}})


if __name__ == "__main__":
    main()
