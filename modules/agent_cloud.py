# File: ~/.config/local-ai/modules/agent_cloud.py
# Dynamic Cloud Cascade Engine (Top-Down .env Priority)

import os
import re
import json
from typing import List, Dict, Any, Tuple

ENV_PATH: str = os.path.expanduser("~/.config/local-ai/.env")


def get_active_configs(messages: List[Dict[str, str]]) -> List[Tuple[str, Dict[str, str], Dict[str, Any], int]]:
    """Compiles active cloud API configurations, prioritizing them based on their top-down order in .env."""
    configs: List[Tuple[str, Dict[str, str], Dict[str, Any], int]] = []
    if not os.path.exists(ENV_PATH):
        return configs

    # Standard OpenAI-compatible endpoint mappings
    url_map: Dict[str, str] = {
        "GEMINI_API_KEY": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "OPENAI_API_KEY": "https://api.openai.com/v1/chat/completions",
        "XAI_API_KEY": "https://api.x.ai/v1/chat/completions",
        "OPENROUTER_API_KEY": "https://openrouter.ai/api/v1/chat/completions"
    }

    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line_strip = line.strip()
                if not line_strip or line_strip.startswith("#"):
                    continue
                
                # Match any active key assignment (e.g. GEMINI_API_KEY="your-key")
                match = re.match(r"^([A-Z0-9_]+_API_KEY|[A-Z0-9_]+_KEY)\s*=\s*\"?([^\"]*)\"?$", line_strip)
                if match:
                    key_name, key_val = match.groups()
                    if not key_val.strip():
                        continue
                        
                    provider: str = key_name.split("_")[0].lower()  # e.g., 'gemini', 'openai'
                    
                    # 1. SPECIAL CASE: Anthropic Claude (Uses different headers/endpoints)
                    if key_name == "CLAUDE_API_KEY":
                        model = os.environ.get("CLAUDE_MODEL", "claude-fable-5")
                        
                        # Extract system instructions to top-level key for Anthropic schema
                        claude_messages: List[Dict[str, str]] = []
                        system_prompt: Optional[str] = None
                        for m in messages:
                            if m.get("role") == "system":
                                system_prompt = m.get("content")
                            else:
                                claude_messages.append({"role": m.get("role") or "user", "content": m.get("content") or ""})
                        
                        body: Dict[str, Any] = {
                            "model": model,
                            "messages": claude_messages,
                            "stream": True,
                            "max_tokens": 4096
                        }
                        if system_prompt:
                            body["system"] = system_prompt
                            
                        headers: Dict[str, str] = {
                            "x-api-key": key_val,
                            "anthropic-version": "2023-06-01"
                        }
                        configs.append((
                            "https://api.anthropic.com/v1/messages",
                            headers,
                            body,
                            30
                        ))
                    
                    # 2. GENERAL CASE: Any OpenAI-Compatible Provider
                    else:
                        url = url_map.get(key_name)
                        if url:
                            # Map default fallback models dynamically per provider
                            fallback_model = {
                                "gemini": "gemini-3.1-flash-lite",
                                "openai": "gpt-5.5",
                                "xai": "grok-4.5"
                            }.get(provider, "default-model")
                            
                            model_var_name = "OPENROUTER_MODEL" if provider == "openrouter" else f"{provider.upper()}_MODEL"
                            model_name = os.environ.get(model_var_name) or fallback_model
                            
                            body = {
                                "model": model_name,
                                "messages": messages,
                                "stream": True
                            }
                            
                            # Inject OpenRouter usage tracking if applicable
                            if provider == "openrouter":
                                body["usage"] = {"include": True}
                                
                            headers = {"Authorization": f"Bearer {key_val}"}
                            if provider == "openrouter":
                                headers["HTTP-Referer"] = "https://github.com/j5onrf/local-ai"
                                
                            timeout = 180 if provider == "openrouter" else 30
                            configs.append((url, headers, body, timeout))
    except Exception:
        pass

    return configs
