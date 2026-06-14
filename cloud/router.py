import os
import time
import random
import logging
import openai
from typing import List, Dict, Any

# Set up logging to track live failovers in your terminal terminal session
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("CloudRouter")

class ResilientFallbackRouter:
    def __init__(self):
        # Configure your ordered priority chain. 
        # All tracking variables are initialized here to keep state across agent actions.
        self.providers = [
            {
                "name": "Gemini-Direct",
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                "api_key": os.getenv("GEMINI_API_KEY"),
                "model": "gemini-1.5-flash",
                "cooldown_until": 0.0
            },
            {
                "name": "OpenRouter",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "model": "google/gemini-2.5-flash", 
                "cooldown_until": 0.0
            },
            {
                "name": "Groq",
                "base_url": "https://api.groq.com/openai/v1",
                "api_key": os.getenv("GROQ_API_KEY"),
                "model": "llama-3.1-8b-instant",
                "cooldown_until": 0.0
            },
            {
                "name": "Cerebras",
                "base_url": "https://api.cerebras.ai/v1",
                "api_key": os.getenv("CEREBRAS_API_KEY"),
                "model": "llama3.1-8b",
                "cooldown_until": 0.0
            }
        ]
        # Cooldown duration in seconds (e.g., 5 minutes) if an API trips the breaker
        self.cooldown_duration = 300 

    def get_completion(self, messages: List[Dict[str, str]], max_internal_retries: int = 3, **kwargs) -> str:
        current_time = time.time()

        for provider in self.providers:
            # 1. Circuit Breaker Evaluation
            if current_time < provider["cooldown_until"]:
                remaining_cooldown = int(provider["cooldown_until"] - current_time)
                logger.info(f"Skipping {provider['name']} (Circuit open. Cooling down for {remaining_cooldown}s)")
                continue

            # 2. Environment Verification
            if not provider["api_key"]:
                logger.warning(f"Skipping {provider['name']} (Missing API key in environment variables)")
                continue

            # 3. Execution & Internal Retry Loop
            client = openai.OpenAI(
                base_url=provider["base_url"],
                api_key=provider["api_key"],
                timeout=15.0 # Strict timeout: if an endpoint hangs for 15s, drop it
            )

            for attempt in range(max_internal_retries):
                try:
                    logger.info(f"Attempting {provider['name']} (Attempt {attempt + 1}/{max_internal_retries})")
                    
                    runtime_params = {**kwargs, "model": provider["model"], "messages": messages}
                    response = client.chat.completions.create(**runtime_params)
                    
                    return response.choices[0].message.content

                except (openai.RateLimitError, openai.InternalServerError, openai.APITimeoutError) as transient_err:
                    # Handle transient errors with randomized exponential backoff
                    if attempt < max_internal_retries - 1:
                        sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                        logger.warning(f"Transient error on {provider['name']}: {transient_err}. Retrying in {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                    else:
                        # Retries exhausted. Trip the circuit breaker for this specific provider.
                        provider["cooldown_until"] = time.time() + self.cooldown_duration
                        logger.error(f"Exhausted retries for {provider['name']}. Tripping circuit breaker for {self.cooldown_duration}s.")
                        break # Break retry loop, fall through to next provider

                except openai.AuthenticationError as auth_err:
                    # Broken keys cannot be bypassed via retries. Lock it down immediately.
                    provider["cooldown_until"] = time.time() + (self.cooldown_duration * 3)
                    logger.error(f"Auth failure on {provider['name']}: {auth_err}. Disabling provider.")
                    break

                except Exception as unhandled_err:
                    # Catch-all safety net for general socket drops or API structural modifications
                    logger.error(f"Unexpected variance on {provider['name']}: {unhandled_err}")
                    provider["cooldown_until"] = time.time() + self.cooldown_duration
                    break

        # 4. Global Fallback Trigger
        raise RuntimeError("All configured cloud endpoints have either timed out, rate limited, or hard faulted.")

# Singleton instance to persist the cooldown state across consecutive calls within the script session
router_instance = ResilientFallbackRouter()
