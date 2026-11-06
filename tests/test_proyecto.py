from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from api.app import MODELO, app
from src.asistente.graph import crear_grafo


class ModeloFalso:
    def invoke(self, mensajes):
        return AIMessage(content=f"Eco: {mensajes[-1].content}")


def test_grafo_sin_credenciales():
    grafo = crear_grafo(modelo=ModeloFalso())
    resultado = grafo.invoke({"messages": [HumanMessage(content="hola")]})
    assert resultado["messages"][-1].content == "Eco: hola"


def test_api_salud_y_validacion_chat():
    cliente = TestClient(app)
    assert cliente.get("/health").json() == {"ok": True, "modelo": MODELO}
    assert cliente.post("/chat", json={"user_id": "cliente-1"}).status_code == 422


def test_api_telegram_rechaza_secreto_incorrecto(monkeypatch):
    monkeypatch.setenv("TELEGRAM_SECRET", "secreto-prueba")
    with TestClient(app) as cliente:
        respuesta = cliente.post("/telegram", json={"update_id": 123})
    assert respuesta.status_code == 403


def test_api_telegram_enruta_y_responde_con_httpx(monkeypatch):
    import api.app as modulo_api

    monkeypatch.setenv("TELEGRAM_SECRET", "secreto-prueba")
    monkeypatch.setenv("TELEGRAM_TOKEN", "token-prueba")
    llamadas = {}

    class GrafoFalso:
        async def ainvoke(self, entrada, config):
            llamadas["entrada"] = entrada
            llamadas["config"] = config
            return {
                "ruta": "preventa",
                "motivo": "Consulta por producto.",
                "respuesta": "Soy el agente de preventa.",
            }

    class RespuestaFalsa:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True, "result": {"message_id": 5}}

    class ClienteHttpFalso:
        def __init__(self, timeout):
            llamadas["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            llamadas["url"] = url
            llamadas["body"] = json
            return RespuestaFalsa()

    monkeypatch.setattr(modulo_api, "crear_router", GrafoFalso)
    monkeypatch.setattr(modulo_api.httpx, "AsyncClient", ClienteHttpFalso)
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secreto-prueba"},
            json={"update_id": 123, "message": {"chat": {"id": 9876}, "text": "¿Tienen poleras?"}},
        )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True}
    assert llamadas["config"]["configurable"]["thread_id"] == "9876"
    assert llamadas["entrada"]["mensaje"] == "¿Tienen poleras?"
    assert llamadas["url"] == "https://api.telegram.org/bottoken-prueba/sendMessage"
    assert llamadas["body"] == {"chat_id": 9876, "text": "Soy el agente de preventa."}


def test_api_telegram_ignora_update_sin_texto(monkeypatch):
    import api.app as modulo_api

    monkeypatch.setenv("TELEGRAM_SECRET", "secreto-prueba")

    class GrafoNoUsado:
        async def ainvoke(self, *args, **kwargs):
            raise AssertionError("No debe invocar el grafo para updates sin texto")

    monkeypatch.setattr(modulo_api, "crear_router", GrafoNoUsado)
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secreto-prueba"},
            json={"update_id": 124, "message": {"chat": {"id": 9876}, "photo": []}},
        )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True}


def test_swagger_documentado_y_sin_telegram():
    cliente = TestClient(app)
    esquema = cliente.get("/openapi.json").json()
    assert esquema["info"]["title"] == "Ecommerce Router API"
    assert "/chat" in esquema["paths"]
    assert "/telegram" not in esquema["paths"]
    assert {"salud", "chat", "telegram"}.issubset({tag["name"] for tag in esquema["tags"]})


def test_saltos_del_grafo():
    grafo = crear_grafo(modelo=ModeloFalso())
    actualizaciones = list(grafo.stream({"messages": [HumanMessage(content="hola")]}, stream_mode="updates"))
    assert [nodo for actualizacion in actualizaciones for nodo in actualizacion] == ["responder"]


def test_api_invocacion_sin_servicio_externo(monkeypatch):
    import api.app as modulo_api
    from src.router.graph import crear_grafo as crear_router
    from src.router.tools import Decision

    class RouterFalso:
        def invoke(self, mensajes):
            return Decision(ruta="generica", motivo="Es una consulta de prueba.")

    monkeypatch.setattr(modulo_api, "crear_router", lambda: crear_router(modelo=RouterFalso()))
    with TestClient(app) as cliente:
        respuesta = cliente.post("/chat", json={"user_id": "cliente-1", "texto": "hola"})
    assert respuesta.status_code == 200
    assert respuesta.json()["ruta"] == "generica"
    assert respuesta.json()["motivo"] == "Es una consulta de prueba."
    assert respuesta.json()["respuesta"] == "¡Hola! Este chat es para ayudarte con la tienda."


def test_api_modelo_falla_devuelve_502_seguro(monkeypatch, caplog):
    import api.app as modulo_api

    class GrafoFallido:
        async def ainvoke(self, *args, **kwargs):
            raise RuntimeError("detalle interno con GOOGLE_API_KEY=secreto")

    monkeypatch.setattr(modulo_api, "crear_router", GrafoFallido)
    with TestClient(app) as cliente:
        respuesta = cliente.post("/chat", json={"user_id": "cliente-1", "texto": "hola"})
    assert respuesta.status_code == 502
    assert "secreto" not in respuesta.text
    assert "stack trace" not in respuesta.text.lower()
    assert "GOOGLE_API_KEY=secreto" in caplog.text
