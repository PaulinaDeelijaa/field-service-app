# Field Service App

Offline-first field service platform with three components:

| Folder | Stack | Purpose |
|---|---|---|
| `field-service-backend/` | FastAPI, PostgreSQL, Docker | REST API + sync engine |
| `field-service-web-dashboard/` | React, Vite, Tailwind | Manager dashboard |
| `field-service-mobile/` | Expo, React Native, SQLite | Field worker mobile app |

## Quick start

### Backend
```powershell
cd field-service-backend
docker compose up --build
docker compose exec api python docker/seed_admin.py
```

Default manager: `admin@fieldservice.com` / `Admin1234`

### Web dashboard
```powershell
cd field-service-web-dashboard
npm install
npm run dev
```

### Mobile
```powershell
cd field-service-mobile
npm install
npx expo start --lan
```

Update `field-service-mobile/src/services/api.ts` with your PC's LAN IP.

See each subfolder's README for full documentation.
