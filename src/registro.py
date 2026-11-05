from functools import lru_cache

from src.asistente.graph import crear_grafo
from src.router.graph import crear_grafo as crear_router


AGENTES = {"asistente": crear_grafo, "router": crear_router}


@lru_cache
def obtener_grafo(nombre: str):
    return AGENTES[nombre]()
