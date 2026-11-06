import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_dotenv(ROOT / ".env")
    token = os.getenv("TELEGRAM_TOKEN", "")
    if not token:
        raise SystemExit("Configura TELEGRAM_TOKEN en .env o en el entorno.")

    endpoint = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    try:
        response = httpx.get(endpoint, timeout=20.0)
    except httpx.RequestError as error:
        raise SystemExit(f"No se pudo contactar con Telegram ({type(error).__name__}).") from None

    try:
        resultado = response.json()
    except ValueError:
        resultado = {"response": response.text}
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    if not response.is_success or not isinstance(resultado, dict) or resultado.get("ok") is not True:
        raise SystemExit("No se pudo consultar la información del webhook.")


if __name__ == "__main__":
    main()
