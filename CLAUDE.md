# CLAUDE.md

## Rules for the AI

- Keep this file 100% accurate (update it with any structure/stack/command/convention change); max 100 lines.
- English everywhere (code, identifiers, docs, commits); no code comments/docstrings (strip Alembic's too).
- Every new environment variable goes into `.env.example`, `Settings` and the deploy workflow's jq env file.

## Project

Delivery API (FastAPI, three layers), Postgres, Firebase Auth + FCM, Redis, Cloud Run; UI: `../brabos-delivery-ui`.

- Python 3.14, uv (`package = false`), taskipy; FastAPI, Pydantic v2, firebase-admin, redis, stripe, boto3, GCS
- SQLAlchemy 2.0 async + asyncpg, Alembic; primary keys are UUIDv7 via stdlib `uuid.uuid7`
- Tests: pytest (asyncio auto) + httpx on real Postgres (`app_test`); Firebase, Redis, FCM, storage, Stripe faked

## Domain rules

- Firebase Auth is the only user source. One Firebase user owns at most one establishment (`establishments.firebase_uid`,
  advisory lock on register). Public URL key is `slug` (generated from the name, unique, `me` reserved).
- Establishment: name, address, phone, optional CNPJ (check digits), `primary_color`/`accent_color` (hex, red default,
  theme of the public ordering page), `auto_accept`, `delivery_fee_enabled` + `delivery_fee`, `min_order`,
  `online_payments_enabled` (needs Stripe), `logo_key`, `next_order_number` (locked row → sequential numbers).
- Opening hours: `opening_hours` weekday 0=Monday..6, `opens_at`/`closes_at` (`closes < opens` crosses midnight),
  replaced via `PUT /opening-hours`. Absences (emergency) close the shop while active. `services/common.is_within_hours`.
- Products: name unique per shop ignoring case, `price` `Numeric(10,2)` ↔ `schemas/types.Price`, category, description,
  ingredients, `allows_half`, `asks_doneness`, `active`, `position`, `image_keys` (≤ 5, first = `image_url`; all in
  `image_urls`), `featured` (≤ 3 per shop, else 409). Ordered ones can't be deleted (409): deactivate (hidden, not orderable).
- Orders: only delivery. Status `placed → accepted → delivered`, or `cancelled`. Items snapshot names and
  `unit_price`; half-and-half charges the most expensive half; doneness required iff a half asks for it. Totals =
  subtotal + fee (if enabled). `change_for` only for cash and ≥ total. Closed shop → 409. `auto_accept` accepts on
  placement (system actor). Owner cancels placed/accepted with a reason; customer cancels only while placed.
- Customer device token (`X-Customer-Token`, SHA-256 stored); optional bearer links `customer_uid` (`/customers/me`).
- Couriers: owner creates a single-use 7-day invite (`/courier-invites`, link `PUBLIC_APP_URL/entregador/convite/…`);
  the signed-in courier accepts it; active couriers see accepted orders and mark them delivered.
- Push (FCM): `push_devices` per role (owner/courier/customer). After commit `services/notifications.Notifier` sends:
  new paid/non-online order → owner; accepted/delivered/cancelled → customer; accepted → couriers; customer cancel →
  owner. Invalid tokens are deleted. Off unless `PUSH_ENABLED`.
- Change log: `order_events` (kind, actor owner/customer/courier/system, actor_uid, detail); `GET /order-events`.
  `GET /audit` unions `_history` tables of `services/audit.SCOPED_MODELS` (no token hashes). `GET /reports/sales` (default
  last 30 days): sales exclude cancelled/pending/refunded; halves count 0.5 and split revenue.
- Images (`core/storage.ObjectStorage`, `STORAGE_PROVIDER=none|gcs|r2`): `POST /uploads` presigns a PUT for
  `establishments/{id}/{kind}s/{uuid7}.{ext}`; `*_key` fields must use the own prefix; replaced keys are deleted
  after commit; `api/media.present` fills `*_url` with signed GETs (private bucket, 1-2 h windows). No storage: 503 / 422.
- Payments (`core/payments.PaymentGateway`, Stripe when `STRIPE_SECRET_KEY`): `online` orders are `pending` with a
  `checkout_url`; `POST /payments/webhook` marks paid (then notifies/auto-accepts) or expired (cancels); cancelling a
  paid order refunds. Without Stripe: `online` → 422, webhook → 503.
- Public: `/establishments/{slug}/…` (profile + `is_open`, products, hours, orders, `my-orders`), invite lookup,
  customer push devices, webhook. Owner routes use `require_establishment` (403); others' rows → 404.
- Unregistering purges orders (items first) and every row with `establishment_id`, then the establishment.

## SCD Type 4

- Every entity uses `@versioned` (`app/models/history.py`) creating `<table>_history`: entity columns + `history_id`,
  `operation`, `valid_from`, `valid_to` (NULL = open version), `changed_by` (`session.info["actor"]`, the uid).
- `after_flush` writes history: mutate only through the ORM; columns need explicit types (`test_history.py`).

## Layout

```
app/
  core/          config, database, auth, cache, exceptions, migrations, push, storage, payments (Protocols)
  integrations/  firebase, fcm, redis, storage (+ _gcs, _r2, _views), stripe
  api/           deps, pagination, filters (PeriodDep), media (present), cache, health, v1/endpoints/*
  models/ schemas/ repositories/  establishment, opening_hours, absence, product, order(+items), order_event,
                 courier(+invite), customer, push_device
  services/      establishment, opening_hours, absence, catalog, availability, order, notifications, courier,
                 customer, push, report, audit, upload, common
alembic/         async env.py, versions/ (ruff post-write hooks)
tests/           conftest, fakes (identity, cache, push, storage, payments), helpers, one module per resource
```

## Layer rules

- CORS: `CORS_ORIGINS`. Response cache (`api/cache.py`, off without `REDIS_URL`): v1 GET 200s keyed by token +
  customer token + path + query; writes bump table versions; `is_open` caps TTL to 1 minute (`cache_until`).
- Endpoints parse input, call a service, map to schemas. Owner deps use `AuditedSessionDep`; customer deps
  `CustomerSessionDep` (actor = uid when signed in); public deps `SessionDep`.
- Services own rules, raise `AppError` subclasses (never `HTTPException`) and commit; external calls after commit.
- Repositories only touch the session; never commit. Relationships are `viewonly`, `lazy="raise"`; load aggregates
  with selectinload + `populate_existing` (`order_aggregate_options`).
- External services only via Protocols; tests override their `get_*` deps (`FakeIntegrations` fixture).
- New entity: model + `@versioned` → `models/__init__` → schema → repo → service → deps → endpoint → migration → tests

## Commands

```bash
docker compose up -d db          # + redis, with REDIS_URL=redis://localhost:6379/0 in .env
uv sync && uv run alembic upgrade head && uv run task dev
uv run pytest
uv run ruff check . && uv run ruff format .
uv run alembic revision --autogenerate -m "message" && uv run alembic check
```

## Deployment

- GitHub Actions: PRs run lint + tests + `alembic check`; pushes to `main` build → Artifact Registry → deploy → smoke
  test. The app creates the database if missing and migrates on startup. Auth via SA key secret `GCP_CREDENTIALS`;
  secrets `DATABASE_URL`, `REDIS_URL`, `FIREBASE_CREDENTIALS_BASE64`, `R2_*` keys, `STRIPE_*`; vars for the rest.
- `DATABASE_URL` accepts provider URLs (normalized for asyncpg). `Dockerfile`: multi-stage uv, slim, non-root, `$PORT`.
