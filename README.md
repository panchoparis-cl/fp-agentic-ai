# Ecommerce Router API

Proyecto Python 3.12 para clasificar mensajes de un chat de ecommerce con LangGraph y Gemini. El router deriva cada mensaje a uno de tres destinos:

- `preventa`: consultas de productos, precios, tallas, stock, descuentos y compras.
- `postventa`: pedidos existentes, problemas, devoluciones, cambios y garantías.
- `generica`: saludos sin pedido y consultas ajenas a la tienda.

Los agentes de preventa y postventa son cascarones de respuesta. La ruta genérica responde sin volver a consultar el modelo. La API conserva el historial en memoria por `user_id` mientras el proceso está activo.

## Requisitos y preparación local

Se necesita Python 3.12 y una clave de Gemini con acceso al modelo configurado.

En PowerShell, desde la raíz del proyecto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` y añade tu `GOOGLE_API_KEY`. No compartas ni subas ese archivo. Hoy el código lee `GOOGLE_API_KEY` y `MODELO`; las variables `TELEGRAM_TOKEN`, `TELEGRAM_SECRET` y `PUBLIC_URL` están preparadas para la futura integración del webhook.

## Ejecutar el router localmente

Con `.venv` activado y `.env` configurado:

```powershell
python main.py router "¿Tienen la polera azul en talla M?" --saltos
python main.py router --diagrama
```

`--saltos` muestra los nodos recorridos y el motivo del router. `--diagrama` imprime el Mermaid sin llamar al modelo. También puedes enviar otro mensaje reemplazando el texto del primer comando.

## Levantar y probar la API

Inicia FastAPI desde la raíz:

```powershell
uvicorn api.app:app --reload --port 8001
```

Swagger está en <http://localhost:8001/docs>. La API ofrece `GET /health`, `POST /chat` y un endpoint temporal `POST /telegram`. Ejemplo de chat desde PowerShell:

```powershell
curl.exe -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d '{"user_id":"cliente-123","texto":"¿Tienen la polera azul en talla M?"}'
```

Reutiliza el mismo `user_id` para mantener el hilo de conversación en memoria. Si falla el modelo, `/chat` responde `502` con un mensaje seguro y registra el detalle en el log del servidor.

## Pruebas

Ejecuta la suite con:

```powershell
python -m pytest
```

La prueba parametrizada de 15 casos llama a Gemini y requiere `GOOGLE_API_KEY` con créditos disponibles; se acepta un mínimo de 13 aciertos. El evaluador imprime la tabla completa:

```powershell
python scripts/test_router.py
```

## Desplegar en Heroku

`Procfile`, `.python-version` y `requirements.txt` ya están preparados. Instala el Heroku CLI, inicia sesión y sustituye `nombre-unico-app` por el nombre disponible para tu app:

```powershell
heroku login
heroku create nombre-unico-app --remote heroku
heroku config:set GOOGLE_API_KEY="TU_CLAVE_DE_GEMINI" MODELO="gemini-3.5-flash-lite" --app nombre-unico-app
git push heroku main
heroku open --app nombre-unico-app
```

Para revisar los logs:

```powershell
heroku logs --tail --app nombre-unico-app
```

La URL pública será `https://nombre-unico-app.herokuapp.com`; el puerto lo proporciona Heroku mediante `$PORT`. Configura credenciales solo como variables de entorno de Heroku, nunca en el código ni en Git.

## Preparar la conexión con Telegram

1. En Telegram, abre `@BotFather`, ejecuta `/newbot` y guarda el token en un gestor seguro.
2. Cuando el webhook esté implementado y verifique `X-Telegram-Bot-Api-Secret-Token`, configura las variables en Heroku. Reemplaza los valores de ejemplo; genera un secreto propio y aleatorio:

   ```powershell
   heroku config:set TELEGRAM_TOKEN="TOKEN_DE_BOTFATHER" TELEGRAM_SECRET="SECRETO_ALEATORIO" PUBLIC_URL="https://nombre-unico-app.herokuapp.com" --app nombre-unico-app
   ```

3. Una vez completada esa verificación en `/telegram`, registra la URL HTTPS del webhook en Telegram:

   ```powershell
   curl.exe -X POST "https://api.telegram.org/botTOKEN_DE_BOTFATHER/setWebhook" -d "url=https://nombre-unico-app.herokuapp.com/telegram" -d "secret_token=SECRETO_ALEATORIO"
   ```

**Estado actual:** `/telegram` solo acepta cualquier JSON y devuelve `{"ok":true}`. Aún no verifica el secreto, procesa mensajes ni responde al usuario. Por seguridad, no registres un webhook de producción hasta implementar la verificación y el flujo completo de Telegram.

## Bruno

La colección está en `bruno/`. Selecciona el entorno `Local` o `Heroku`; ambos definen `baseUrl` para alternar entre `http://localhost:8001` y la URL desplegada.
