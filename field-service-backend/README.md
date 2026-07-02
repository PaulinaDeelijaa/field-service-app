# field-service-backend

FastAPI + PostgreSQL backend for the Offline-First Field Service platform.

---

## System Design

### Why offline-first matters here

Field workers operate in basements, tunnels, remote sites, and RF-shielded
equipment rooms.  The mobile app must complete its full workflow (view tasks,
submit reports, capture photos) without any network dependency.  The backend
is the *source of truth* but it is never a *prerequisite* for doing work.

---

## Database Schema

```
┌─────────────┐      ┌─────────────────┐      ┌──────────────┐
│    users    │      │      tasks      │      │ task_reports │
│─────────────│      │─────────────────│      │──────────────│
│ id (PK)     │◄─────│ assigned_to_id  │      │ id (PK)      │
│ email       │◄─────│ created_by_id   │◄─────│ task_id (FK) │
│ full_name   │      │ client_id       │      │ worker_id FK)│
│ role        │      │ title           │      │ client_id    │
│ hashed_pwd  │      │ description     │      │ content      │
│ is_active   │      │ status          │      │ materials    │
│ created_at  │      │ priority        │      │ time_spent   │
│ updated_at  │      │ location_*      │      │ server_ver   │
└─────────────┘      │ scheduled_at    │      │ created_at   │
                     │ started_at      │      │ updated_at   │
                     │ completed_at    │      └──────────────┘
                     │ deleted_at      │
                     │ server_version  │      ┌──────────────┐
                     │ created_at      │      │    photos    │
                     │ updated_at      │      │──────────────│
                     └─────────────────┘      │ id (PK)      │
                              │               │ task_id (FK) │
                              └───────────────│ report_id FK)│
                                              │ client_id    │
                     ┌─────────────────┐      │ file_path    │
                     │   sync_logs     │      │ sha256       │
                     │─────────────────│      │ mime_type    │
                     │ id (PK)         │      │ client_ts    │
                     │ user_id (FK)    │      └──────────────┘
                     │ device_id       │
                     │ client_last_sync│
                     │ tasks_received  │
                     │ tasks_sent      │
                     │ status          │
                     └─────────────────┘
```

---

## Key Design Decisions

### 1. `client_id` as idempotency key

Every record that originates on a mobile device carries a `client_id` — a
UUID the device generates once, before the record has ever been sent to the
server.  The sync endpoint performs an **upsert on `client_id`** rather than
`id`, which means:

- A network retry that re-sends the same payload is a no-op.
- The server's auto-generated `id` is stable once assigned.
- The client can reference related records (e.g. `report.task_id`) using the
  server `id` once it receives the first sync response.

### 2. `server_version` for optimistic concurrency

`Task` and `TaskReport` carry an integer `server_version` counter.

```
UPDATE tasks
SET    status = :new_status,
       server_version = server_version + 1
WHERE  id = :id
AND    server_version = :expected_version   -- stale write → 0 rows affected
```

If the `WHERE` clause matches 0 rows, a conflict is raised and resolved by
the configured `SYNC_CONFLICT_STRATEGY`.

### 3. Conflict resolution strategies

| Strategy             | Behaviour                                                     |
|----------------------|---------------------------------------------------------------|
| `latest_timestamp`   | Record with the most recent `updated_at` wins (default).     |
| `server_wins`        | Server state always takes precedence over client changes.     |
| `client_wins`        | Client state always overwrites server state (dangerous — only |
|                      | used in test environments with a single device).              |

The strategy is a runtime config value, not hard-coded, so it can be changed
without a deploy for incident response.

### 4. Soft deletes

Hard deletes break sync.  A deleted row disappears from the server's delta
query (`WHERE updated_at > :last_synced_at`) and the mobile client never
learns the record is gone — it silently persists stale data forever.

`deleted_at` tombstones solve this: the row stays in the delta, the client
sees `deleted_at IS NOT NULL`, and marks its local copy as deleted.

### 5. `SyncLog` as an append-only audit table

Every sync call writes one `SyncLog` row.  This enables:
- Idempotency short-circuit: detect re-sent payloads by `(device_id, client_last_synced_at)`.
- Per-device debugging without log scraping.
- Capacity planning via aggregate queries.

---

## Project Structure

```
field-service-backend/
├── app/
│   ├── main.py                 # FastAPI app factory
│   ├── core/
│   │   ├── config.py           # Pydantic settings
│   │   ├── security.py         # JWT encode/decode, password hashing
│   │   ├── permissions.py      # Role-based access dependency factories
│   │   └── dependencies.py     # get_current_user FastAPI dependency
│   ├── db/
│   │   ├── base.py             # DeclarativeBase with id/created_at/updated_at
│   │   ├── session.py          # Async engine + session factory
│   │   └── migrations/
│   │       ├── env.py          # Alembic async env
│   │       ├── script.py.mako
│   │       └── versions/
│   ├── models/
│   │   ├── __init__.py         # Re-exports all mappers for Alembic
│   │   ├── user.py
│   │   ├── task.py
│   │   ├── task_report.py
│   │   ├── photo.py
│   │   └── sync_log.py
│   ├── schemas/                # Pydantic request/response models (next phase)
│   ├── api/                    # FastAPI routers (next phase)
│   ├── services/               # Business logic layer (next phase)
│   └── tests/
├── docker/
│   ├── entrypoint.sh           # Wait for DB → migrate → start uvicorn
│   ├── wait_for_db.py
│   ├── seed_admin.py           # Create first manager account
│   └── init-db.sql             # Creates field_service_test DB
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
├── .env.example
└── README.md
```

---

## Getting Started

### Option A — Docker (recommended)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

```powershell
cd field-service-backend

# .env already exists — docker-compose reads SECRET_KEY and other settings from it
docker compose up --build
```

That's it. Docker will:

1. Start PostgreSQL 15
2. Wait until the database is healthy
3. Run Alembic migrations automatically
4. Start the API with hot-reload on port **8000**

| URL | Purpose |
|---|---|
| http://localhost:8000/health | Health check |
| http://localhost:8000/docs | Swagger UI |

**Create the first manager account** (required before you can log in):

```powershell
docker compose exec api python docker/seed_admin.py
```

Default credentials:

- Email: `admin@fieldservice.com`
- Password: `Admin1234`

**Useful commands:**

```powershell
docker compose up -d              # Run in background
docker compose logs -f api        # Follow API logs
docker compose down               # Stop containers
docker compose down -v            # Stop and delete database data
docker compose exec api pytest app/tests/ -v   # Run tests inside container
```

**Optional — pgAdmin** (database UI on port 5050):

```powershell
docker compose --profile tools up -d
```

Open http://localhost:5050 — login with `admin@fieldservice.com` / `admin`, then add a server:

- Host: `db`
- Port: `5432`
- Username: `postgres`
- Password: `postgres`

---

### Option B — Native (without Docker)

**Prerequisites:** Python 3.11+, PostgreSQL 15+ installed locally.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env — set DATABASE_URL and SECRET_KEY

createdb field_service
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Test

Against Docker Postgres (port 5432 exposed):

```powershell
pytest app/tests/ -v --cov=app --cov-report=term-missing
```

Or inside the container:

```powershell
docker compose exec api pytest app/tests/ -v
```

---

## Environment Variables

| Variable                  | Required | Default             | Description                              |
|---------------------------|----------|---------------------|------------------------------------------|
| `DATABASE_URL`            | Yes      | —                   | asyncpg connection string                |
| `SECRET_KEY`              | Yes      | —                   | JWT signing key (min 32 bytes)           |
| `APP_ENV`                 | No       | `development`       | Controls docs visibility, debug mode     |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No   | `60`                | JWT access token TTL                     |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | No   | `30`                | JWT refresh token TTL                    |
| `SYNC_CONFLICT_STRATEGY`  | No       | `latest_timestamp`  | `server_wins` / `client_wins` / `latest_timestamp` |
| `SYNC_BATCH_SIZE`         | No       | `500`               | Max records per sync response            |
| `UPLOAD_DIR`              | No       | `/var/field-service/uploads` | Root directory for photo storage |
| `MAX_UPLOAD_SIZE_MB`      | No       | `20`                | Per-file upload limit                    |

---

## Next Steps

- **Web dashboard** — `field-service-web-dashboard` (React manager UI)
- **Mobile app** — `field-service-mobile` (offline-first React Native)
