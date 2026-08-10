# Field Service App

Offline-first field service platform: managers assign work from a web dashboard; field workers complete tasks on mobile, even without connectivity. Data syncs automatically when back online.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Web Dashboard  │────▶│  FastAPI Backend │◀────│   Mobile App    │
│  (React/Vite)   │     │  PostgreSQL      │     │  (Expo/SQLite)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        Manager                  Sync API                  Field Worker
```

| Component | Stack | Role |
|---|---|---|
| `field-service-backend/` | FastAPI, PostgreSQL, Docker | REST API + bidirectional sync |
| `field-service-web-dashboard/` | React, Vite, Tailwind | Manager dashboard |
| `field-service-mobile/` | Expo, SQLite, SecureStore | Offline-first worker app |

## Prerequisites

- **Docker Desktop** (backend + database)
- **Node.js 18+** (web + mobile)
- **Expo Go** on your phone (mobile testing)

---

## 1. Backend

```powershell
cd field-service-backend
copy .env.example .env
docker compose up --build
```

In a second terminal, seed accounts and demo data:

```powershell
docker compose exec api python docker/seed_admin.py
docker compose exec api python docker/seed_demo.py
```

| Account | Email | Password | Role |
|---|---|---|---|
| Manager | `admin@fieldservice.com` | `Admin1234` | manager |
| Demo worker | `worker@fieldservice.com` | `Worker1234` | field_worker |

API: http://localhost:8000/docs

---

## 2. Web Dashboard

```powershell
cd field-service-web-dashboard
npm install
npm run dev
```

Open http://localhost:5173 and log in as manager.

---

## 3. Mobile App

Set your PC's LAN IP in `field-service-mobile/app.json`:

```json
"extra": { "apiUrl": "http://YOUR_LAN_IP:8000" }
```

Or use an environment variable:

```powershell
$env:EXPO_PUBLIC_API_URL="http://YOUR_LAN_IP:8000"
```

Then:

```powershell
cd field-service-mobile
npm install --legacy-peer-deps
npx expo start --lan
```

Scan the QR code with **Expo Go**. Log in as `worker@fieldservice.com` / `Worker1234`.

> Phone and PC must be on the same Wi-Fi. If connection fails, allow ports **8000** and **8081** in Windows Firewall.

---

## Demo Walkthrough

1. **Backend running** — `docker compose up`
2. **Seed data** — `seed_admin.py` + `seed_demo.py`
3. **Dashboard** — log in as manager, view tasks on Overview/Tasks pages
4. **Mobile** — log in as worker, pull to refresh, open a task
5. **Complete work** — start task → submit report with photos → mark complete
6. **Verify** — refresh dashboard task detail → see report text and photos

---

## Key Features

- **Offline-first mobile** — SQLite local store, sync queue, works without network
- **Bidirectional sync** — `POST /sync` with conflict resolution (server-wins / latest-timestamp)
- **Photo pipeline** — metadata via sync, binary upload via multipart
- **Role-based access** — managers create/assign; workers see only their tasks
- **Optimistic concurrency** — `server_version` prevents lost updates

---

## Project Structure

```
field-service-app/
├── field-service-backend/     # FastAPI API + Docker
├── field-service-web-dashboard/ # React manager UI
├── field-service-mobile/        # Expo field worker app
└── README.md
```

See each subfolder's README for detailed documentation.
