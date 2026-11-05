from typing import Literal

from pydantic import BaseModel, Field

from src.asistente.tools import crear_modelo


class Decision(BaseModel):
    ruta: Literal["preventa", "postventa", "generica"] = Field(description="A qué agente va el mensaje.")
    motivo: str = Field(description="Una frase: por qué esa ruta.")


def crear_router_estructurado():
    return crear_modelo(temperature=0).with_structured_output(Decision)
