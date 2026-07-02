# field-service-web-dashboard

React manager dashboard for the Offline-First Field Service platform.

Built with: React 18, TypeScript, Vite, TailwindCSS, TanStack Query, React Router.

## Features

- **Login** — JWT auth, token stored in localStorage
- **Overview** — live stats (total, pending, in-progress, completed)
- **Tasks** — list, search, filter by status, create, assign to worker, delete, view detail
- **Workers** — register field workers, copy worker ID for task assignment
- **Task Detail** — view full task info, advance status (pending → in_progress → completed)

## Getting Started

### Prerequisites

- Node.js 18+
- Backend running at `http://localhost:8000`

### Install & run

```powershell
cd field-service-web-dashboard
npm install
npm run dev
```

Open http://localhost:5173

Login with:
- Email: `admin@fieldservice.com`
- Password: `Admin1234`

### Build for production

```powershell
npm run build
```

Output in `dist/`.

## Project Structure

```
src/
├── contexts/
│   └── AuthContext.tsx       JWT auth state, login/logout
├── services/
│   ├── api.ts                Axios instance with auth interceptors
│   ├── auth.ts               login, getMe, register
│   ├── tasks.ts              CRUD task endpoints
│   └── users.ts              workers list
├── components/
│   ├── Layout.tsx            Sidebar + outlet wrapper
│   └── ProtectedRoute.tsx    Redirect to /login if unauthenticated
├── pages/
│   ├── LoginPage.tsx
│   ├── OverviewPage.tsx      Stats + recent tasks
│   ├── TasksPage.tsx         Task list + create modal
│   ├── TaskDetailPage.tsx    Task detail + status transitions
│   └── WorkersPage.tsx       Register workers
└── types/
    └── index.ts              Shared TypeScript types
```
