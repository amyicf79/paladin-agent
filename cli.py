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
    print(f"   [OK]  已生成 {len(_TEMPLATE)} 个文件")
    print(f"\n👉 cd {name} && python app.py")
    return True


def main():
    parser = argparse.ArgumentParser(description="Paladin — AI-Native 脚手架")
    sub = parser.add_subparsers(dest="command")
    init_cmd = sub.add_parser("init", help="初始化新项目")
    init_cmd.add_argument("name", help="项目名称")
    demo_cmd = sub.add_parser("demo", help="运行内置演示场景，展示自主编排能力（零依赖终端可视化）")
    opt_cmd = sub.add_parser("optimize", help="生成策略优化报告")
    opt_cmd.add_argument("--apply", action="store_true", help="将洞察应用到codegen模板")
    opt_cmd.add_argument("--store", default="experience_store", help="经验库路径")
    run_cmd = sub.add_parser("run", help="执行自然语言任务（Planner→Executor→Store）")
    run_cmd.add_argument("prompt", nargs="+", help="任务描述")
    run_cmd.add_argument("--max-iterations", type=int, default=3, help="最大迭代轮次")
    run_cmd.add_argument("--mock", action="store_true", help="使用内置mock后端(不需要API密钥)")
    run_cmd.add_argument("--quiet", action="store_true", help="简约输出，只显示最终结果")
    run_cmd.add_argument("--verbose", action="store_true", help="详细输出，显示所有中间状态（默认模式）")
    demo_cmd.add_argument("--config", type=str, default=None,
                          help="指定 paladin.toml 配置文件路径（默认: 项目根目录）")
    demo_cmd.add_argument("--auto", action="store_true",
                          help="自动播放模式，跳过 Enter 等待")

    args = parser.parse_args()
    if args.command == "init":
        init_project(args.name)
    elif args.command == "demo":
        from paladin.config import load_config
        from paladin.app import Paladin

        cfg = load_config(args.config)
        # CLI --auto 覆盖配置文件中的 auto_mode
        auto = args.auto or cfg.demo.auto_mode
        Paladin.demo(auto=auto)
    elif args.command == "optimize":
        import os, sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from paladin.strategy_optimizer import StrategyOptimizer
        opt = StrategyOptimizer(store_path=args.store)
        report = opt.analyze()
        print(report.summary)
        print()
        for ins in report.insights:
            print(f"[{ins.category}] {ins.title}")
            print(f"  {ins.description}")
            if ins.evidence:
                for ev in ins.evidence[:3]:
                    print(f"  - {ev}")
            print(f"  建议: {ins.recommendation}")
            print()
    elif args.command == "run":
        import os, sys, time
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from paladin.config import load_config
        from paladin.app import Paladin
        
        prompt = " ".join(args.prompt)
        if not args.quiet:
            print(f"[.]  Planning... ({prompt[:50]})")
            start = time.time()
        
        cfg = load_config(None)
        if args.mock:
            cfg.planner.backend = "mock"
        paladin = Paladin(config=cfg)
        result = paladin.run(query=prompt, max_iterations=args.max_iterations)
        
        elapsed = time.time() - start
        if args.quiet:
            print(result)
        else:
            print(f"[OK]  完成 ({elapsed:.1f}s)")
            print(f"━━━━━━━━━━━━━━━━━━━━━")
            print(result)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
