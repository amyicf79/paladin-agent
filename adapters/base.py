# -*- coding: utf-8 -*-
"""BaseLLMAdapter — LLM适配器抽象基类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLLMAdapter(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict], stream: bool = False, **kwargs) -> str:
        ...
