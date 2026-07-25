"""
app.py — Paladin 应用入口

指挥官(Planner) + 调度官(Executor) + 三篱笆(Cache/Router/Watch)

用法：
    python app.py "查询今天的天气并生成报告"
"""
import sys
from paladin.models.cache import cache
from paladin.models.router import ModelRouter
from paladin.models.watch import CostWatch
from paladin.adapters.deepseek import DeepSeekAdapter
from paladin.commander import Planner
from paladin.dispatcher import Executor


class Paladin:
    def __init__(self):
        self.adapter = DeepSeekAdapter()
        self.planner = Planner(self.adapter)
        self.executor = Executor()
        self.router = ModelRouter()
        self.watch = CostWatch()

    def run(self, query: str):
        plan = self.planner.plan(query)
        print(f"[指挥官] 计划: {plan}")
        if not plan:
            print("[调度官] 无工具调用 → 直接 LLM 对话（走三篱笆）")
            return "".join(self.adapter.chat([{"role": "user", "content": query}]))
        results = self.executor.execute(plan)
        print(f"[调度官] 结果: {results}")
        return results


def main():
    app = Paladin()
    if len(sys.argv) > 1:
        print(app.run(" ".join(sys.argv[1:])))
    else:
        print("Paladin — AI-Native 脚手架 (Ctrl+C 退出)")
        while True:
            try:
                q = input("\n> ")
                if q.strip():
                    print(app.run(q))
            except KeyboardInterrupt:
                print("\nbye.")
                break


if __name__ == "__main__":
    main()

