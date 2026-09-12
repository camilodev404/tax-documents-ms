# Tax Documents Service

## Overview

Tax Documents Service is a FastAPI microservice for ingesting personal income tax bracket tables from PDF documents, validating and normalizing the extracted rows, persisting them in PostgreSQL, and exposing the records through a read API.

The ingestion workflow uses AI only for structured extraction from PDF text. The `GET /tax-brackets` API reads persisted data from PostgreSQL and does not call OpenAI.

Implemented capabilities:

- Extract text from PDF files with `pdfplumber`.
- Use LangChain with OpenAI structured output for tax bracket extraction.
- Validate extracted records with Pydantic v2.
- Normalize `NO_LIMIT` to SQL `NULL`.
- Persist records transactionally with SQLAlchemy 2 and PostgreSQL.
- Prevent duplicate ingestion by `source_document` and `source_record_id`.
- Query all records or filter by tax year.
- Seed the demonstration database without OpenAI calls.

## Business Assumption and Dataset

The business domain is progressive personal income tax brackets. The project assumes all input PDFs belong to the same controlled domain and populate an already-defined relational model. The PDFs do not define new database fields.

The controlled dataset contains five annual documents:

- `income-tax-brackets-2022.pdf`
- `income-tax-brackets-2023.pdf`
- `income-tax-brackets-2024.pdf`
- `income-tax-brackets-2025.pdf`
- `income-tax-brackets-2026.pdf`

Each document contains 10 records, for a complete dataset of 50 records. The documents use the same table schema:

```text
record_id
tax_year
jurisdiction
currency
income_min
income_max
tax_rate
```

`NO_LIMIT` represents the absence of an upper income bound and is normalized to `None` in Python and SQL `NULL` in PostgreSQL.

This stable dataset is intentional: the exercise focuses on extraction, validation, persistence, API design, idempotency, deployment readiness, and documented production evolution. The tax data should be treated as synthetic demonstration data, not official tax legislation.

## Features

- `GET /health` health check.
- `GET /tax-brackets` list endpoint.
- Optional filters: `tax_year` and `jurisdiction`.
- Deterministic result ordering by `tax_year`, `jurisdiction`, `income_min`, and `source_record_id`.
- PDF ingestion command for one PDF or all PDFs in `data/input`.
- Portable seed command for loading the verified 50-record dataset without OpenAI.
- Alembic migration for the initial schema.
- Unit and integration test coverage for validation, normalization, idempotency, repository behavior, seed loading, and API filtering.

## Technology Stack

| Technology | Purpose |
| --- | --- |
| Python 3.12 | Application runtime and Docker image runtime |
| FastAPI | HTTP API and OpenAPI documentation |
| PostgreSQL 16 | Relational persistence |
| SQLAlchemy 2 | ORM and repository implementation |
| Alembic | Database migrations |
| Pydantic v2 | Request, response, extraction, and seed validation |
| pydantic-settings | Environment-based configuration |
| LangChain | OpenAI chat model integration and structured output |
| OpenAI `gpt-5-nano` | Intended model for real PDF ingestion |
| `pdfplumber` | Local PDF text extraction |
| Pytest | Unit and integration tests |
| Ruff | Linting and formatting |
| Docker and Docker Compose | Local runtime and production image validation |

## Architecture

### Processing Flow

Ingestion flow:

```text
PDF
→ PDF text extraction
→ LangChain/OpenAI structured extraction
→ Pydantic validation
→ normalization
→ ingestion service
→ repository
→ PostgreSQL
```

Query flow:

```text
HTTP client
→ FastAPI router
→ query service/repository
→ PostgreSQL
→ validated JSON response
```

OpenAI is used during ingestion only. GET requests never invoke the AI extractor.

### C4 Component Diagram

```mermaid
C4Component
    title Tax Documents Service - Component Diagram

    Person(client, "API Consumer", "Queries persisted tax bracket records")
    System_Ext(openai, "OpenAI API", "Produces structured extraction output")
    ContainerDb(postgres, "PostgreSQL", "PostgreSQL 16", "Stores normalized income tax brackets")

    Container_Boundary(service, "Tax Documents Service") {
        Component(app, "FastAPI Application", "app.main", "Creates the API application and registers routers")
        Component(health, "Health Router", "FastAPI router", "Exposes GET /health")
        Component(api, "Tax Brackets Router", "FastAPI router", "Exposes GET /tax-brackets")
        Component(query, "Tax Bracket Service", "Application service", "Coordinates read use cases")
        Component(ingestion, "Ingestion Command", "Python CLI", "Coordinates PDF ingestion")
        Component(reader, "PDF Reader", "pdfplumber", "Extracts text from PDF files")
        Component(extractor, "Structured Extractor", "LangChain and OpenAI", "Converts PDF text into structured records")
        Component(validation, "Validation and Normalization", "Pydantic and service functions", "Validates records and normalizes decimal values")
        Component(repository, "Tax Bracket Repository", "SQLAlchemy", "Reads and writes income tax bracket records")
        Component(seed, "Seed Command", "Python CLI", "Loads portable seed data idempotently")
    }

    Rel(client, health, "Checks service health", "HTTP/JSON")
    Rel(client, api, "Queries tax brackets", "HTTP/JSON")
    Rel(app, health, "Registers")
    Rel(app, api, "Registers")
    Rel(api, query, "Uses")
    Rel(query, repository, "Reads")
    Rel(ingestion, reader, "Reads PDF")
    Rel(reader, extractor, "Provides extracted text")
    Rel(extractor, openai, "Requests structured extraction", "HTTPS")
    Rel(extractor, validation, "Returns structured records")
    Rel(validation, repository, "Persists valid records")
    Rel(seed, validation, "Validates seed records")
    Rel(seed, repository, "Persists missing records")
    Rel(repository, postgres, "Reads and writes", "SQL")
```

### Component Responsibilities

| Component | Path | Responsibility |
| --- | --- | --- |
| FastAPI application | `app/main.py` | Configures logging and registers API routers. |
| Health router | `app/api/routes/health.py` | Provides `GET /health`. |
| Tax brackets router | `app/api/routes/tax_brackets.py` | Provides `GET /tax-brackets` with optional filters. |
| Database dependencies | `app/api/dependencies.py` | Provides database sessions and application services to routers. |
| SQLAlchemy model | `app/models/tax_bracket.py` | Defines the `income_tax_brackets` table mapping. |
| API schemas | `app/schemas/tax_bracket.py` | Defines create and response validation models. |
| Repository | `app/repositories/tax_bracket_repository.py` | Encapsulates SQLAlchemy read/write operations and duplicate skipping. |
| Query service | `app/services/tax_bracket_service.py` | Coordinates read use cases for the API. |
| PDF reader | `app/infrastructure/pdf_reader.py` | Extracts text from PDF files using `pdfplumber`. |
| Extractor protocol | `app/services/tax_document_extractor.py` | Defines the application-facing extraction interface. |
| LangChain extractor | `app/infrastructure/ai/langchain_extractor.py` | Invokes OpenAI through LangChain structured output. |
| Extraction schemas | `app/infrastructure/ai/extractor.py` | Validates AI extraction output and normalizes PDF strings. |
| Ingestion service | `app/services/tax_document_ingestion.py` | Orchestrates document ingestion and transactional persistence. |
| Ingestion command | `app/commands/ingest_documents.py` | CLI entry point for PDF ingestion. |
| Seed service | `app/services/tax_bracket_seed.py` | Loads validated seed records transactionally. |
| Seed command | `app/cli/seed_tax_brackets.py` | CLI entry point for portable seed loading. |

## AI-Powered PDF Extraction

`PdfTextReader` validates the file path, requires a `.pdf` extension, and extracts page text with `pdfplumber`. It raises `PdfReadError` when the file is missing, invalid, unreadable, or contains no extractable text.

`LangChainTaxDocumentExtractor` builds a `ChatOpenAI` model from runtime configuration and calls `with_structured_output(ExtractedTaxBrackets, method="json_schema", strict=True)`. The system prompt instructs the model to:

- extract only rows present in the table;
- keep PDF `record_id` as `source_record_id`;
- convert `NO_LIMIT` to `null`;
- represent `10%` as `0.10`;
- not generate `id`, `created_at`, or `source_document`.

For model names starting with `gpt-5`, the adapter omits the `temperature` request parameter because this model family may reject configurable temperature values through the provider API. The configured model for the assignment is `gpt-5-nano`.

LangGraph is intentionally not used. The workflow is linear and deterministic, with no agent planning, tools, memory, or autonomous branching.

### Structured Output and Validation

The AI response is validated by `ExtractedTaxBrackets` and `ExtractedTaxBracket` in `app/infrastructure/ai/extractor.py`.

Normalization and validation behavior:

- Numeric strings are converted to `Decimal`.
- Thousands separators are removed before decimal conversion.
- Percent strings such as `10%` become decimal fractions such as `0.10`.
- `NO_LIMIT` becomes `None`.
- `currency` is normalized to uppercase.
- `income_max` must be greater than `income_min` when present.
- `tax_rate` must be between `0` and `1`.

The ingestion service then validates document-level constraints, including unique `source_record_id` values and continuous income brackets per `(tax_year, jurisdiction)`. It quantizes tax rates to four decimal places before persistence.

Invalid extraction output fails before persistence. Persistence uses a transaction per document, so a failed document does not leave partial rows.

### Idempotency

The implementation has two idempotency layers:

1. Before reading and extracting a PDF, `TaxDocumentIngestionService` checks whether rows already exist for the `source_document`. If records exist, ingestion is skipped before any OpenAI call.
2. PostgreSQL enforces a unique constraint on:

```text
(source_document, source_record_id)
```

Verified skip behavior for an already processed 10-record document:

```text
status=skipped
extracted=0
valid=0
inserted=0
skipped=10
reason=source_document_already_processed
```

This document-level existence check is safe for the controlled workflow because each source document is persisted atomically. The implementation does not include checksum-based document version tracking.

## Data Model

The primary entity is `IncomeTaxBracket`, persisted in the `income_tax_brackets` table.

| Column | SQL type | Nullable | Purpose |
| --- | --- | --- | --- |
| `id` | `UUID` | No | Internally generated primary key. |
| `source_record_id` | `INTEGER` | No | `record_id` extracted from the source PDF. |
| `tax_year` | `INTEGER` | No | Tax year for the bracket. Indexed. |
| `jurisdiction` | `VARCHAR(120)` | No | Jurisdiction name from the PDF. |
| `currency` | `VARCHAR(3)` | No | Three-letter uppercase currency code. |
| `income_min` | `NUMERIC(18,2)` | No | Lower income bound. |
| `income_max` | `NUMERIC(18,2)` | Yes | Upper income bound, or `NULL` when no upper limit exists. |
| `tax_rate` | `NUMERIC(7,4)` | No | Decimal fraction tax rate, where `0.10 = 10%`. |
| `source_document` | `VARCHAR(255)` | No | Source PDF filename. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | Database-generated creation timestamp. |

Monetary values and tax rates use `NUMERIC` in PostgreSQL and `Decimal` in Python. They are never stored as floating-point types.

## API

### Health Check

```http
GET /health
```

Example:

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "ok"
}
```

Expected status: `200 OK`.

### List All Tax Brackets

```http
GET /tax-brackets
```

Example:

```bash
curl http://localhost:8000/tax-brackets
```

When the complete seed is loaded, this returns 50 records. Results are ordered by `tax_year`, `jurisdiction`, `income_min`, and `source_record_id`.

Representative response shape:

```json
[
  {
    "id": "bd86ea55-56bb-446c-a7cc-8c7c74313545",
    "source_record_id": 1,
    "tax_year": 2022,
    "jurisdiction": "North Region",
    "currency": "USD",
    "income_min": "0.00",
    "income_max": "18000.00",
    "tax_rate": "0.0000",
    "source_document": "income-tax-brackets-2022.pdf",
    "created_at": "2026-09-12T01:18:26.388193Z"
  }
]
```

Expected status: `200 OK`.

### Filter by Tax Year

```http
GET /tax-brackets?tax_year=2022
```

Example:

```bash
curl "http://localhost:8000/tax-brackets?tax_year=2022"
```

Each valid year from 2022 through 2026 returns 10 records when the complete seed is loaded.

The router also supports an optional exact `jurisdiction` filter:

```bash
curl "http://localhost:8000/tax-brackets?tax_year=2022&jurisdiction=North%20Region"
```

### Empty Results and Validation Errors

- A year with no records returns `200 OK` and an empty JSON list: `[]`.
- A non-integer `tax_year` returns FastAPI's standard `422 Unprocessable Entity` validation response.
- A non-positive integer such as `tax_year=0` also returns `422 Unprocessable Entity` because the query parameter is constrained with `gt=0`.

### Interactive Documentation

FastAPI exposes interactive OpenAPI documentation at:

```http
GET /docs
```

Example:

```bash
open http://localhost:8000/docs
```

## Project Structure

```text
app/
  main.py
  api/
    dependencies.py
    routes/
      health.py
      tax_brackets.py
  core/
    config.py
    logging.py
  infrastructure/
    database.py
    pdf_reader.py
    ai/
      extractor.py
      langchain_extractor.py
  models/
    tax_bracket.py
  repositories/
    tax_bracket_repository.py
  schemas/
    tax_bracket.py
  services/
    tax_bracket_seed.py
    tax_bracket_service.py
    tax_bracket_validation.py
    tax_document_extractor.py
    tax_document_ingestion.py
  commands/
    ingest_documents.py
  cli/
    seed_tax_brackets.py
alembic/
  versions/
    0001_create_income_tax_brackets.py
data/
  input/
  seed/
    income_tax_brackets.json
tests/
  unit/
  integration/
Dockerfile
docker-compose.yml
pyproject.toml
```

## Configuration

Configuration is loaded with `pydantic-settings` from environment variables and `.env` when present. `.env.example` documents the expected variables. Do not commit real secrets.

| Variable | Required | Used by | Description |
| --- | --- | --- | --- |
| `APP_NAME` | No | Application settings | Service name. |
| `DATABASE_URL` | Yes | API, migrations, seed, ingestion | SQLAlchemy database URL. |
| `INPUT_DIR` | No | Ingestion command | Directory used when ingesting all PDFs. Defaults to `data/input`. |
| `OPENAI_API_KEY` | Only for real PDF ingestion | Ingestion command | OpenAI credential. Not needed for GET requests, migrations, or seed loading. |
| `OPENAI_MODEL` | Only for real PDF ingestion | Ingestion command | Chat model name. Use `gpt-5-nano` for the assignment run. |
| `OPENAI_TEMPERATURE` | No | Ingestion command | Temperature for non-`gpt-5` models. Defaults to `0`. |
| `POSTGRES_DB` | Docker Compose | PostgreSQL container | Database name used by Compose. |
| `POSTGRES_USER` | Docker Compose | PostgreSQL container | Database user used by Compose. |
| `POSTGRES_PASSWORD` | Docker Compose | PostgreSQL container | Database password used by Compose. |

API running from the host:

```env
DATABASE_URL=postgresql+psycopg://tax_user:local_password@localhost:5432/tax_documents
```

API running in Docker Compose:

```env
DATABASE_URL=postgresql+psycopg://tax_user:local_password@db:5432/tax_documents
```

`db` is the Docker Compose service hostname. `localhost` from inside the API container points to the API container itself, not the PostgreSQL container.

The production image does not include `.env`; runtime configuration must be injected through the deployment environment.

## Running Locally with Docker Compose

### Start the Database

```bash
docker compose up -d db
docker compose ps
```

### Run Database Migrations

```bash
docker compose run --rm api alembic upgrade head
```

The `api` service command also runs `alembic upgrade head` before starting Uvicorn.

### Populate the Database from Seed Data

```bash
docker compose run --rm api python -m app.cli.seed_tax_brackets data/seed/income_tax_brackets.json
```

Expected first execution on an empty migrated database:

```text
received=50 inserted=50 skipped=0 invalid=0
```

Expected second execution:

```text
received=50 inserted=0 skipped=50 invalid=0
```

### Start the API

```bash
docker compose up -d api
```

The API listens on port `8000`.

### Verify the Deployment

```bash
curl http://localhost:8000/health
curl http://localhost:8000/tax-brackets
curl "http://localhost:8000/tax-brackets?tax_year=2022"
```

To enter PostgreSQL without expanding credentials in the shell:

```bash
docker compose exec -it db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### Stop the Services

```bash
docker compose down
```

This stops and removes the containers and default network while preserving the named PostgreSQL volume. Do not use `docker compose down -v` unless you intentionally want to delete the database volume.

## Running the PDF Ingestion Pipeline

Real PDF ingestion requires `OPENAI_API_KEY` and `OPENAI_MODEL`. It is not required to test the GET API because seed data can initialize the database without OpenAI.

Ingest one PDF from the host:

```bash
python3 -m app.commands.ingest_documents --file data/input/income-tax-brackets-2022.pdf
```

Ingest all PDFs discovered in `INPUT_DIR` or `data/input`:

```bash
python3 -m app.commands.ingest_documents --input-dir data/input
```

Compose variant for one PDF:

```bash
docker compose run --rm api python -m app.commands.ingest_documents --file data/input/income-tax-brackets-2022.pdf
```

Behavior:

- Each unprocessed PDF causes one OpenAI structured extraction call.
- If `source_document` already exists in the database, the document is skipped before OpenAI is called.
- The document is persisted in a single transaction.
- A failure rolls back that document's transaction.
- The seed command is preferred for demonstration deployment because it does not require OpenAI and does not spend API credits.

## Seed Data

The portable seed file is:

```text
data/seed/income_tax_brackets.json
```

It contains 50 validated records: 10 for each year from 2022 through 2026.

Run it with:

```bash
python -m app.cli.seed_tax_brackets data/seed/income_tax_brackets.json
```

The seed loader:

- validates every record with `IncomeTaxBracketCreate`;
- rejects JSON floats so decimals must be encoded as strings;
- uses the existing SQLAlchemy repository;
- runs transactionally;
- skips existing `(source_document, source_record_id)` pairs;
- does not read PDFs;
- does not call OpenAI.

## Testing

Install development dependencies first:

```bash
pip install -e ".[dev]"
```

Run the normal suite:

```bash
python3 -m pytest tests/unit
python3 -m pytest tests/integration -m "not openai_integration"
python3 -m ruff check .
python3 -m ruff format --check .
```

Verification snapshot from the latest local run:

```text
Unit tests: 14 passed
Integration tests: 21 passed, 1 deselected
Ruff check: passed
Ruff format check: passed
```

The optional OpenAI integration test is marked `openai_integration` and excluded from the normal suite because it requires a real API key and makes an external provider call.

## Production Docker Image

Build the image:

```bash
docker build -t tax-documents-ms:local .
```

The image:

- uses Python 3.12;
- runs the application as a non-root user;
- does not contain `.env`;
- does not contain source PDFs from `data/input`;
- includes `data/seed/income_tax_brackets.json`;
- can run the API, Alembic, and seed command as separate commands;
- does not automatically invoke OpenAI;
- does not automatically seed every replica;
- reads `DATABASE_URL` at runtime.

Latest local verification showed an approximate image size of 120 MB.

Example separate commands:

```bash
docker run --rm --network tax-documents-ms_default \
  -e DATABASE_URL='postgresql+psycopg://<user>:<password>@db:5432/<database>' \
  tax-documents-ms:local alembic upgrade head

docker run --rm --network tax-documents-ms_default \
  -e DATABASE_URL='postgresql+psycopg://<user>:<password>@db:5432/<database>' \
  tax-documents-ms:local \
  python -m app.cli.seed_tax_brackets data/seed/income_tax_brackets.json

docker run --rm --network tax-documents-ms_default -p 8000:8000 \
  -e DATABASE_URL='postgresql+psycopg://<user>:<password>@db:5432/<database>' \
  tax-documents-ms:local
```

## Parallel Processing Strategy

Current ingestion is sequential. `TaxDocumentIngestionService.ingest_files` processes the provided paths one at a time, while isolating failures per document.

Proposed bounded-concurrency evolution:

- Process different PDFs concurrently with a small configurable worker limit.
- Give each document its own SQLAlchemy session and transaction.
- Do not share SQLAlchemy sessions across workers.
- Preserve document-level atomicity.
- Respect OpenAI rate limits.
- Retry transient provider failures with exponential backoff.
- Use the database uniqueness constraint and document-level status to prevent duplicate work.
- For larger workloads, move ingestion to a queue/worker model.

A suitable future AWS-oriented ingestion topology would be:

```text
S3 → SQS → ECS workers → RDS PostgreSQL
```

This queue and worker model is proposed future work; it is not implemented in this repository.

## Bottlenecks and Scalability

Concrete bottlenecks:

- OpenAI request latency during ingestion.
- OpenAI rate limits and cost.
- PDF text extraction quality.
- Scanned PDFs requiring OCR, which is not implemented.
- Large PDFs increasing prompt size.
- Database connection pool limits under concurrent ingestion.
- Concurrent duplicate ingestion attempts.
- Long synchronous ingestion jobs.
- Single-instance availability in a demonstration deployment.

Mitigations and proposed improvements:

- Bounded concurrency for PDF ingestion.
- Retry and backoff for transient provider errors.
- Queue-based workers for larger workloads.
- OCR fallback for scanned PDFs.
- Chunking or table-aware extraction for larger documents.
- Explicit database connection-pool sizing.
- Checksums and processing-status tracking for document versions.
- Separate API and worker services.
- RDS PostgreSQL and ECS/Fargate for production.

## Security Considerations

Implemented safeguards:

- No real credentials are required in source control.
- `.env` is excluded from the Docker image build context.
- Source PDFs are excluded from the production image build context.
- OpenAI credentials are required only for real PDF ingestion.
- GET requests, migrations, and seed loading do not require `OPENAI_API_KEY`.
- SQLAlchemy generates parameterized SQL for ORM queries.
- Pydantic validates extraction, seed, and response data.
- PostgreSQL enforces the uniqueness constraint.
- The application image runs as a non-root user.

Important limitations:

- The GET API is public and unauthenticated.
- API rate limiting is not implemented.
- In the intended EC2 demonstration deployment, PostgreSQL port `5432` should not be publicly exposed by the EC2 security group.
- Production secrets should be managed with AWS Secrets Manager or an equivalent secret manager.
- Production traffic should use HTTPS through a load balancer or reverse proxy.

## Deployment

### Current Demonstration Deployment

Do not treat the following placeholders as a live deployment:

- API: `http://<PUBLIC_IP>:8000/tax-brackets`
- Swagger UI: `http://<PUBLIC_IP>:8000/docs`
- Health check: `http://<PUBLIC_IP>:8000/health`

Intended demonstration topology:

- One Amazon EC2 instance.
- API and PostgreSQL in separate Docker containers.
- Docker Compose orchestration.
- Named PostgreSQL volume.
- Port `8000` publicly available.
- Port `5432` blocked by the EC2 security group.
- Seed command initializes the 50 records.
- No OpenAI key is required to serve GET requests.

### Proposed Production Architecture

Proposed production evolution:

- Amazon ECR for image storage.
- Amazon ECS Fargate for API and worker services.
- Application Load Balancer for HTTPS traffic.
- Amazon RDS for PostgreSQL.
- AWS Secrets Manager for database and OpenAI secrets.
- CloudWatch for logs and metrics.
- Private database networking.
- Separate ingestion workers for PDF processing.
- Optional S3 and SQS for document storage and asynchronous ingestion.

These are proposed production improvements, not implemented infrastructure in this repository.

## Design Decisions and Trade-offs

- PostgreSQL was selected because all documents populate the same stable relational model.
- One normalized table is sufficient for the controlled domain.
- `Decimal` and PostgreSQL `NUMERIC` were selected for monetary values and tax rates.
- LangChain structured output reduces parsing ambiguity when converting PDF table text to typed records.
- Pydantic remains the application validation boundary even when the model returns structured output.
- LangGraph was avoided because the ingestion workflow is linear and deterministic.
- Document-level short-circuiting reduces unnecessary OpenAI cost.
- The PostgreSQL unique constraint provides final duplicate protection.
- Seed-based deployment avoids repeated AI calls for the demonstration dataset.
- EC2 plus Docker Compose prioritizes delivery simplicity for the take-home assignment.
- ECS plus RDS is the proposed production evolution.

## Known Limitations

- The dataset uses a controlled PDF layout and stable schema.
- OCR for scanned documents is not implemented.
- Checksum-based document version tracking is not implemented.
- The GET endpoint has no authentication or rate limiting.
- Ingestion currently runs sequentially.
- The demonstration deployment has a single EC2 failure domain.
- CI/CD is not included in this repository.
- The initial public demonstration is expected to use HTTP unless HTTPS is added through a proxy or load balancer.
- The tax data is synthetic and not official tax guidance.

## Future Improvements

- Add document checksum tracking and ingestion status records.
- Add bounded-concurrency ingestion.
- Split API and ingestion workers.
- Add OCR fallback for scanned PDFs.
- Add API authentication and rate limiting.
- Add structured observability: request logs, ingestion metrics, and provider latency metrics.
- Add CI/CD for linting, tests, image build, and deployment.
- Deploy production infrastructure with ECS, RDS, Secrets Manager, CloudWatch, HTTPS, and private networking.
