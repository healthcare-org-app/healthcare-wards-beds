# wards-beds-service

wards-beds-service — domain: identity

- **Port:** 9201
- **Language:** Python 3.11 + Flask
- **Database:** `identity` (Postgres, table `wards_beds`)
- **Event bus:** Kafka

## API

| Method    | Path                       |
|-----------|----------------------------|
| GET       | `/api/wards_beds/`          |
| POST      | `/api/wards_beds/`          |
| GET       | `/api/wards_beds/<id>`      |
| PUT/PATCH | `/api/wards_beds/<id>`      |
| DELETE    | `/api/wards_beds/<id>`      |
| GET       | `/health`                  |
| GET       | `/ready`                   |

## Events

**Publishes:** (none)
**Subscribes:** encounter.started, encounter.ended

## HTTP peer dependencies

- `facilities-service`
- `audit-log-service`

## Local dev

```bash
pip install -e ../../libs/py-healthcare-common
pip install -r requirements.txt
cp .env.example .env
(cd ../../infra && docker compose up -d postgres kafka kafka-init)
python -m app.main
```

## Tests

```bash
pytest
```
