import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


def crear_modelo(*, temperature: float | None = None) -> ChatGoogleGenerativeAI:
    load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("Falta GOOGLE_API_KEY. Configúrala en .env o en el entorno.")
    opciones = {"model": os.getenv("MODELO", "gemini-3.5-flash-lite")}
    if temperature is not None:
        opciones["temperature"] = temperature
    return ChatGoogleGenerativeAI(**opciones)
