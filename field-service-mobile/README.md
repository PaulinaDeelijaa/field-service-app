# field-service-mobile

Offline-first React Native (Expo) app for field workers.  
Built with **Expo Router**, **expo-sqlite**, and **expo-secure-store**.

---

## Features

| Feature | Details |
|---|---|
| **Offline-first** | All data is stored locally in SQLite. The app is fully usable without a network connection. |
| **Background sync** | Changes queue as `pending_sync` and are pushed to the server on every pull-to-refresh or app focus. |
| **Conflict handling** | Server-wins strategy: if the server returns a newer version of a record the local copy is overwritten. |
| **Secure storage** | JWT tokens are stored in the device keychain/keystore via `expo-secure-store`. |
| **Camera + gallery** | Field workers can attach photos to reports from the camera or photo library. |

---

## Project Structure

```
field-service-mobile/
├── app/                        # expo-router screens
│   ├── _layout.tsx             # root layout – DB init, AuthProvider
│   ├── index.tsx               # redirect to /login or /(app)/tasks
│   ├── login.tsx               # login screen
│   └── (app)/
│       ├── _layout.tsx         # protected layout
│       ├── tasks.tsx           # task list
│       └── task/
│           ├── [clientId].tsx  # task detail
│           └── [clientId]/
│               └── report.tsx  # submit report
├── src/
│   ├── types/index.ts          # shared TypeScript types
│   ├── db/
│   │   ├── database.ts         # SQLite init + schema
│   │   ├── taskRepository.ts   # task CRUD
│   │   ├── reportRepository.ts # report CRUD
│   │   └── syncWatermark.ts    # last-synced-at + device ID
│   ├── services/
│   │   ├── api.ts              # axios instance + auth interceptors
│   │   ├── authService.ts      # login / logout / restore session
│   │   ├── storage.ts          # secure token storage
│   │   └── syncService.ts      # bidirectional sync engine
│   ├── hooks/
│   │   └── useSync.ts          # React hook wrapping syncService
│   ├── contexts/
│   │   └── AuthContext.tsx     # current user + login/logout
│   └── components/
│       ├── StatusBadge.tsx     # task status + sync state chips
│       └── PriorityIndicator.tsx
├── app.json
├── package.json
└── tsconfig.json
```

---

## Prerequisites

- **Node.js 18+**
- **Expo CLI**: `npm install -g expo-cli` (or use `npx expo`)
- **Expo Go** app on your Android/iOS device, **or** an emulator

---

## Getting Started

### 1. Install dependencies

```powershell
cd field-service-mobile
npm install
```

### 2. Configure the backend URL

Open `src/services/api.ts` and set `API_BASE_URL` to your backend's LAN IP address:

```ts
export const API_BASE_URL = "http://192.168.1.XXX:8000";
```

> The backend must be reachable from the device/emulator. Run `ipconfig` in PowerShell
> to find your machine's local IP and make sure the Docker backend port `8000` is exposed.

### 3. Start the dev server

```powershell
npx expo start
```

Scan the QR code with **Expo Go** (Android) or the Camera app (iOS).

---

## Offline Sync Design

```
Device                             Server
  |                                  |
  | -- POST /sync -----------------> |
  |    {                             |
  |      last_synced_at,             |
  |      tasks: [pending_sync…],     |
  |      reports: [pending_sync…]    |
  |    }                             |
  |                                  |
  | <-- SyncResponse --------------- |
  |    {                             |
  |      server_timestamp,           |
  |      tasks: [delta since ts],    |
  |      conflicts: […]              |
  |    }                             |
```

- Every entity has a `client_id` (device UUID) and a `server_version` counter.
- New records created offline have `id = ""` — the server assigns the real UUID on first sync.
- The `sync_watermark` table stores `last_synced_at` so only deltas are fetched each sync.
- `sync_state` transitions: `pending_sync` → `synced` (or `conflict`).

---

## Building for Production

```powershell
# Android APK
npx expo build:android

# iOS (requires macOS + Xcode)
npx expo build:ios
```

Or use [EAS Build](https://docs.expo.dev/build/introduction/) for cloud builds:

```powershell
npm install -g eas-cli
eas build --platform android
```
