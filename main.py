import argparse
from uuid import uuid4

from langchain_core.messages import HumanMessage

from src.registro import AGENTES, obtener_grafo


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecutar un agente LangGraph")
    parser.add_argument("agente", choices=AGENTES)
    parser.add_argument("mensaje", nargs="?", help="Mensaje para el agente")
    parser.add_argument("--saltos", action="store_true", help="Mostrar los nodos ejecutados")
    parser.add_argument("--diagrama", action="store_true", help="Imprimir Mermaid sin ejecutar")
    parser.add_argument("--thread-id", help="ID de conversación para la memoria (mismo proceso)")
    args = parser.parse_args()

    grafo = obtener_grafo(args.agente)
    if args.diagrama:
        print(grafo.get_graph().draw_mermaid())
        return
    if not args.mensaje:
        parser.error("se requiere un mensaje salvo con --diagrama")

    entrada = {"mensaje": args.mensaje, "messages": [HumanMessage(content=args.mensaje)]}
    config = {"configurable": {"thread_id": args.thread_id or str(uuid4())}}
    if args.saltos:
        nodos = []
        motivo = None
        respuesta = None
        for actualizacion in grafo.stream(entrada, config=config, stream_mode="updates"):
            for nodo, estado in actualizacion.items():
                nodos.append(nodo)
                motivo = estado.get("motivo", motivo)
                respuesta = estado.get("respuesta") or estado.get("messages", [respuesta])[-1]
        print("[saltos] " + " → ".join(nodos))
        if motivo:
            print(f"[motivo] {motivo}")
    else:
        estado = grafo.invoke(entrada, config=config)
        respuesta = estado.get("respuesta") or estado["messages"][-1]
    print(respuesta if isinstance(respuesta, str) else respuesta.content)


if __name__ == "__main__":
    main()
