import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

# Use model you already installed
MODEL_NAME = "phi"


def call_ollama(prompt: str) -> str:

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 200,
            "temperature": 0.3
        }
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        return result.get("response", "").strip()

    except requests.exceptions.ConnectionError:
        print("⚠️ Ollama server not running.")
        return "AI server is not running. Please start Ollama."

    except Exception as e:
        print("Ollama Error:", e)
        return "AI response generation failed."