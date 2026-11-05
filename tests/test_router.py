import json
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

from api.app import app
from src.router.graph import crear_grafo
from src.router.tools import Decision


CASOS = [
    ("¿tienen la polera azul en talla M?", "preventa", "agente_preventa"),
    ("mi pedido 4521 llegó roto", "postventa", "agente_postventa"),
    ("hola", "generica", "respuesta_generica"),
    ("¿cuánto cuesta el envío a Valparaíso?", "preventa", "agente_preventa"),
    ("quiero devolver unas zapatillas", "postventa", "agente_postventa"),
    ("¿qué hora es en Tokio?", "generica", "respuesta_generica"),
]
CASOS_JSON = json.loads((Path(__file__).parent / "casos_router.json").read_text(encoding="utf-8"))


class RouterFalso:
    def invoke(self, mensajes):
        texto = mensajes[-1].content.lower()
        if "pedido" in texto or "devolver" in texto:
            ruta = "postventa"
        elif "polera" in texto or "envío" in texto:
            ruta = "preventa"
        else:
            ruta = "generica"
        return Decision(ruta=ruta, motivo=f"Clasificación de prueba: {ruta}.")


def test_router_usa_salida_estructurada(monkeypatch):
    import src.router.tools as herramientas

    class ModeloEspia:
        def with_structured_output(self, esquema):
            assert esquema is Decision
            return "router estructurado"

    def crear_modelo_falso(**opciones):
        assert opciones == {"temperature": 0}
        return ModeloEspia()

    monkeypatch.setattr(herramientas, "crear_modelo", crear_modelo_falso)
    assert herramientas.crear_router_estructurado() == "router estructurado"


@pytest.mark.parametrize("mensaje,ruta,nodo", CASOS)
def test_rutas_y_saltos(mensaje, ruta, nodo):
    grafo = crear_grafo(modelo=RouterFalso())
    entrada = {"mensaje": mensaje, "messages": [HumanMessage(content=mensaje)]}
    config = {"configurable": {"thread_id": str(uuid4())}}
    eventos = list(grafo.stream(entrada, config=config, stream_mode="updates"))
    assert [nombre for evento in eventos for nombre in evento] == ["router", nodo]
    estado = grafo.get_state(config).values
    assert estado["ruta"] == ruta
    assert estado["motivo"]
    assert estado["respuesta"] == estado["messages"][-1].content
    assert estado["mensaje"] == mensaje


def test_memoria_por_thread_id():
    grafo = crear_grafo(modelo=RouterFalso())
    config = {"configurable": {"thread_id": "cliente-1"}}
    for mensaje in ("hola", "mi pedido 4521 llegó roto"):
        estado = grafo.invoke(
            {"mensaje": mensaje, "messages": [HumanMessage(content=mensaje)]}, config=config
        )
    assert len(estado["messages"]) == 4
    assert estado["ruta"] == "postventa"
    otro = grafo.invoke(
        {"mensaje": "hola", "messages": [HumanMessage(content="hola")]},
        config={"configurable": {"thread_id": "cliente-2"}},
    )
    assert len(otro["messages"]) == 2


def test_api_router(monkeypatch):
    import api.app as modulo_api

    grafo = crear_grafo(modelo=RouterFalso())
    monkeypatch.setattr(modulo_api, "crear_router", lambda: grafo)
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/chat",
            json={"texto": "mi pedido 4521 llegó roto", "user_id": "cliente-api"},
        )
    assert respuesta.status_code == 200
    assert respuesta.json()["ruta"] == "postventa"
    assert respuesta.json()["motivo"]
    assert "mi pedido 4521 llegó roto" in respuesta.json()["respuesta"]


def test_cli_saltos_y_motivo(monkeypatch, capsys):
    import main

    monkeypatch.setattr(main, "obtener_grafo", lambda nombre: crear_grafo(modelo=RouterFalso()))
    monkeypatch.setattr(sys, "argv", ["main.py", "router", "hola", "--saltos"])
    main.main()
    salida = capsys.readouterr().out
    assert "router → respuesta_generica" in salida
    assert "[motivo] Clasificación de prueba: generica." in salida


@pytest.fixture(scope="module")
def resultados_router_modelo():
    """Clasifica una vez los 15 casos con el modelo real; requiere API disponible."""
    grafo = crear_grafo()
    resultados = {}
    for caso in CASOS_JSON:
        estado = grafo.invoke(
            {
                "mensaje": caso["mensaje"],
                "messages": [HumanMessage(content=caso["mensaje"])],
            },
            config={"configurable": {"thread_id": str(uuid4())}},
        )
        resultados[caso["mensaje"]] = {
            "ruta": estado["ruta"],
            "motivo": estado["motivo"],
        }
    return resultados


@pytest.mark.parametrize("caso", CASOS_JSON, ids=lambda caso: caso["mensaje"])
def test_router_alcanza_13_de_15(caso, resultados_router_modelo):
    aciertos = sum(
        resultados_router_modelo[item["mensaje"]]["ruta"] == item["esperado"]
        for item in CASOS_JSON
    )
    fallados = [
        f'{item["mensaje"]!r}: esperado {item["esperado"]}, obtenido '
        f'{resultados_router_modelo[item["mensaje"]]["ruta"]}'
        for item in CASOS_JSON
        if resultados_router_modelo[item["mensaje"]]["ruta"] != item["esperado"]
    ]
    assert aciertos >= 13, f"Aciertos: {aciertos}/15. Fallados: {fallados}"
