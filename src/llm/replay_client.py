import json
import hashlib
import os
from typing import Optional
from .client import LLMResponse, LLMClient, GroqClient

class ReplayClient:
    def __init__(self, replay_file: str, record_mode: bool = False):
        self.replay_file = replay_file
        self.record_mode = record_mode
        self.responses = {}
        
        if os.path.exists(self.replay_file):
            with open(self.replay_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        self.responses[entry['prompt_hash']] = entry['response']
                        
        if self.record_mode:
            self.real_client = GroqClient()
        else:
            from .mock_client import MockClient
            self.fallback_client = MockClient()

    def complete(self, system_prompt: str, user_prompt: str, context: Optional[dict] = None) -> LLMResponse:
        combined = system_prompt + user_prompt
        prompt_hash = hashlib.md5(combined.encode('utf-8')).hexdigest()
        
        if prompt_hash in self.responses and not self.record_mode:
            data = self.responses[prompt_hash]
            return LLMResponse(**data)
            
        if self.record_mode:
            response = self.real_client.complete(system_prompt, user_prompt, context)
            
            os.makedirs(os.path.dirname(self.replay_file), exist_ok=True)
            with open(self.replay_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'prompt_hash': prompt_hash,
                    'system_prompt': system_prompt,
                    'user_prompt': user_prompt,
                    'response': {
                        'content': response.content,
                        'model': response.model,
                        'usage_tokens': response.usage_tokens,
                        'cost_usd': response.cost_usd
                    }
                }) + '\n')
            return response
            
        return self.fallback_client.complete(system_prompt, user_prompt, context)
