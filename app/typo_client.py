import requests
from app.config import settings


def fix_typo(text: str) -> str:
    try:
        response = requests.post(settings.typo_api_url, json={"text": text})
        response.raise_for_status()
        return response.json().get("corrected", text)
    except Exception as e:
        print(f"[Typo Fixer] Error: {e}")
        return text