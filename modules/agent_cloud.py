# File: ~/.config/local-ai/modules/agent_cloud.py
import os

def get_active_configs(messages: list) -> list:
    """Compiles active cloud API configurations, mapping payloads to provider-specific schemas.
    
    Returns a list of tuples: (url, headers, body, timeout)
    """
    configs = []

    # 1. Google Gemini API (via OpenAI-compatibility Endpoint)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        gemini_model = os.environ.get("GEMINI_MODEL", os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite"))
        body = {
            "model": gemini_model,
            "messages": messages,
            "stream": True
        }
        headers = {"Authorization": f"Bearer {gemini_key}"}
        configs.append((
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            headers,
            body,
            30
        ))

    # 2. OpenAI Subscription API (Supporting gpt-5.5)
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        openai_model = os.environ.get("OPENAI_MODEL", os.environ.get("CLOUD_MODEL", "gpt-5.5"))
        body = {
            "model": openai_model,
            "messages": messages,
            "stream": True
        }
        headers = {"Authorization": f"Bearer {openai_key}"}
        configs.append((
            "https://api.openai.com/v1/chat/completions",
            headers,
            body,
            30
        ))

    # 3. Anthropic Claude Subscription API (Supporting claude-fable-5)
    claude_key = os.environ.get("CLAUDE_API_KEY")
    if claude_key:
        claude_model = os.environ.get("CLAUDE_MODEL", os.environ.get("CLOUD_MODEL", "claude-fable-5"))
        
        # Format messages for Anthropic (Extract System instructions to top-level key)
        claude_messages = []
        system_prompt = None
        for m in messages:
            if m.get("role") == "system":
                system_prompt = m.get("content")
            else:
                claude_messages.append({"role": m.get("role"), "content": m.get("content")})
        
        body = {
            "model": claude_model,
            "messages": claude_messages,
            "stream": True,
            "max_tokens": 4096
        }
        if system_prompt:
            body["system"] = system_prompt
            
        headers = {
            "x-api-key": claude_key,
            "anthropic-version": "2023-06-01"
        }
        configs.append((
            "https://api.anthropic.com/v1/messages",
            headers,
            body,
            30
        ))

    # 4. x.AI Grok Subscription API (Supporting grok-4.5)
    xai_key = os.environ.get("XAI_API_KEY")
    if xai_key:
        xai_model = os.environ.get("XAI_MODEL", os.environ.get("CLOUD_MODEL", "grok-4.5"))
        body = {
            "model": xai_model,
            "messages": messages,
            "stream": True
        }
        headers = {"Authorization": f"Bearer {xai_key}"}
        configs.append((
            "https://api.x.ai/v1/chat/completions",
            headers,
            body,
            30
        ))

    # 5. OpenRouter API Configurations
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        openrouter_model = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
        body = {
            "model": openrouter_model,
            "messages": messages,
            "stream": True,
            "usage": {"include": True}
        }
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "HTTP-Referer": "https://github.com/j5onrf/local-ai"
        }
        configs.append((
            "https://openrouter.ai/api/v1/chat/completions",
            headers,
            body,
            180
        ))

    return configs
