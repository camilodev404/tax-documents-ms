# tax-document-ms

Microservicio FastAPI para cargar filas de tramos de impuesto sobre la renta extraídas desde PDFs.

El flujo de negocio es determinista:

```text
PDF -> extracción local de texto -> OpenAI con LangChain -> salida estructurada Pydantic
    -> validación -> normalización -> transacción en PostgreSQL
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

Existe una restricción única sobre `source_document + source_record_id`.
La primera versión usa la estrategia idempotente más simple: omite registros que ya existen para el mismo documento y `record_id`; no reemplaza filas existentes.

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

Configura OpenAI solo para ejecutar la ingesta:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0
```

Los endpoints normales de la API no requieren OpenAI para iniciar.

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

Para procesar un PDF específico:

```bash
python -m app.commands.ingest_documents --file data/input/income-tax-brackets-2022.pdf
```

Para procesar todos los PDFs del directorio de entrada:

```bash
python -m app.commands.ingest_documents --input-dir data/input
```

El comando valida la ruta, extrae texto localmente con `pdfplumber`, ejecuta OpenAI mediante `ChatOpenAI`, valida todos los registros, normaliza tasas como fracciones decimales y persiste el documento en una sola transacción. Informa registros extraídos, insertados y omitidos.

Si falta `OPENAI_API_KEY` u `OPENAI_MODEL`, la ingesta falla con un error claro. Esa validación ocurre al ejecutar la ingesta, no al importar módulos ni al iniciar endpoints que no usan IA.

Para modelos `gpt-5*`, el adaptador omite el parámetro `temperature` y usa el valor por defecto del proveedor, porque esa familia puede rechazar temperaturas configurables.

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

La prueba opcional que llama OpenAI está marcada como `openai_integration` y queda excluida por defecto. Para ejecutarla, configura `OPENAI_API_KEY` y usa:

```bash
pytest -m openai_integration
```

## Lint y formato

```bash
ruff check .
ruff format .
```
