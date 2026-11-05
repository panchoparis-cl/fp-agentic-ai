import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.messages import HumanMessage

from src.router.graph import crear_grafo


def main() -> None:
    casos_path = ROOT / "tests" / "casos_router.json"
    casos = json.loads(casos_path.read_text(encoding="utf-8"))
    grafo = crear_grafo()
    resultados = []

    for caso in casos:
        estado = grafo.invoke(
            {
                "mensaje": caso["mensaje"],
                "messages": [HumanMessage(content=caso["mensaje"])],
            },
            config={"configurable": {"thread_id": str(uuid4())}},
        )
        obtenido = estado["ruta"]
        resultados.append(
            {
                "mensaje": caso["mensaje"],
                "esperado": caso["esperado"],
                "obtenido": obtenido,
                "correcto": obtenido == caso["esperado"],
                "motivo": estado["motivo"],
            }
        )

    columnas = ["mensaje", "esperado", "obtenido", "✔/✘", "motivo"]
    filas = [
        [
            resultado["mensaje"],
            resultado["esperado"],
            resultado["obtenido"],
            "✔" if resultado["correcto"] else "✘",
            resultado["motivo"],
        ]
        for resultado in resultados
    ]
    anchos = [max(len(columna), *(len(fila[indice]) for fila in filas)) for indice, columna in enumerate(columnas)]
    separador = "+-" + "-+-".join("-" * ancho for ancho in anchos) + "-+"

    print(separador)
    print("| " + " | ".join(columna.ljust(anchos[indice]) for indice, columna in enumerate(columnas)) + " |")
    print(separador)
    for fila in filas:
        print("| " + " | ".join(valor.ljust(anchos[indice]) for indice, valor in enumerate(fila)) + " |")
    print(separador)

    aciertos = sum(resultado["correcto"] for resultado in resultados)
    total = len(resultados)
    print(f"Aciertos: {aciertos}/{total} ({aciertos / total:.1%})")
    fallados = [resultado for resultado in resultados if not resultado["correcto"]]
    if fallados:
        print("Fallados:")
        for resultado in fallados:
            print(
                f'- {resultado["mensaje"]!r}: esperado={resultado["esperado"]}, '
                f'obtenido={resultado["obtenido"]}; motivo: {resultado["motivo"]}'
            )
    else:
        print("Fallados: ninguno")


if __name__ == "__main__":
    main()
