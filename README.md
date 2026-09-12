# tax-document-ms

Microservicio FastAPI para cargar filas de tramos de impuesto sobre la renta extraídas desde PDFs.

El flujo de negocio es determinista:

```text
PDF -> extracción con LLM -> validación -> normalización -> persistencia
```

No usa LangGraph, agentes, herramientas ni memoria. LangChain queda limitado al adaptador de modelo con salida estructurada.

## Modelo de datos

La entidad principal es `IncomeTaxBracket`.

Campos:

- `id`: UUID generado internamente.
- `source_record_id`: entero extraído desde `record_id` del PDF.
- `tax_year`: año fiscal.
- `jurisdiction`: jurisdicción.
- `currency`: código ISO de tres caracteres.
- `income_min`: decimal.
- `income_max`: decimal nullable. `NULL` representa ausencia de límite superior.
- `tax_rate`: decimal.
- `source_document`: nombre del PDF origen.
- `created_at`: timestamp generado por la base de datos.

Existe una restricción única sobre `source_document + source_record_id`, por lo que repetir la ingesta no duplica registros.

## Convenciones de normalización

- `NO_LIMIT` en el PDF se normaliza como `None` y se persiste como `NULL`.
- Las tasas se persisten como fracción decimal con cuatro decimales.
  - `10%` se normaliza como `0.1000`.
- Montos y tasas usan `Decimal`; no se almacenan como strings ni `float`.

## Instalación local

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Ejecutar PostgreSQL

```bash
docker compose up -d db
```

## Migrar la base de datos

```bash
alembic upgrade head
```

## Ejecutar la API

```bash
uvicorn app.main:app --reload
```

Endpoints iniciales:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/tax-brackets
curl "http://localhost:8000/tax-brackets?tax_year=2024"
```

Si no hay resultados, `GET /tax-brackets` responde `200 OK` con `[]`.
Si el filtro es inválido, por ejemplo `tax_year=0`, FastAPI responde `422 Unprocessable Entity`.

## Cargar PDFs

Coloca los archivos en:

```text
data/input/
```

Ejecuta:

```bash
python -m app.commands.ingest_documents --input-dir data/input
```

El adaptador `LangChainTaxDocumentExtractor` es intencionalmente un placeholder. Para usar IA real falta configurar un proveedor y modelo concretos de LangChain e inyectar un `BaseChatModel`. Sin esa configuración, el comando falla claramente y no intenta inventar extracción.

## Docker Compose

```bash
docker compose up --build
```

Esto levanta PostgreSQL, ejecuta migraciones y publica la API en:

```text
http://localhost:8000
```

## Pruebas

```bash
pytest
```

## Lint y formato

```bash
ruff check .
ruff format .
```
