Librería Jehová Jiréh — IA (Texto únicamente)

Este proyecto integra IA solo para generación de texto (sin imágenes). Las respuestas de IA están enfocadas al dominio de una librería: catálogo, productos, autores, ISBN, precios, stock, carrito, autenticación básica, facturación y endpoints propios.

**Contenido**
- Configuración de entorno (solo texto)
- Guardrails de dominio (whitelist)
- Pruebas rápidas
- Notas de seguridad
 - Endpoints API (resumen)
 - Variables de entorno

**Configuración de entorno**

- Copia `.env.example` a `.env` y completa los valores reales:

```
AI_PROVIDER=gemini
GEMINI_API_KEY=tu_api_key
GEMINI_MODEL=gemini-2.5-flash-latest
GEMINI_TIMEOUT=15
GEMINI_MAX_RETRIES=3

AI_DOMAIN_WHITELIST_ENABLED=true
AI_DOMAIN_WHITELIST="librería,catalogo,producto,autor,isbn,precio,stock,carrito,login,registro,verificación,factura,pedido,envío,tarifa,logística,usuario,correo,endpoint,/api/v1"
```

- Reinicia la aplicación Flask para aplicar cambios.

Notas:
- No hay soporte de imágenes: no se envían ni aceptan imágenes.
- `AI_PROVIDER=gemini` usa el endpoint Gemini v1 (texto).

**Guardrails de dominio (whitelist)**

- Cuándo aplica: cuando `AI_DOMAIN_WHITELIST_ENABLED=true`.
- Qué permite: consultas sobre la librería y su catálogo (términos en `AI_DOMAIN_WHITELIST`).
- Qué rechaza: temas fuera del dominio (clima, política, noticias, etc.).
- Cómo ajustar el dominio permitido: edita `AI_DOMAIN_WHITELIST` (lista separada por comas) y reinicia.

Activar whitelist (por defecto):
```
AI_DOMAIN_WHITELIST_ENABLED=true
```

Desactivar whitelist (permite temas generales bajo tu propio riesgo):
```
AI_DOMAIN_WHITELIST_ENABLED=false
```

Respuesta de rechazo (estándar sugerida):
- "Lo siento, solo puedo ayudarte con temas relacionados a la Librería Jehová Jiréh (catálogo, productos, ISBN, stock, pedidos y endpoints de la app)."

**Pruebas rápidas**

Puedes probar desde el navegador o con `curl`.

- Caso permitido
  - Pregunta: "¿Qué filtros tiene el catálogo? ¿Puedo buscar por ISBN?"
  - Esperado: respuesta breve explicando filtros soportados y confirmando búsqueda por ISBN.

- Caso bloqueado
  - Pregunta: "Cuéntame sobre el clima de Guatemala"
  - Esperado (con whitelist activa): rechazo estándar indicando que el tema está fuera del dominio.

Rutas útiles (según tu app):
- `POST /api/v1/ia/chat` con cuerpo JSON `{ "mensaje": "..." }`
- Dev: `POST /api/v1/ai/gemini-ping` con cuerpo `{ "prompt": "..." }`

**Notas de seguridad**

- No se registran prompts completos ni PII; los logs incluyen solo metadatos (proveedor, modelo, estado, latencia y, si aplica, MIME/tamaño) sin claves ni contenido sensible.
- No se exponen API keys: coloca `GEMINI_API_KEY` solo en `.env` local/seguro.
- Controla el dominio temático con `AI_DOMAIN_WHITELIST_ENABLED` y `AI_DOMAIN_WHITELIST`.

**Endpoints API (resumen)**

- Auth `/api/v1/auth`
  - POST `/register` → crea usuario (devuelve usuario)
  - POST `/login` → devuelve `access_token`, `refresh_token`
  - POST `/refresh` → renueva access/refresh
  - GET `/me` → estado autenticación
  - POST `/logout` → revoca refresh

- Catálogo `/api/v1/catalogo`
  - GET `/productos?q=&tipo=&orden=&page=&limit=` → `{ items, page, limit, total, pages }`
  - GET `/productos/:id` → detalle normalizado
  - (admin) POST `/productos`, PUT `/productos/:id`, DELETE `/productos/:id`
  - Google Books proxy: GET `/books/search` y GET `/books/:volumeId`, POST `/books/import` (admin)

- Carrito `/api/v1/carrito` (JWT requerido)
  - GET `/` → `{ items, total }`
  - POST `/items` → `{ id/nombre/precio/cantidad/portada_url }`
  - PUT `/items/:producto_id` → `{ cantidad }`
  - DELETE `/items/:producto_id`

- Pedidos `/api/v1/pedidos` (JWT)
  - POST `/checkout` → crea pedido `pending_payment` (idempotente por header `Idempotency-Key`)

- Pagos `/api/v1/payments`
  - POST `/stripe/create-payment-intent` `{ pedido_id?, total? }` → valida total servidor y devuelve `clientSecret`
  - POST `/paypal/create-order` `{ pedido_id?, total?, currency }` → valida total servidor y devuelve `approveUrl`
  - POST `/paypal/capture` `{ orderID, pedido_id }` → mock captura y valida contra total servidor

- Facturación `/api/v1/facturas`
  - POST `/` → crea factura `{items:[{nombre,precio,cantidad}]}`
  - GET `/:id`
  - GET `/?usuario_id=&page=&limit=` (JWT)

- IA `/api/v1/ia`
  - POST `/chat` `{ mensaje }` → `{ texto }` (whitelist de dominio, SOLO TEXTO)

**Variables de entorno**

- Básicas
  - `SECRET_KEY`, `JWT_SECRET`, `SQLALCHEMY_DATABASE_URI` (o usa sqlite por defecto)
  - `ALLOWED_ORIGINS` (CORS, CSV), `RATE_LIMIT_PER_MIN` (por ruta sensible)

- Google Books
  - `GOOGLE_BOOKS_API_KEY`, `GOOGLE_BOOKS_BASE_URL=https://www.googleapis.com/books/v1`
  - `GOOGLE_BOOKS_DEFAULT_LANG=es`, `GOOGLE_BOOKS_TIMEOUT=10`, `GOOGLE_BOOKS_CACHE_TTL=900`

- IA
  - `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.5-flash`, `GEMINI_TIMEOUT`, `GEMINI_MAX_RETRIES`

- Pagos
  - Stripe: `STRIPE_SECRET_KEY`
  - PayPal: `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_API_BASE` (sandbox por defecto)

# proyeto_2025
