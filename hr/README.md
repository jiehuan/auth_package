# Contractor Hub

A dashboard for HR to track contractor SoWs. Upload an Excel/CSV list, see who is expiring or still active in the internal system, edit records inline, and export back to Excel.

Stack: TanStack Start (React 19, SSR), Tailwind v4, shadcn/ui, recharts and SheetJS, built with Nitro's `node-server` preset.
**The pages and the API run in the same Node server**, so there is no separate backend. Data is stored in SQLite through Node's built-in `node:sqlite`, on a persistent volume.

## Project layout

```
src/routes/_app/index.tsx          Dashboard page (KPIs, charts, table, filters)
src/components/contractors/        Upload dialog and edit side panel
src/lib/contractors.ts             Types, status rules, Excel parsing and export (browser)
src/lib/api.ts                     Browser client for /api
src/routes/api/                    API routes (server only)
src/server/db.server.ts            SQLite connection and schema migrations (PRAGMA user_version)
src/server/contractors.server.ts   Data access, validation and import logic
src/server/http.server.ts          JSON responses, write-header check, error handling
```

Files named `*.server.ts` are never included in the browser bundle.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health probe; opens the database and returns the record count |
| GET | `/api/contractors` | All records, sorted by SoW end date |
| POST | `/api/contractors` | Create one record |
| GET / PUT / DELETE | `/api/contractors/:id` | Read, replace or delete one record |
| POST | `/api/contractors/import` | `{ mode: "replace" \| "merge", rows, fields }`, applied in a single transaction |

POST, PUT and DELETE requests must send the `X-Requested-With: fetch` header. The frontend adds it to every request.

### Import rules

- **replace** deletes all records, then inserts the rows from the file.
- **merge** matches existing records by email, case-insensitive.
  - A matched record is updated, but only in the columns that were mapped during upload. Unmapped columns keep their current values.
  - If the new SoW end date is later than the stored one, the renewal count goes up by one.
  - Rows with no match, or with no email, are inserted as new records.

### Status

Status is computed from the dates on every read and is not stored.

| Status | Rule |
|---|---|
| Terminated | Termination date has passed |
| Expired | SoW end date has passed |
| Expiring | SoW ends within 180 days |
| Active | Everything else |

## Local development

```bash
npm ci
npm run dev          # http://localhost:3000; data goes to ./data/contractor-hub.db
```

| Command | Purpose |
|---|---|
| `npm run typecheck` | TypeScript check |
| `npm run lint` | ESLint |
| `npm run build` | Production build into `.output/` |
| `npm start` | Run the production build |

Requires Node 22.13 or later for `node:sqlite`.

When updating dependencies, regenerate `package-lock.json` with **npm 12 or later**. A lockfile written by npm 10 makes `npm ci` fail with EUSAGE.

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `PORT` / `HOST` | `3000` / `localhost` | The image sets `8080` / `0.0.0.0` |
| `DATA_DIR` | `./data` | Directory for the SQLite file; the image sets `/data` |
| `DB_PATH` | `$DATA_DIR/contractor-hub.db` | Override the database file path if needed |

## Deployment

| File | Purpose |
|---|---|
| `harness/build-stage.yaml` | CI stage: `npm ci`, typecheck, build, `cp -r .output dist`, then buildah packages the image |
| `Dockerfile` | Only copies `dist/`; no `RUN` steps, and no npm or `node_modules` at runtime |
| `openshift/deployment.yaml` | ConfigMap, PVC, Deployment, Service and Route (Harness Go template) |
| `openshift/values-dev.yaml` | DEV environment values |

Deployment notes:

- **One replica with the Recreate strategy.** SQLite allows one writer, and a ReadWriteOnce volume cannot be mounted by two pods at once, so a rolling update would hang.
- **The PVC has the `harness.io/skip-versioning` annotation.** Without it, Harness renames the claim on every deploy and the pod starts on a new, empty volume.
- **Probes.**
  - Startup and readiness use `/api/health`, which opens the database, so the pod receives no traffic if the volume is missing.
  - Liveness uses the static `/healthz.json`, so a slow query never restarts the pod.
- **Backups.** All data is one SQLite file on the PVC. Copy it periodically with `oc rsync <pod>:/data ./backup`, or ask the platform team to snapshot the volume.
- **Build the image locally:**
  ```bash
  npm run build && rm -rf dist && cp -r .output dist && docker build -t contractor-hub:dev .
  ```

## Authentication (not yet implemented)

There is no sign-in yet. Anyone who can reach the Route can view and edit all data.

When authentication is added, there are two places to change:

- `src/routes/_app/route.tsx`: add the sign-in check for pages in `beforeLoad`.
- `src/server/http.server.ts`: add identity checks for the API. Every API handler is wrapped by `handle()`, so that is the single place to enforce it.
