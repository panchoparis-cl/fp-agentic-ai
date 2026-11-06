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

Edita `.env` y añade tu `GOOGLE_API_KEY`. No compartas ni subas ese archivo. La API usa `TELEGRAM_TOKEN` y `TELEGRAM_SECRET` para el webhook; los scripts de Telegram también leen `PUBLIC_URL`.

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

Swagger está en <http://localhost:8001/docs>. La API ofrece `GET /health`, `POST /chat` y `POST /telegram`. El webhook de Telegram valida el secreto, enruta mensajes de texto por `chat_id` y contesta usando la API de Telegram. Ejemplo de chat desde PowerShell:

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

## Telegram

1. En Telegram, abre `@BotFather`, envía `/newbot` y sigue las instrucciones. Copia el token y elige un secreto aleatorio para el webhook. Configura ambos como variables de Heroku (sustituye `nombre-unico-app` y los valores de ejemplo):

   ```powershell
   heroku config:set TELEGRAM_TOKEN="TOKEN_DE_BOTFATHER" TELEGRAM_SECRET="SECRETO_ALEATORIO" --app nombre-unico-app
   ```

   Guarda también `TELEGRAM_TOKEN` y `TELEGRAM_SECRET` en tu `.env` local para que los scripts puedan llamar a Telegram. No subas `.env` a GitHub.

2. Añade y publica los cambios en GitHub y Heroku:

   ```powershell
   git add .
   git commit -m "Conecta Telegram a la API"
   git push origin main
   git push heroku main
   ```

3. Configura la URL pública de Heroku y registra el webhook. El script lee `TELEGRAM_TOKEN`, `TELEGRAM_SECRET` y `PUBLIC_URL` del entorno o de `.env`:

   ```powershell
   heroku config:set PUBLIC_URL="https://nombre-unico-app.herokuapp.com" --app nombre-unico-app
   $env:PUBLIC_URL = "https://nombre-unico-app.herokuapp.com"
   python scripts/set_webhook.py
   python scripts/webhook_info.py
   ```

   En `getWebhookInfo`, confirma que `url` termine en `/telegram` y que no haya errores pendientes (`last_error_message`).

4. En otro terminal, observa los logs y después envía estos mensajes al bot, uno por uno:

   ```powershell
   heroku logs --tail --app nombre-unico-app
   ```

   - `¿tienen la polera azul en talla M?` → `preventa`
   - `mi pedido 4521 llegó roto` → `postventa`
   - `hola` → `generica`
   - `¿cuánto cuesta el envío a Valparaíso?` → `preventa`
   - `quiero devolver unas zapatillas` → `postventa`
   - `¿qué hora es en Tokio?` → `generica`

   En cada entrada de log `Telegram ... ruta=...` verifica que aparezca la ruta esperada.

5. Si el bot no responde, comprueba que el webhook use la URL HTTPS exacta con `/telegram`, que `TELEGRAM_SECRET` en Heroku coincida con el secreto registrado en Telegram, que el token de BotFather sea correcto y que la app esté activa. Revisa `python scripts/webhook_info.py` y `heroku logs --tail --app nombre-unico-app`.

### Prueba local opcional con cloudflared

Con Uvicorn corriendo en el puerto 8001 y las credenciales de Telegram en `.env`, abre otro terminal y ejecuta:

```powershell
cloudflared tunnel --url http://localhost:8001
```

Usa la URL HTTPS `trycloudflare.com` que imprime el comando:

```powershell
$env:PUBLIC_URL = "https://tu-subdominio.trycloudflare.com"
python scripts/set_webhook.py
python scripts/webhook_info.py
```

Telegram mantiene un solo webhook por bot: esto reemplaza temporalmente el de Heroku. Para volver a Heroku, restaura `PUBLIC_URL` a la URL de Heroku y ejecuta de nuevo `python scripts/set_webhook.py`.

## Bruno

La colección está en `bruno/`. Selecciona el entorno `Local` o `Heroku`; ambos definen `baseUrl` para alternar entre `http://localhost:8001` y la URL desplegada.
