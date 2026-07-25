"""
app.py — Paladin 应用入口

用法：
    python app.py         # 启动交互式会话
    python app.py "你好"  # 单次查询
"""
import sys
from paladin.models.cache import cache
from paladin.models.router import ModelRouter, quality_score
from paladin.models.watch import CostWatch
from paladin.adapters.deepseek import DeepSeekAdapter


class AIApp:
    """AI-Native 应用实例

    指挥官-调度官模式内建：commander 层做决策，dispatcher 层做路由。
    模型篱笆（缓存→路由→监控）默认启用。
    """

    def __init__(self, model: str = "deepseek-chat"):
        self.adapter = DeepSeekAdapter(model=model)
        self.router = ModelRouter()
        self.watch = CostWatch()
        self._history = []

    def chat(self, user_input: str) -> str:
        """一次完整对话（缓存→路由→监控）"""
        kwargs = {"messages": [{"role": "user", "content": user_input}]}

        # 1. 查缓存
        cached = cache.get("flash", kwargs)
        if cached:
            return cached["text"]

        # 2. 调用模型
        full = ""
        for chunk in self.adapter.chat([{"role": "user", "content": user_input}]):
            full += chunk

        # 3. 写缓存
        cache.put("flash", kwargs, {"text": full})

        # 4. 记录成本（约算）
        self.watch.record("flash", len(user_input) * 2, len(full) * 2)

        return full


def main():
    app = AIApp()
    if len(sys.argv) > 1:
        print(app.chat(" ".join(sys.argv[1:])))
    else:
        print("Paladin AI — Interactive Chat (Ctrl+C to exit)")
        while True:
            try:
                user = input("\n> ")
                if user.strip():
                    print(app.chat(user))
            except KeyboardInterrupt:
                print("\nbye.")
                break


if __name__ == "__main__":
    main()
