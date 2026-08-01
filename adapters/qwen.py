# -*- coding: utf-8 -*-
"""QwenAdapter — 通义千问适配器（OpenAI兼容协议）"""
from openai import OpenAI
from .base import BaseLLMAdapter

class QwenAdapter(BaseLLMAdapter):
    def __init__(self, config: dict):
        self.client = OpenAI(
            base_url=config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            api_key=config.get("api_key", "")
        )
        self.model = config.get("model", "qwen-plus")

    def chat(self, messages, stream=False, **kwargs):
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=stream, **kwargs
        )
        return resp.choices[0].message.content
