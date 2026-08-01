# -*- coding: utf-8 -*-
"""AdapterFactory — LLM适配器工厂"""

class AdapterFactory:
    _registry = {
        "deepseek": "paladin.adapters.deepseek.DeepSeekAdapter",
        "ollama": "paladin.adapters.ollama.OllamaAdapter",
        "qwen": "paladin.adapters.qwen.QwenAdapter",
    }
    @classmethod
    def create(cls, provider, config):
        import importlib
        path = cls._registry.get(provider)
        if not path:
            raise ValueError(f"Unknown LLM provider: {provider}")
        mod_name, cls_name = path.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        return getattr(mod, cls_name)(config)
