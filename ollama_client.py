import requests
import json

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="dolphin-mistral:7b", embed_model=None):
        # Ensure the base_url has a scheme
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"
        
        self.base_url = base_url.rstrip("/")
        if "/api/" in self.base_url:
            self.base_url = self.base_url.split("/api/")[0]
            
        self.model = model
        self.embed_model = embed_model or model
        self._embedding_working = None # Track if current model works

    def _get_available_models(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return [m["name"] for m in response.json().get("models", [])]
        except:
            return []

    def _test_embedding(self, model_name):
        url = f"{self.base_url}/api/embed"
        payload = {"model": model_name, "input": "test"}
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                return True
            # Try legacy
            url = f"{self.base_url}/api/embeddings"
            payload = {"model": model_name, "prompt": "test"}
            resp = requests.post(url, json=payload, timeout=30)
            return resp.status_code == 200
        except:
            return False

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
        # If we already know the current embed_model doesn't work, try to find one that does
        if self._embedding_working is False:
            all_models = self._get_available_models()
            for m in all_models:
                if m != self.embed_model and self._test_embedding(m):
                    print(f"Info: Found compatible embedding model: '{m}'")
                    self.embed_model = m
                    self._embedding_working = True
                    break
            
            if self._embedding_working is False:
                # Still no luck
                return []

        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.embed_model,
            "input": prompt
        }
        try:
            response = requests.post(url, json=payload)
            
            if response.status_code == 404:
                # Try legacy
                url = f"{self.base_url}/api/embeddings"
                payload = {"model": self.embed_model, "prompt": prompt, "keep_alive": 0}
                response = requests.post(url, json=payload)
                response.raise_for_status()
                self._embedding_working = True
                return response.json()["embedding"]

            # Handle "does not support embeddings" which usually comes as a 500 or 400
            if response.status_code != 200:
                err_msg = response.json().get("error", "").lower()
                if "not support embeddings" in err_msg or response.status_code == 500:
                    if self._embedding_working is None:
                        self._embedding_working = False
                        return self.get_embeddings(prompt) # Recursive attempt after switching
                    
            response.raise_for_status()
            self._embedding_working = True
            # Unload the embedding model immediately to free VRAM for the Brain
            requests.post(f"{self.base_url}/api/generate", json={"model": self.embed_model, "keep_alive": 0})
            
            # /api/embed returns a list of embeddings in "embeddings" field
            return response.json()["embeddings"][0]
        except Exception as e:
            if self._embedding_working is None:
                self._embedding_working = False
                return self.get_embeddings(prompt)
            print(f"Warning: Embeddings failed for '{self.embed_model}'. Memory disabled.")
            return []
