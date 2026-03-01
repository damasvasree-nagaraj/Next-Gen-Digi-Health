import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "phi"   # ⚡ FASTEST MODEL

def call_ollama(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 200,   # fast response
            "temperature": 0.3
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=60
    )
    response.raise_for_status()

    return response.json().get("response", "").strip()
