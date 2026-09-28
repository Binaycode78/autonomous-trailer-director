import os
import time
import logging
from dataclasses import dataclass
from typing import Protocol, Optional

@dataclass
class LLMResponse:
    content: str
    model: str
    usage_tokens: int
    cost_usd: float

class LLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str, context: Optional[dict] = None) -> LLMResponse:
        ...

class GroqClient:
    def __init__(self):
        import groq
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.client = groq.Groq(api_key=self.api_key) if self.api_key else None
        self.default_model = "llama-3.3-70b-versatile"
        self.fallback_model = "llama-3.1-8b-instant"

    def complete(self, system_prompt: str, user_prompt: str, context: Optional[dict] = None) -> LLMResponse:
        import groq
        if not self.client:
            raise ValueError("GROQ_API_KEY environment variable not set")
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    messages=messages,
                    model=self.default_model,
                )
                
                content = response.choices[0].message.content
                tokens = response.usage.total_tokens if response.usage else 0
                cost = (tokens / 1000.0) * 0.002
                
                logging.info(f"Groq API call to {self.default_model} cost: ${cost:.6f}")
                return LLMResponse(content=content, model=self.default_model, usage_tokens=tokens, cost_usd=cost)
            except groq.APIConnectionError as e:
                logging.warning(f"Connection error: {e}, retrying...")
                time.sleep(2 ** attempt)
            except groq.RateLimitError as e:
                logging.warning(f"Rate limit error: {e}, retrying...")
                time.sleep(2 ** attempt)
            except Exception as e:
                logging.warning(f"Error with {self.default_model}: {e}, trying fallback...")
                try:
                    response = self.client.chat.completions.create(
                        messages=messages,
                        model=self.fallback_model,
                    )
                    content = response.choices[0].message.content
                    tokens = response.usage.total_tokens if response.usage else 0
                    cost = (tokens / 1000.0) * 0.002
                    logging.info(f"Groq API fallback call to {self.fallback_model} cost: ${cost:.6f}")
                    return LLMResponse(content=content, model=self.fallback_model, usage_tokens=tokens, cost_usd=cost)
                except Exception as fallback_e:
                    raise fallback_e
        raise Exception("Max retries exceeded")

def get_client(mode: str = "mock", model: Optional[str] = None, replay_dir: Optional[str] = None) -> LLMClient:
    if mode == "real":
        client = GroqClient()
        if model:
            client.default_model = model
        return client
    elif mode == "mock":
        from .mock_client import MockClient
        return MockClient()
    elif mode == "replay":
        from .replay_client import ReplayClient
        replay_file = os.path.join(replay_dir, "replay.jsonl") if replay_dir else "d:/stage_project/data/replay.jsonl"
        return ReplayClient(replay_file=replay_file)
    else:
        raise ValueError(f"Unknown mode: {mode}")
