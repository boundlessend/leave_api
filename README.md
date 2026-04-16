# leave requests api

## что внутри

- fastapi api для заявок на отпуск
- jwt access token и refresh token
- хранение access и refresh токенов в redis с ttl
- logout завершает текущую сессию целиком и после него refresh больше не работает
- postgresql + sqlalchemy + alembic
- uuid для `user.id` и `leave_request.id`
- время заявок и обработки хранится в таймзоне `europe/moscow`
- pytest для базовых сценариев
- dockerfile, docker compose и makefile

## структура

```text
app/
  api/
  core/
  db/
  schemas/
  services/
alembic/
tests/
```

## быстрый старт через docker compose

```bash
cp .env.example .env
make up
docker compose exec app python -m app.seed
```

сервис будет доступен на `http://localhost:8000`

`docker-compose` сам переопределяет `database_url` и `redis_url` на хосты `db` и `redis`, поэтому `.env.example` можно использовать и для локального запуска, и для compose

## запуск локально

для локального запуска `.env.example` уже содержит `localhost` для postgresql и redis

вариант 1: поднимать postgresql и redis локально вне проекта

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

вариант 2: поднять только инфраструктуру через docker и запустить fastapi локально

```bash
cp .env.example .env
docker compose up -d db redis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

## полезные команды

```bash
make install
make migrate
make seed
make test
make down
docker compose exec app python -m app.seed
```

## demo пользователи

после `python -m app.seed` создаются

- admin `admin@example.com` / `admin123`
- user `user@example.com` / `user123`

## основные ручки

### auth

- `POST /api/auth/jwt/login`
- `POST /api/auth/jwt/refresh`
- `POST /api/auth/logout`
- `GET /api/auth/users/me`

### leave requests

- `POST /api/leave-requests`
- `GET /api/leave-requests?status=pending`
- `PATCH /api/leave-requests/{request_id}/approve`
- `PATCH /api/leave-requests/{request_id}/reject`
- `GET /api/admin/leave-requests?status=approved`

`request_id` и `user_id` возвращаются как uuid строки

## пример login

```bash
curl -X POST http://localhost:8000/api/auth/jwt/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

## пример me

```bash
curl http://localhost:8000/api/auth/users/me \
  -H 'Authorization: Bearer <access_token>'
```

## пример создания заявки

```bash
curl -X POST http://localhost:8000/api/leave-requests \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <access_token>' \
  -d '{"start_date":"2026-05-10","end_date":"2026-05-12","reason":"семейные дела"}'
```

## пример отклонения

```bash
curl -X PATCH http://localhost:8000/api/leave-requests/<request_uuid>/reject \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <access_token>' \
  -d '{"manager_comment":"пересечение с критичным релизом"}'
```

## модель доступа

- обычный пользователь видит только свой профиль и свои заявки
- обычный пользователь не может смотреть все заявки и не может менять статус
- admin видит все заявки
- admin может согласовать или отклонить только pending заявку
- повторная обработка approved и rejected заявки запрещена

## login flow

1. пользователь отправляет `email/password` на `POST /api/auth/jwt/login`
2. сервер проверяет пароль через bcrypt
3. сервер создает `session_id` и выпускает `access token` и `refresh token`
4. оба токена и данные текущей сессии сохраняются в redis с ttl
5. защищенные ручки принимают `Authorization: Bearer <access_token>`
6. сервер декодирует jwt, проверяет тип токена и актуальность `session_id` и `jti` в redis
7. `POST /api/auth/jwt/refresh` инвалидирует предыдущую пару токенов в рамках текущей сессии и выдает новую пару
8. `POST /api/auth/logout` завершает текущую сессию и удаляет access token, refresh token и session key из redis

## улучшенный error contract

все прикладные ошибки возвращаются в одном формате

```json
{
  "error": {
    "code": "forbidden",
    "message": "недостаточно прав",
    "details": null
  }
}
```

## ручная проверка

1. залогиниться под user и получить пару токенов
2. вызвать `GET /api/auth/users/me` с access token
3. создать заявку под user
4. получить свои заявки с фильтром и без фильтра
5. вызвать `POST /api/auth/logout` и убедиться, что старые access и refresh токены больше не работают
6. залогиниться под admin и согласовать заявку
7. попробовать повторно отклонить уже закрытую заявку и получить `409`

## тесты

покрыты сценарии

- login/me
- invalid access token
- refresh rotates tokens
- logout invalidates current session access token
- logout invalidates refresh token of current session
- owner sees only own requests
- admin sees all requests
- user cannot approve request
- request not found
- invalid date range
- closed request cannot be approved twice
- overlapping requests are rejected

## миграции

создание новой миграции

```bash
make makemigrations m=add_new_field
```

применение миграций

```bash
make migrate
```
