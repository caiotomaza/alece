# SPDX-License-Identifier: GPL-3.0-only
"""Trusted, pinned Chat Completions endpoints; review model availability periodically."""
from collections import OrderedDict

PROVIDERS = OrderedDict([
    ("openai", {"name": "OpenAI", "endpoint": "https://api.openai.com/v1/chat/completions", "model": "gpt-4.1-mini"}),
    ("gemini", {"name": "Google Gemini", "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "model": "gemini-2.5-flash"}),
    ("deepseek", {"name": "DeepSeek", "endpoint": "https://api.deepseek.com/chat/completions", "model": "deepseek-chat"}),
    ("groq", {"name": "Groq", "endpoint": "https://api.groq.com/openai/v1/chat/completions", "model": "llama-3.3-70b-versatile"}),
    ("mistral", {"name": "Mistral AI", "endpoint": "https://api.mistral.ai/v1/chat/completions", "model": "mistral-small-latest"}),
    ("openrouter", {"name": "OpenRouter", "endpoint": "https://openrouter.ai/api/v1/chat/completions", "model": "openai/gpt-4.1-mini"}),
])
SECTIONS = ("expenses", "investments", "movements")


def get_preset_code(endpoint):
    for code, options in PROVIDERS.items():
        if endpoint == options["endpoint"]:
            return code
    return None


def trusted_preset_endpoint(endpoint):
    return get_preset_code(endpoint) is not None
