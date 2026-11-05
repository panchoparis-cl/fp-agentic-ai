from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from src.asistente.prompts import RESPONDER_PROMPT
from src.asistente.tools import crear_modelo


def crear_grafo(modelo=None):
    # El modelo se crea al ejecutar el nodo: --diagrama no necesita una API key.
    def responder(estado: MessagesState):
        cliente = modelo if modelo is not None else crear_modelo()
        respuesta = cliente.invoke([SystemMessage(content=RESPONDER_PROMPT), *estado["messages"]])
        return {"messages": [respuesta]}

    grafo = StateGraph(MessagesState)
    grafo.add_node("responder", responder)
    grafo.add_edge(START, "responder")
    grafo.add_edge("responder", END)
    return grafo.compile()
