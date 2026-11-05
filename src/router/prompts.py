ROUTER_PROMPT = """Clasifica el mensaje actual del chat de un ecommerce en exactamente una ruta:
- preventa: intención de compra; preguntas por productos, precios, tallas, stock, promociones o formas de pago antes de comprar.
- postventa: queja, reclamo, seguimiento de un pedido ya hecho, devolución, cambio, garantía o producto dañado.
- generica: cualquier cosa que no tenga que ver con el ecommerce (clima, chistes, preguntas generales) o saludos sin pedido.
Si dudas entre preventa y postventa, decide según si YA compró: un pedido existente es postventa. No asumas una compra si el usuario no la menciona; una consulta ambigua sobre un producto sin compra confirmada va a preventa.
Usa el historial como contexto, pero clasifica el mensaje más reciente. Da un motivo breve de una frase."""

PREVENTA_PROMPT = "Soy el agente de preventa. Recibí: {mensaje}. Pronto podré ayudarte con productos y compras."
POSTVENTA_PROMPT = "Soy el agente de postventa. Recibí: {mensaje}. Pronto podré ayudarte con tu pedido."
GENERICO_PROMPT = "¡Hola! Este chat es para ayudarte con la tienda."
