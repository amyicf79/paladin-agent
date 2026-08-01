"""
adapters/deepseek.py — DeepSeek 模型适配器

适配器模式：新增模型只需写一个新文件，零改动核心架构。
"""
from typing import Optional, Generator, List, Dict


class DeepSeekAdapter:
    """DeepSeek 模型适配器"""

    def __init__(self, config: dict = None):
        config = config or {}
        self.model = config.get("model", "deepseek-v4-flash")
        api_key = config.get("api_key") or os.environ.get("DEEPSEEK_API_KEY")
        self.api_key = api_key

    def chat(self, messages: List[Dict], stream: bool = True) -> Generator[str, None, None]:
        """调用 DeepSeek API"""
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key or os.environ.get("DEEPSEEK_API_KEY", ""),
                        base_url="https://api.deepseek.com")
        response = client.chat.completions.create(model=self.model, messages=messages, stream=stream)
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


import os
