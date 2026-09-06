# AGENTS.md — Руководство по экосистеме проектов для AI-агентов и разработчиков

## 1. Связанные проекты экосистемы (Related Projects Ecosystem)

Данный проект входит в состав единой экосистемы инструментов управления и аналитики корпоративной инфраструктуры Big Data (Hadoop / Trino / YARN):

1. **`sql-explorer`** (`/Users/mvmalykh/IdeaProjects/sql-explorer`):
   - Аналитический Web UI и движок исполнения SQL-запросов к Trino, Apache Hive, Hortonworks HDP, ClickHouse.
   - AST-валидация запросов для защиты Read-Only кластеров, умный кэш результатов, мониторинг очередей запросов.
2. **`hdfs-explorer`** (`/Users/mvmalykh/IdeaProjects/hdfs-explorer`):
   - Web UI для взаимодействия с файловой системой HDFS (WebHDFS).
   - Навигация по каталогам, предпросмотр файлов (Parquet, ORC, CSV, Текст), загрузка/скачивание, управление ACL и правами доступа.
3. **`yarn-explorer`** (`/Users/mvmalykh/IdeaProjects/yarn-explorer`):
   - Web UI для визуализации и управления очередями Apache YARN Capacity Scheduler.
   - Редактор весов, лимитов и ресурсов очередей, генерация `capacity-scheduler.xml`, система заявок на изменение (Change Requests) с механизмом Four-Eyes Approval.

---

## 2. Общие ресурсы и архитектурные контракты (Shared Architecture & Contracts)

Хотя код каждого проекта хранится локально и автономно (для независимой сборки Docker-образов без внешних зависимостей), все три проекта **строго следуют единому архитектурному контракту**:

### А. Универсальное хранилище Tri-Storage (`StorageService`)
- **Расположение**: `backend/app/services/storage.py` (экспортирует синглтон `storage_service`; в `hdfs-explorer` модуль `app/core/token_blacklist.py` оставлен как алиас).
- **Поддерживаемые бэкенды**:
  1. **Redis (`redis://...`, `rediss://...`)**:
     - *Rate Limiting*: атомарное скользящее окно через Sorted Set (`ratelimit:{key}`).
     - *Отзыв токенов (Blacklist)*: `SET revoked:{jti} 1 EX {ttl}` со встроенным автоматическим истечением по TTL.
     - *Сущности приложений (`yarn`)*: хранение Change Requests в Hashes (`yarn:cr:{id}`) и ZSet индексах.
  2. **PostgreSQL (`postgresql://...`)**:
     - SQLAlchemy Core с промышленным пулом соединений (`pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`).
  3. **SQLite (`sqlite://...`)**:
     - Локальный движок для разработки с поддержкой `PRAGMA journal_mode=WAL` и режима в памяти (`:memory:`).
- **Переменные окружения подключения**:
  - `STORAGE_URL` или `REDIS_URL` для подключения к Redis.
  - `DATABASE_URL` (или `YARN_DATABASE_URL`) для PostgreSQL / SQLite.

### Б. Подсистема Rate Limiting (`app/core/rate_limiter.py`)
- **Алгоритм**: Sliding Window на базе `StorageService.check_and_record_rate_limit()`.
- **Гранулярность ключа**: `f"{client_ip}:{username}"` — предотвращает DoS и блокировку всех сотрудников офиса за одним корпоративным NAT при подборе пароля одним пользователем.
- **Защита от IP Spoofing (CWE-348 / CWE-290)**:
  - Функция `get_client_ip(request)` и `is_trusted_proxy(host)`.
  - Заголовки `X-Forwarded-For` и `X-Real-IP` считываются **только** если прямой клиентский IP входит в доверенные хосты (`TRUSTED_PROXIES`) или доверенные CIDR-подсети Kubernetes/Nginx (`TRUSTED_CIDRS`).

### В. Серверный отзыв токенов (Token Revocation / Blacklist)
- При вызове `POST /api/v1/auth/logout` токен отзывается на сервере:
  - `storage_service.revoke_token(jti, expires_at)`.
- В middleware/dependency `get_current_user` выполняется обязательная проверка:
  - Если `storage_service.is_token_revoked(jti)` -> `401 Unauthorized` («Токен был отозван»).

### Г. Защита от межсайтовой подделки запросов (CSRF / CWE-352)
- Функция `verify_csrf(request, is_cookie_auth)`:
  - Проверяет `Sec-Fetch-Site: cross-site` (блокирует нелегитимные междоменные вызовы).
  - Проверяет `Origin` и `Referer` по белому списку `CORS_ORIGINS`.
  - Принимает заголовок `X-Requested-With: XMLHttpRequest`.
  - Обязательно применяется на мутирующих методах (`POST /logout`, изменение данных) при аутентификации через сессионные Cookie.

### Д. Структурированный SIEM-аудит безопасности (`app/core/audit.py`)
- Модуль `audit.py` экспортирует функцию:
  ```python
  def audit_log(action: str, username: str, client_ip: str, details: dict = None, status: str = "SUCCESS"): ...
  ```
- Формирует структурированное JSON-событие с таймстампом UTC.
- Записывает логи в stdout приложения и в файл аудита, если задана переменная окружения `AUDIT_LOG_FILE`.

### Е. Единый версионированный стандарт API (`/api/v1/*`)
Все эндпоинты аутентификации во всех трех проектах строго стандартизированы:
- `POST /api/v1/auth/login` — аутентификация (LDAP, Mock, Hybrid) с выдачей JWT и/или сессионной куки.
- `POST /api/v1/auth/logout` — выход из системы, проверка CSRF и серверный отзыв токена.
- `GET  /api/v1/auth/me` — профиль текущего пользователя, системная роль и группы.
- `POST /api/v1/auth/spnego` (или `/negotiate`, `/sso`) — Kerberos SPNEGO SSO аутентификация.

### Ж. Валидация безопасности Production-окружения (`validate_production_security`)
- При отключенном режиме отладки (`server.debug: false` или `SERVER_DEBUG=false`):
  1. Строго запрещен `mode: "mock"` (блокировка запуска с обходом аутентификации).
  2. Запрещены стандартные и короткие (< 32 символов) секретные ключи JWT (`JWT_SECRET_KEY`).
  3. Требуется включенная проверка TLS-сертификатов (`verify_cert: true`).

---

## 3. Правила для AI-агентов (Guidelines for Agents)

При работе с любым из проектов экосистемы необходимо соблюдать следующие правила:
1. **Синхронность изменений в Core-компонентах**:
   - Если вы улучшаете или исправляете безопасность в `rate_limiter.py`, `storage.py`, `security.py`, `audit.py` или `config.py` в одном проекте, **проверьте и обновите аналогичные компоненты в двух других проектах**.
2. **Сохранение Tri-Storage контракта**:
   - Любое персистентное состояние безопасности (лимиты, токены, сессии) обязано поддерживать все 3 бэкенда: **SQLite**, **PostgreSQL** и **Redis**.
3. **Чистота API**:
   - Не возвращать устаревшие неверсионированные префиксы (например `/api/auth`). Все новые маршруты должны использовать версионирование `/api/v1/...`.
4. **Тестирование перед коммитом**:
   - Запускать `pytest` во всех трех репозиториях:
     - `(cd ../sql-explorer && ./backend/venv/bin/pytest backend/tests)`
     - `(cd ../hdfs-explorer && ./backend/venv/bin/pytest backend/tests)`
     - `(cd ../yarn-explorer && ./backend/venv/bin/pytest backend/tests)`
