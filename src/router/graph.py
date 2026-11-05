from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, add_messages

from src.router.prompts import GENERICO_PROMPT, POSTVENTA_PROMPT, PREVENTA_PROMPT, ROUTER_PROMPT
from src.router.tools import crear_router_estructurado


class EstadoRouter(TypedDict):
    mensaje: str
    ruta: Literal["preventa", "postventa", "generica"]
    motivo: str
    respuesta: str
    messages: Annotated[list[AnyMessage], add_messages]


def crear_grafo(modelo=None):
    def router(estado: EstadoRouter):
        cliente = modelo if modelo is not None else crear_router_estructurado()
        decision = cliente.invoke([SystemMessage(content=ROUTER_PROMPT), *estado["messages"]])
        return {"ruta": decision.ruta, "motivo": decision.motivo}

    def agente_preventa(estado: EstadoRouter):
        respuesta = PREVENTA_PROMPT.format(mensaje=estado["mensaje"])
        return {"respuesta": respuesta, "messages": [AIMessage(content=respuesta)]}

    def agente_postventa(estado: EstadoRouter):
        respuesta = POSTVENTA_PROMPT.format(mensaje=estado["mensaje"])
        return {"respuesta": respuesta, "messages": [AIMessage(content=respuesta)]}

    def respuesta_generica(estado: EstadoRouter):
        respuesta = GENERICO_PROMPT
        return {"respuesta": respuesta, "messages": [AIMessage(content=respuesta)]}

    grafo = StateGraph(EstadoRouter)
    grafo.add_node("router", router)
    grafo.add_node("agente_preventa", agente_preventa)
    grafo.add_node("agente_postventa", agente_postventa)
    grafo.add_node("respuesta_generica", respuesta_generica)
    grafo.add_edge(START, "router")
    grafo.add_conditional_edges(
        "router",
        lambda estado: estado["ruta"],
        {
            "preventa": "agente_preventa",
            "postventa": "agente_postventa",
            "generica": "respuesta_generica",
        },
    )
    for destino in ("agente_preventa", "agente_postventa", "respuesta_generica"):
        grafo.add_edge(destino, END)
    return grafo.compile(checkpointer=MemorySaver())
