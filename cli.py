#!/usr/bin/env python3
"""
cli.py — Paladin 脚手架 CLI

用法：
    paladin init my_project     # 创建新项目
    paladin --help              # 查看帮助
"""
import os, sys, shutil, argparse
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent

_TEMPLATE = {
    "app.py": '''"""
my_project — AI-Native 应用
Powered by Paladin
"""
from paladin import AIApp

app = AIApp()

if __name__ == "__main__":
    app.run()
''',
    "commander/__init__.py": '"""commander — 指挥官层（由 Paladin 生成）"""\n',
    "dispatcher/__init__.py": '"""dispatcher — 调度官层（由 Paladin 生成）"""\n',
    "models/cache.py": '"""cache — 模型缓存（由 Paladin 生成）"""\nfrom paladin.models.cache import cache\n',
    "models/router.py": '"""router — 模型路由（由 Paladin 生成）"""\nfrom paladin.models.router import ModelRouter\nrouter = ModelRouter()\n',
    "models/watch.py": '"""watch — 成本监控（由 Paladin 生成）"""\nfrom paladin.models.watch import CostWatch\nwatch = CostWatch()\n',
    "adapters/deepseek.py": '"""DeepSeek adapter（由 Paladin 生成）"""\nfrom paladin.adapters.deepseek import DeepSeekAdapter\nadapter = DeepSeekAdapter()\n',
    "README.md": '''# {name}

AI-Native 应用 — 由 Paladin 生成。

```bash
python app.py
```
''',
}


def init_project(name: str):
    base = Path.cwd() / name
    if base.exists():
        print(f"❌ 目录 '{name}' 已存在")
        return False

    print(f"🚀 创建 Paladin 项目: {name}")
    for rel_path, content in _TEMPLATE.items():
        fp = base / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content.format(name=name), encoding="utf-8")
    print(f"   ✅ 已生成 {len(_TEMPLATE)} 个文件")
    print(f"\n👉 cd {name} && python app.py")
    return True


def main():
    parser = argparse.ArgumentParser(description="Paladin — AI-Native 脚手架")
    sub = parser.add_subparsers(dest="command")
    init_cmd = sub.add_parser("init", help="初始化新项目")
    init_cmd.add_argument("name", help="项目名称")
    sub.add_parser("demo", help="运行内置演示场景，展示自主编排能力（零依赖终端可视化）")

    args = parser.parse_args()
    if args.command == "init":
        init_project(args.name)
    elif args.command == "demo":
        from paladin.app import Paladin
        Paladin.demo()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
