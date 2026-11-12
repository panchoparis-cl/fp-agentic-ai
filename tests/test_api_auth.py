from fastapi.testclient import TestClient

from api.app import app


def test_chat_sin_clave_responde_401(monkeypatch):
    monkeypatch.setenv("API_KEY", "clave-prueba")

    with TestClient(app) as cliente:
        respuesta = cliente.post("/chat", json={"user_id": "cliente-1", "texto": "hola"})

    assert respuesta.status_code == 401
    assert "X-API-Key" in respuesta.json()["detail"]


def test_chat_con_clave_responde_200(monkeypatch):
    import api.app as modulo_api

    monkeypatch.setenv("API_KEY", "clave-prueba")

    class GrafoFalso:
        async def ainvoke(self, entrada, config):
            assert entrada["mensaje"] == "hola"
            assert config["configurable"]["thread_id"] == "cliente-1"
            return {
                "ruta": "generica",
                "motivo": "Saludo de prueba.",
                "respuesta": "¡Hola!",
            }

    monkeypatch.setattr(modulo_api, "crear_router", GrafoFalso)
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/chat",
            headers={"X-API-Key": "clave-prueba"},
            json={"user_id": "cliente-1", "texto": "hola"},
        )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ruta": "generica",
        "motivo": "Saludo de prueba.",
        "respuesta": "¡Hola!",
    }
