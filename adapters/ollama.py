# -*- coding: utf-8 -*-
"""OllamaAdapter — Ollama本地模型适配器（OpenAI兼容协议）"""
from openai import OpenAI
from .base import BaseLLMAdapter

class OllamaAdapter(BaseLLMAdapter):
    def __init__(self, config: dict):
        self.client = OpenAI(
            base_url=config.get("base_url", "http://localhost:11434/v1"),
            api_key=config.get("api_key", "ollama")
        )
        self.model = config.get("model", "qwen2.5:7b")

    def chat(self, messages, stream=False, **kwargs):
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=stream, **kwargs
        )
        return resp.choices[0].message.content
