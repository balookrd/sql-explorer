# Backend: SQL Web Explorer

Бэкенд-сервис портала аналитических запросов **SQL Web Explorer (Trino & Hive)**, реализованный на базе **FastAPI (Python 3.12/3.14)**. Сервис предоставляет единый веб-интерфейс к аналитическим движкам Trino и Apache Hive (HiveServer2), обеспечивает аутентификацию (LDAPS / Kerberos SPNEGO), аудит, кэширование метаданных каталога, потоковую передачу результатов через Server-Sent Events (SSE) и защиту от инъекций.

---

## 🏛 Архитектура компонентов бэкенда

```
backend/
├── app/
│   ├── api/                     # REST API контроллеры
│   │   ├── auth.py              # Аутентификация (/api/auth/login, /spnego, /me, /logout)
│   │   ├── catalog.py           # Каталог данных (/api/catalog/catalogs, schemas, tables)
│   │   ├── clusters.py          # Доступные аналитические кластеры (/api/clusters)
│   │   └── queries.py           # Исполнение и стриминг SQL (/api/queries/execute, stream, cancel)
│   ├── core/                    # Ядро сервиса
│   │   ├── acl.py               # Проверка прав (check_cluster_access, check_ui_access)
│   │   ├── audit.py             # Журнал аудита безопасности и SQL-активности
│   │   ├── config.py            # Pydantic Settings, загрузка config.yaml
│   │   ├── kerberos_auth.py     # Kerberos SPNEGO аутентификация
│   │   ├── ldap_auth.py         # Безопасная аутентификация через LDAPS
│   │   └── security.py          # PyJWT, HttpOnly Cookie, CSRF-защита, Rate Limiting
│   ├── db/                      # Персистентное хранилище (SQLAlchemy / Alembic)
│   │   ├── models.py            # Модели истории запросов, сохраненных скриптов, сессий
│   │   └── session.py           # Подключение к SQLite или PostgreSQL
│   ├── models/                  # Pydantic-схемы
│   │   ├── auth.py              # UserInfo, TokenResponse, LoginRequest
│   │   ├── catalog.py           # Схемы каталогов, таблиц и колонок
│   │   └── query.py             # QueryRequest, QueryStatus, QueryResult
│   ├── services/                # Движки выполнения запросов
│   │   ├── hive_engine.py       # Клиент HiveServer2 (TCLIService / Thrift / Impyla)
│   │   ├── mock_engine.py       # Демонстрационный движок для dev-режима
│   │   ├── query_manager.py     # Диспетчеризация, отмена и управление состоянием запросов
│   │   └── trino_engine.py      # Клиент Trino DB API с поддержкой impersonation
│   ├── docker-entrypoint.sh     # Инициализация Kerberos (kinit) и запуск uvicorn
│   └── main.py                  # Входная точка FastAPI, CORS, Security Headers, SPA fallback
├── tests/                       # Автоматические тесты (pytest)
│   └── test_backend.py          # Тесты безопасности, аутентификации, CSRF, каталога и запросов
└── requirements.txt             # Зависимости Python
```

---

## 🛡️ Безопасность (Security Architecture)

1. **Защита от CSRF**:
   - Автоматическая валидация `Sec-Fetch-Site`, `Origin`, `Referer` и заголовка `X-Requested-With: XMLHttpRequest` для всех мутирующих HTTP-запросов (`POST`, `PUT`, `DELETE`).
2. **Безопасное хранение токенов**:
   - Поддержка `HttpOnly`, `SameSite=Lax`, `Secure` Cookie сессий без риска кражи токена через XSS.
3. **Безопасность JWT**:
   - Использование современной библиотеки `PyJWT >= 2.9.0`.
   - Fail-fast проверка слабых дефолтных ключей при запуске в боевых режимах.
4. **Контроль частоты запросов (Rate Limiting)**:
   - Встроенный скользящий Rate Limiter для эндпоинта аутентификации `/api/auth/login` с заголовком `Retry-After`.
5. **Безопасность аналитических запросов**:
   - Проброс пользователя (`X-Trino-User` в Trino и `doAs` в Hive) для соблюдения политик доступа Ranger / Sentry.

---

## 🧪 Запуск тестов

```bash
PYTHONPATH=. pytest
```
