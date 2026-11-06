import logging
import os
import hmac
from contextlib import asynccontextmanager
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, ConfigDict, Field

from src.router.graph import crear_grafo as crear_router


load_dotenv()
logger = logging.getLogger(__name__)
MODELO = os.getenv("MODELO") or "gemini-3.5-flash-lite"


class ChatRequest(BaseModel):
    """Mensaje entrante del usuario, asociado a su conversación."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"user_id": "cliente-123", "texto": "¿Tienen la polera azul en talla M?"}
            ]
        }
    )

    user_id: str = Field(
        description="Identificador estable del usuario; se usa como thread_id para conservar la memoria.",
        examples=["cliente-123"],
        min_length=1,
    )
    texto: str = Field(
        description="Mensaje del usuario que el router debe clasificar y responder.",
        examples=["¿Tienen la polera azul en talla M?"],
        min_length=1,
    )


class ChatResponse(BaseModel):
    """Ruta elegida por el router y respuesta del agente correspondiente."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ruta": "preventa",
                    "motivo": "Pregunta por disponibilidad y talla antes de comprar.",
                    "respuesta": "Soy el agente de preventa. Recibí: ¿Tienen la polera azul en talla M? Pronto podré ayudarte con productos y compras.",
                }
            ]
        }
    )

    ruta: Literal["preventa", "postventa", "generica"] = Field(
        description="Agente al que se derivó el mensaje.",
        examples=["preventa"],
    )
    motivo: str = Field(
        description="Motivo breve de la decisión de enrutamiento.",
        examples=["Pregunta por disponibilidad y talla antes de comprar."],
    )
    respuesta: str = Field(
        description="Respuesta final del agente seleccionado.",
        examples=["Soy el agente de preventa. Pronto podré ayudarte con productos y compras."],
    )


class ErrorResponse(BaseModel):
    detail: str = Field(
        description="Descripción segura del error, sin detalles internos ni credenciales.",
        examples=["El modelo no pudo procesar el mensaje. Inténtalo de nuevo más tarde."],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Se construye una vez por ciclo de vida de la aplicación, no por request.
    app.state.router_graph = crear_router()
    yield


app = FastAPI(
    title="Ecommerce Router API",
    version="1.0.0",
    description=(
        "API de chat para una tienda ecommerce. El router clasifica cada mensaje en "
        "preventa, postventa o generica y lo deriva al agente correspondiente."
    ),
    openapi_tags=[
        {"name": "salud", "description": "Estado y configuración de la API."},
        {"name": "chat", "description": "Enrutamiento de mensajes del chat ecommerce."},
        {"name": "telegram", "description": "Webhook de Telegram."},
    ],
    lifespan=lifespan,
)


@app.get(
    "/health",
    tags=["salud"],
    summary="Comprobar el estado de la API",
    description="Devuelve el estado del servicio y el modelo configurado.",
)
async def health() -> dict[str, Any]:
    return {"ok": True, "modelo": MODELO}


@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["chat"],
    summary="Enrutar un mensaje de chat",
    description="Clasifica el mensaje y lo envía al agente preventa, postventa o generica.",
    responses={
        200: {"description": "Mensaje clasificado y respuesta del agente."},
        422: {"description": "El body no cumple el esquema requerido (user_id y texto)."},
        502: {
            "model": ErrorResponse,
            "description": "El modelo no pudo procesar el mensaje; el detalle se registra en el servidor.",
        },
    },
)
async def chat(entrada: ChatRequest, request: Request) -> ChatResponse:
    try:
        estado = await request.app.state.router_graph.ainvoke(
            {
                "mensaje": entrada.texto,
                "messages": [HumanMessage(content=entrada.texto)],
            },
            config={"configurable": {"thread_id": entrada.user_id}},
        )
        return ChatResponse(
            ruta=estado["ruta"],
            motivo=estado["motivo"],
            respuesta=estado["respuesta"],
        )
    except Exception as error:
        logger.exception("Falló el procesamiento del chat para user_id=%s", entrada.user_id)
        raise HTTPException(
            status_code=502,
            detail="El modelo no pudo procesar el mensaje. Inténtalo de nuevo más tarde.",
        ) from error


@app.post(
    "/telegram",
    include_in_schema=False,
    tags=["telegram"],
)
async def telegram(
    request: Request,
    secret_header: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, bool]:
    secreto_configurado = os.getenv("TELEGRAM_SECRET", "")
    if not secreto_configurado or not secret_header or not hmac.compare_digest(
        secreto_configurado.encode("utf-8"), secret_header.encode("utf-8")
    ):
        logger.warning("Webhook de Telegram rechazado: secreto inválido o ausente")
        raise HTTPException(status_code=403, detail="Secreto de webhook inválido")

    try:
        update = await request.json()
    except ValueError:
        logger.warning("Telegram envió un body que no es JSON válido")
        return {"ok": True}

    if not isinstance(update, dict):
        return {"ok": True}
    message = update.get("message")
    if not isinstance(message, dict):
        return {"ok": True}
    chat = message.get("chat")
    chat_id = chat.get("id") if isinstance(chat, dict) else None
    texto = message.get("text")
    if chat_id is None or not isinstance(texto, str) or not texto.strip():
        return {"ok": True}

    token = os.getenv("TELEGRAM_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_TOKEN no está configurado; se confirma el update sin procesarlo")
        return {"ok": True}

    try:
        estado = await request.app.state.router_graph.ainvoke(
            {
                "mensaje": texto,
                "messages": [HumanMessage(content=texto)],
            },
            config={"configurable": {"thread_id": str(chat_id)}},
        )
    except Exception:
        logger.exception("Falló el grafo al procesar un mensaje de Telegram (chat_id=%s)", chat_id)
        return {"ok": True}

    ruta = estado.get("ruta", "desconocida")
    motivo = estado.get("motivo", "")
    respuesta = str(estado.get("respuesta", ""))
    logger.info("Telegram chat_id=%s ruta=%s motivo=%s", chat_id, ruta, motivo)

    try:
        async with httpx.AsyncClient(timeout=20.0) as cliente:
            response = await cliente.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": respuesta},
            )
            response.raise_for_status()
            resultado = response.json()
            if not isinstance(resultado, dict) or resultado.get("ok") is not True:
                logger.error("Telegram sendMessage no aceptó el mensaje (chat_id=%s)", chat_id)
    except httpx.HTTPError as error:
        # No imprimir el texto del error: su URL puede contener el token del bot.
        logger.error(
            "Telegram sendMessage falló (chat_id=%s, error=%s, status=%s)",
            chat_id,
            type(error).__name__,
            getattr(getattr(error, "response", None), "status_code", None),
        )
    except Exception as error:
        logger.error("Telegram sendMessage falló (chat_id=%s, error=%s)", chat_id, type(error).__name__)

    return {"ok": True}
