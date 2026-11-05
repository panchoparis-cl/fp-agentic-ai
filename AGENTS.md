# Reglas del proyecto

- Los agentes van en `src/{nombre_agente}/` con `graph.py`, `prompts.py` y `tools.py`. Cada nodo tiene su propio prompt en `prompts.py`; no se escriben reglas dentro de `graph.py`.
- Se ejecutan desde la raíz con `python main.py {nombre_agente} "mensaje"`. El flag `--saltos` imprime los nodos por los que pasó el grafo. El flag `--diagrama` imprime el Mermaid del grafo sin ejecutarlo.
- La API va en `api/app.py` (FastAPI) y se levanta con `uvicorn api.app:app --reload --port 8000`.
- Los scripts sueltos van en `scripts/` y las pruebas en `tests/` (pytest).
- Para Heroku: `Procfile` con `web: uvicorn api.app:app --host 0.0.0.0 --port $PORT`, `.python-version` con `3.12` y `requirements.txt` siempre actualizado.
- `.gitignore` incluye `.env`, `.venv`, `__pycache__` y `.langgraph_api`.
- Nunca incluir credenciales reales en el código; usar variables de entorno y `.env.example` como plantilla.
