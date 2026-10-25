# brabos-delivery-api

Delivery ordering API for burger shops and other food businesses. It uses FastAPI with three layers
(API → Service → Repository), PostgreSQL through async SQLAlchemy 2.0, Firebase Authentication and Cloud Messaging,
and SCD Type 4 history tables. Primary keys are UUIDv7. The Dockerfile targets Google Cloud Run. The web app lives in
[`brabos-delivery-ui`](../brabos-delivery-ui).

## Local development

```bash
cp .env.example .env
docker compose up -d db
uv sync
uv run alembic upgrade head
uv run task dev
```

The interactive docs are at http://localhost:8080/docs. Run the tests with `uv run pytest`, which needs the `app_test`
database that compose creates.

## Data model

| Table                         | Purpose                                                                                                                             |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `establishments`              | Owner (`firebase_uid`), `slug`, name, address, phone, CNPJ, colors, auto-accept, delivery fee, minimum order, online payments, logo |
| `opening_hours`               | Weekly hours. `closes_at < opens_at` means the shop closes after midnight                                                           |
| `absences`                    | Emergency closures. No orders are accepted while one is active                                                                      |
| `products`                    | Name, description, ingredients, category, price, half-and-half, doneness, active, position, images, featured                        |
| `orders`                      | Customer name, phone, address, reference point, payment method, change, totals, status, payment status, courier                     |
| `order_items`                 | Product name and price frozen at order time, optional second half, quantity, doneness, notes                                        |
| `order_events`                | Change log of each order: placed, accepted, delivered, cancelled, paid, refunded                                                    |
| `couriers`, `courier_invites` | Couriers who joined through a single-use invite link                                                                                |
| `customers`                   | Profile of a signed-in customer, used for order history and future loyalty programs                                                 |
| `push_devices`                | FCM tokens of owners, couriers and customers                                                                                        |

Every table also has a `<table>_history` copy (SCD Type 4). `GET /api/v1/audit` serves that history.

## Integrations

### Push notifications (FCM)

Set `PUSH_ENABLED=true`. The API reuses the Firebase Admin credentials, so it needs either
`FIREBASE_CREDENTIALS_BASE64` or the default application credentials on Cloud Run. Browsers register their tokens
through `POST /api/v1/push-devices`.

### Product images (Google Cloud Storage or Cloudflare R2)

The bucket stays private. Uploads go straight from the browser to the bucket:

1. The browser asks for a URL with `POST /api/v1/uploads` (`kind`, `content_type`, `size`).
2. It sends the file with `PUT` to that pre-signed URL.
3. It saves the returned `key` in `image_keys` (up to 5) on the product or `logo_key` on the establishment.

Images are read through pre-signed `GET` URLs: every `image_url`, `image_urls` and `logo_url` in the responses (and
`view_url` in the upload response) is signed on the fly. A URL is valid for 1 to 2 hours and is the same for every
request within the same hour, so browsers can cache the image. Clients must store the `key`, never these URLs.

| Provider | Variables                                                                                                                                                                         |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GCS      | `STORAGE_PROVIDER=gcs`, `GCS_BUCKET`. The service account needs `roles/storage.objectAdmin` and `iam.serviceAccounts.signBlob` (`roles/iam.serviceAccountTokenCreator` on itself) |
| R2       | `STORAGE_PROVIDER=r2`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`                                                                                   |

The bucket must allow CORS `PUT` with the `Content-Type` header from the UI origin. For GCS, put this in `cors.json`
and run `gcloud storage buckets update gs://BUCKET --cors-file=cors.json`:

```json
[
  {
    "origin": ["https://your-ui.example"],
    "method": ["PUT"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
```

For R2, add the same rule in the bucket's CORS settings in the Cloudflare dashboard.

### Online payments (Stripe)

1. Set `STRIPE_SECRET_KEY`.
2. Create a webhook endpoint pointing to `https://API/api/v1/payments/webhook` for the events
   `checkout.session.completed` and `checkout.session.expired`.
3. Set its signing secret as `STRIPE_WEBHOOK_SECRET`.
4. Turn on `online_payments_enabled` in the establishment profile.

`PUBLIC_APP_URL` is used to build the pages customers return to after paying. For local testing, forward the
webhook with `stripe listen --forward-to localhost:8080/api/v1/payments/webhook`.

## Deployment

`.github/workflows/deploy.yml` runs lint, tests and `alembic check` on every pull request. Every push to `main` is
deployed to Cloud Run in `southamerica-east1`. Repository settings:

- **Secrets:** `GCP_CREDENTIALS`, `DATABASE_URL`, `REDIS_URL`, `FIREBASE_CREDENTIALS_BASE64`,
  `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.
- **Variables:** `PUBLIC_APP_URL`, `PUSH_ENABLED`, `STORAGE_PROVIDER`, `GCS_BUCKET`, `R2_ACCOUNT_ID`, `R2_BUCKET`, `CORS_ORIGINS`, `CLOUD_RUN_SERVICE`, `GCP_SERVICE_ACCOUNT` and the other optional
  values in the workflow.
