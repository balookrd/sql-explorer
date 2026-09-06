# Backend: SQL Web Explorer

Бэкенд-сервис портала аналитических запросов **SQL Web Explorer (Trino & Hive)**, реализованный на базе **FastAPI (Python 3.12/3.14)**. Сервис предоставляет единый веб-интерфейс к аналитическим движкам Trino и Apache Hive (HiveServer2), обеспечивает аутентификацию (LDAPS / Kerberos SPNEGO), аудит, кэширование метаданных каталога, потоковую передачу результатов через Server-Sent Events (SSE) и защиту от инъекций.

---

## 🏛 Архитектура компонентов бэкенда

```
backend/
├── app/
│   ├── api/                     # REST API контроллеры
│   │   ├── ai.py                # ИИ-ассистент (/api/ai/check, /explain, /optimize, /fix, /status)
│   │   ├── auth.py              # Аутентификация (/api/auth/login, /spnego, /me, /logout)
│   │   ├── catalog.py           # Каталог данных (/api/catalog/catalogs, schemas, tables)
│   │   ├── clusters.py          # Доступные аналитические кластеры (/api/clusters)
│   │   └── queries.py           # Исполнение и стриминг SQL (/api/queries/execute, stream, cancel)
│   ├── core/                    # Ядро сервиса
│   │   ├── acl.py               # Проверка прав (check_cluster_access, check_ui_access)
│   │   ├── audit.py             # Журнал аудита безопасности и SQL-активности
│   │   ├── config.py            # Pydantic Settings, конфигурация AI и загрузка config.yaml
│   │   ├── kerberos.py          # Kerberos SPNEGO аутентификация
│   │   ├── ldap_auth.py         # Безопасная аутентификация через LDAPS
│   │   └── security.py          # PyJWT, HttpOnly Cookie, CSRF-защита, Rate Limiting
│   ├── db/                      # Персистентное хранилище (SQLAlchemy / Alembic)
│   │   ├── models.py            # Модели истории запросов, сохраненных скриптов, сессий
│   │   └── session.py           # Подключение к SQLite или PostgreSQL
│   ├── models/                  # Pydantic-схемы
│   │   ├── auth.py              # UserInfo, TokenResponse, LoginRequest
│   │   ├── catalog.py           # Схемы каталогов, таблиц и колонок
│   │   └── query.py             # QueryRequest, QueryStatus, QueryResult
│   ├── services/                # Движки выполнения запросов и аналитики
│   │   ├── ai_service.py        # Клиент On-premise LLM и эвристический MockSQLAnalyzer
│   │   ├── hive_engine.py       # Клиент HiveServer2 (TCLIService / Thrift / Impyla)
│   │   ├── mock_engine.py       # Демонстрационный движок для dev-режима
│   │   ├── query_manager.py     # Диспетчеризация, отмена и управление состоянием запросов
│   │   └── trino_engine.py      # Клиент Trino DB API с поддержкой impersonation
│   ├── docker-entrypoint.sh     # Инициализация Kerberos (kinit) и запуск uvicorn
│   └── main.py                  # Входная точка FastAPI, CORS, Security Headers, SPA fallback
├── tests/                       # Автоматические тесты (pytest)
│   ├── test_ai_service.py       # Тесты ИИ-линтера, Mock-анализатора и AI API
│   └── test_backend.py          # Тесты безопасности, аутентификации, CSRF, каталога и запросов
└── requirements.txt             # Зависимости Python
```

---

## 🛡️ Безопасность (Security Architecture)

1. **Строгая защита от CSRF**:
   - Валидация источников через `urllib.parse.urlparse` с точным сравнением схемы, хоста и порта со списком разрешенных `server.cors_origins` и `Host` заголовком.
   - Защита Fail-Closed: обязательное отклонение (HTTP 403) для всех мутирующих запросов (`POST`, `PUT`, `DELETE`, `PATCH`) при Cookie-сессии в случае отсутствия или несовпадения источников.
2. **Безопасное хранение и передача токенов**:
   - Токены принимаются исключительно через `Authorization: Bearer <token>` или `HttpOnly`, `SameSite=Lax`, `Secure` Cookie.
   - Полный отказ от передачи токенов в URL Query-параметрах во избежание утечек в логи и заголовки Referer.
3. **Безопасность JWT и отзыва сессий**:
   - Библиотека `PyJWT >= 2.9.0` с защитой от алгоритмических атак.
   - Персистентный отзыв токенов при выходе (`/api/auth/logout`) с записью в базу данных.
4. **Контроль частоты запросов (Rate Limiting)**:
   - Встроенный скользящий Rate Limiter с защитой от IP-спуфинга: заголовок `X-Forwarded-For` учитывается только от доверенных прокси, для прямых подключений используется реальный IP сокета.
5. **Аутентификация Kerberos SPNEGO и LDAP**:
   - Автоматическое обогащение ролевых групп пользователя из каталога LDAP при входе через Kerberos SSO.
   - Строгая проверка TLS-сертификатов (`verify_cert: true`).
   - Изоляция тестовых пользователей: `mock_users` доступны исключительно при `mode: "mock"`.
6. **Безопасность аналитических запросов**:
   - Проброс пользователя (`X-Trino-User` в Trino и `doAs` в Hive) для соблюдения политик доступа Ranger / Sentry.
   - Многоуровневый анализ SQL для безопасного автодобавления `LIMIT` и таймауты сетевых сокетов движков.

---

## 🧪 Запуск тестов

```bash
PYTHONPATH=. pytest
```
