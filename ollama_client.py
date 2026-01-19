import requests
import json

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="dolphin-mistral:7b"):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt, system_prompt=None, context=None, stream=False):
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }
        if system_prompt:
            payload["system"] = system_prompt
        if context:
            payload["context"] = context
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        if stream:
            return response
        else:
            return response.json()

    def chat(self, messages, stream=False):
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        if stream:
            return response
        else:
            return response.json()

    def get_embeddings(self, prompt):
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": prompt
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()["embedding"]
