# SQL Web Explorer (Trino & Apache Hive)

**SQL Web Explorer** — современный корпоративный веб-портал для интерактивной аналитики и выполнения SQL-запросов к распределенным движкам **Trino** и **Apache Hive (HiveServer2 / Cloudera / Hortonworks)**. Поддерживает мультикластерность, аутентификацию через **LDAPS** и **Kerberos SPNEGO SSO**, сквозную имперсонацию пользователей (**`doAs` / `X-Trino-User`**), разграничение доступа (**ACL**), фоновое исполнение запросов и промышленное развертывание в **Kubernetes (Helm)**.

---

## 📑 Содержание

- [Специализированная документация](#-специализированная-документация)
- [Ключевые возможности](#-ключевые-возможности)
- [Архитектура решения](#-архитектура-решения)
- [Быстрый старт: Демо-стенд в Docker](#-быстрый-старт-демонстрационный-стенд-в-docker)
- [Тестовые учетные записи (LDAP)](#-тестовые-учетные-записи-ldap)
- [Локальная разработка](#-локальная-разработка)
- [Конфигурация (`config.yaml`)](#️-конфигурация-configyaml)
- [Развертывание в Kubernetes (Helm)](#️-развертывание-в-kubernetes-helm)
- [Тестирование](#-тестирование)
- [Структура проекта](#-структура-проекта)
- [Лицензия](#-лицензия)

---

## 📚 Специализированная документация

| Документ | Содержание |
|---|---|
| 🎪 **[DEMO.md](DEMO.md)** | Подробное руководство по керберизированному демо-стенду (Trino, Hive, Metastore, OpenLDAP, MIT KDC) и сценарии проверки |
| ☸️ **[helm/sql-explorer/README.md](helm/sql-explorer/README.md)** | Описание параметров `values.yaml`, сетевых политик, Ingress и инструкция по Helm-деплою в Kubernetes |
| ⚙️ **[backend/README.md](backend/README.md)** | Спецификация REST API, архитектура FastAPI, движки Trino/Hive, безопасность и запуск тестов |
| 🎨 **[frontend/README.md](frontend/README.md)** | Архитектура интерфейса на Svelte 5 (Runes), Monaco Editor, SSE стриминг и сборка |

---

## 🚀 Ключевые возможности

### 1. Мультикластерность и аналитические движки
- **Единая точка входа**: одновременная работа с несколькими независимыми кластерами Trino и Apache Hive (CDP, HDP, Apache) с переключением в реальном времени без перезагрузки интерфейса.
- **Сквозная имперсонация (Impersonation / Proxy User)**:
  - **Trino**: Выполнение запросов от имени реального вошедшего пользователя через заголовок `X-Trino-User`.
  - **Hive (HiveServer2)**: Выполнение запросов с параметром `hive.server2.proxy.user` (`doAs`).
  - Строгое соблюдение политик безопасности **Apache Ranger** и **Trino System Access Control** на уровне хранилища данных.
- **Интерактивный каталог (Schema Explorer)**: древовидный просмотр Каталогов -> Схем -> Таблиц -> Колонок с типами данных и быстрой вставкой имен в редактор.

### 2. Корпоративная безопасность и аудит
- **Kerberos SPNEGO SSO**: бесшовный сквозной вход без ввода пароля по билетам Kerberos из браузера (`Authorization: Negotiate`) с автоматическим обогащением групп пользователя из каталога LDAP (`get_user_info`).
- **LDAPS (Active Directory / OpenLDAP / FreeIPA)**: аутентификация по логину/паролю со строгой проверкой TLS-сертификатов (`verify_cert: true`) и автоматическим получением ролевых групп.
- **Разграничение прав (ACL)**: гранулярные списки доступа к веб-интерфейсу и к каждому кластеру по пользователям и LDAP-группам.
- **Эшелонированная защита (OWASP Top 10)**:
  - Сессионные токены передаются исключительно через заголовок `Authorization: Bearer` или защищенные `HttpOnly`, `SameSite=Lax` Cookie (передача JWT через Query-параметры `?token=` полностью заблокирована во избежание утечек через логи).
  - Строгая защита от CSRF (`verify_csrf`) на базе точного URL-парсинга (`urllib.parse.urlparse`), валидации `Origin` / `Referer` и блокировки запросов при несовпадении или отсутствии источников (Fail-Closed).
  - Скользящий лимитер запросов (Rate Limiting) с защитой от IP-спуфинга (доверяет `X-Forwarded-For` только от доверенных прокси) и заголовком `Retry-After`.
  - Персистентный отзыв токенов при выходе (Logout Blacklist в SQLite / PostgreSQL).
  - Строгая изоляция тестовых аккаунтов (`mock_users` активны исключительно при `auth.mode: "mock"` и заблокированы в `hybrid` / `ldaps_only`).
  - Продвинутая санитизация запросов: многоуровневый анализ SQL для безопасного добавления `LIMIT` (игнорирует комментарии и подзапросы/CTE) и защита сокетов Hive/Trino таймаутами.
  - **Безопасность ИИ (AI Prompt Sanitization & AST Guard)**: автоматическая санитизация входящих промптов от jailbreak/injection инструкций и жесткая Read-Only валидация SQL на уровне AST-дерева (`sqlglot`), блокирующая любые DDL/DML мутации (`DROP`, `DELETE`, `ALTER`, `GRANT`, `TRUNCATE`).
  - Строгий **Content-Security-Policy (CSP)**: директивы `object-src 'none'`, `base-uri 'self'`, `form-action 'self'` и `frame-ancestors 'none'`, исключающие внедрение плагинов и кликджекинг.
  - Защита хранилища: поддержка PostgreSQL для многопользовательской работы и автоматическое ограничение реплик (`replicaCount: 1`) в Helm-манифестах при использовании SQLite.
  - Структурированный аудит безопасности (JSON) всех операций входа и выполнения запросов для интеграции с SIEM/SOC.
  - Запуск Docker-контейнера от непривилегированного пользователя (`appuser`, UID 10001) и Helm-секреты через Kubernetes `Secret`.

### 3. Продвинутый редактор и фоновые очереди
- **Monaco Editor (движок VS Code)**: подсветка синтаксиса Trino/Hive SQL, автодополнение, форматирование и горячие клавиши (`Cmd+Enter` / `Ctrl+Enter`).
- **Выполнение мульти-запросов**: разделение цепочек SQL по `;`, выполнение выделенного фрагмента или запроса под текущей позицией курсора.
- **Стриминг результатов в реальном времени**: передача строк через Server-Sent Events (SSE) с индикацией таймингов и возможностью экстренной отмены (`Stop`).
- **Фоновая очередь задач**: запросы продолжают исполняться на кластере даже при закрытии вкладки браузера.
- **Виртуализированная таблица результатов**: мгновенный просмотр больших выборок с фильтрацией, пагинацией и безопасным экспортом в CSV и JSON.

### 4. Корпоративный ИИ-ассистент и SQL Linter (On-premise LLM)
- **Комплексный линтинг и аудит**: проверка диалектов (Trino vs Hive), детекция антипаттернов производительности (`SELECT *`, отсутствие `LIMIT`, неявные `CROSS JOIN`, отсутствие фильтрации по партициям дат) и деструктивных операций (`DROP`, `TRUNCATE`, `ALTER`).
- **Безопасная генерация (AST Read-Only Guard)**: гарантированный семантический контроль — сгенерированные или исправленные AI запросы проверяются через AST-парсер перед выдачей пользователю.
- **Интеграция с Monaco Editor**: автоматическая подсветка замечаний и ошибок волнистыми линиями прямо в редакторе с подсказками по исправлению при наведении курсора.
- **Пошаговое объяснение запросов (Explain)**: структурированный разбор используемых таблиц, фильтров, CTE и логики работы на естественном языке.
- **Оптимизация в 1 клик (Optimize & Rewrite)**: генерация оптимизированного SQL с быстрым применением в редактор.
- **Автоматическое исправление ошибок (Fix Error)**: анализ текста ошибки движка Trino/Hive и генерация исправленного SQL.
- **Поддержка On-premise и автономного режима**: интеграция с локальными LLM-серверами (Ollama, vLLM, LiteLLM) по OpenAI-совместимому API, а при их отсутствии — автоматический переход на встроенный детерминированный `MockSQLAnalyzer` без GPU.

---

## 🏗 Архитектура решения

```mermaid
flowchart TD
    Browser["Веб-браузер пользователя"]
    Frontend["Frontend UI (Svelte 5 + Monaco Editor SPA)"]
    Backend["Backend Service (FastAPI + SQLAlchemy)"]
    LDAP["OpenLDAP / Active Directory (LDAPS :636)"]
    KDC["Kerberos KDC (Keytab & SPNEGO :88)"]
    Trino["Trino Coordinator (Impersonation X-Trino-User)"]
    Hive["Apache HiveServer2 (Impersonation doAs)"]
    LLM["On-premise LLM (Ollama / vLLM / Mock Analyzer)"]
    DB[("База данных (PostgreSQL / SQLite PVC)")]

    Browser -->|HTTPS / WSS| Frontend
    Frontend -->|REST API + SSE + Monaco Markers| Backend
    Backend -->|1. Проверка логина и групп| LDAP
    Backend -->|2. SPNEGO / kinit сервисный тикет| KDC
    Backend -->|3. SQL + X-Trino-User| Trino
    Backend -->|4. TCLIService + doAs| Hive
    Backend -->|5. Линтинг и оптимизация SQL| LLM
    Backend -->|История и отозванные токены| DB
```

---

## 🐳 Быстрый старт: Демонстрационный стенд в Docker

В репозиторий включен полностью автономный керберизированный демо-стенд, содержащий Trino, Hive 4, PostgreSQL Metastore, OpenLDAP и MIT Kerberos KDC.

### Состав стенда:
| Контейнер | Назначение | Адрес на хосте |
|---|---|---|
| **`sql-demo-explorer`** | Портал SQL Web Explorer (Backend + UI) | **[http://localhost:8002](http://localhost:8002)** |
| **`sql-demo-trino`** | Координатор Trino с каталогами `tpch` и `hive` | [http://localhost:8080](http://localhost:8080) |
| **`sql-demo-hive`** | Apache HiveServer2 с поддержкой Kerberos и `doAs` | `localhost:10000` |
| **`sql-demo-ldap`** | Сервер каталогов OpenLDAP | `localhost:389` |
| **`sql-demo-kdc`** | MIT Kerberos KDC (`COMPANY.LOCAL`) | `localhost:88` |

### Запуск одной командой:
```bash
./demo/start-demo.sh
```
*(или `docker compose -f demo/docker-compose.yaml up -d --build`)*

После запуска веб-интерфейс доступен по адресу: 👉 **[http://localhost:8002](http://localhost:8002)**.  
Подробное руководство со сценариями тестирования доступно в **[DEMO.md](DEMO.md)**.

### Остановка стенда:
```bash
./demo/stop-demo.sh
```

---

## 🔐 Тестовые учетные записи (LDAP)

| Логин | Пароль | Ролевая группа | Назначение и доступ к кластерам |
|---|---|---|---|
| **`analyst_user`** | `password123` | `bi-analysts`, `reporting` | Доступ к Trino и общему Hive; нет доступа к HDP кластеру инженеров |
| **`de_user`** | `password123` | `data-engineers`, `bi-analysts` | Полный доступ к Trino, Hive Core и защищенному Hive HDP |
| **`admin_user`** | `password123` | `data-platform-admins` | Администратор платформы, полный доступ ко всем кластерам и настройкам |

---

## 💻 Локальная разработка

### Требования:
- Python 3.11+
- Node.js 20+ и npm
- Системные библиотеки Kerberos (`libkrb5-dev` в Debian/Ubuntu или Xcode CLI tools в macOS)

### 1. Запуск Backend:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Запуск dev-сервера с автоматической перезагрузкой
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Запуск Frontend:
```bash
cd frontend
npm install
npm run dev
```
Фронтенд запустится на `http://localhost:5173` и будет автоматически проксировать `/api` на бэкенд `localhost:8000`.

### 3. Production сборка единого контейнера:
```bash
docker build -t sql-explorer:latest .
docker run -d -p 8000:8000 -v $(pwd)/config:/app/config sql-explorer:latest
```

---

## ⚙️ Конфигурация (`config.yaml`)

Конфигурация задается через YAML-файл (путь передается через переменную `CONFIG_PATH`):

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  debug: false
  cors_origins: ["http://localhost:8000", "http://localhost:5173"]
  secure_cookies: false

database:
  # SQLite по умолчанию. Для PostgreSQL: "postgresql+asyncpg://user:pass@host:5432/sql_explorer"
  url: "sqlite+aiosqlite:///./data/sql_explorer.db"

auth:
  mode: "hybrid" # hybrid (Kerberos SPNEGO + LDAPS), ldaps_only, kerberos_only, mock
  jwt:
    secret_key: "CHANGE-ME-IN-PRODUCTION-RANDOM-SECRET"
    expire_minutes: 480
  ldap:
    enabled: true
    server_uri: "ldaps://ad.company.local:636"
    use_ssl: true
    bind_dn: "cn=svc_sql_explorer,ou=services,dc=company,dc=local"
    bind_password: "ServicePassword"
    user_base_dn: "ou=users,dc=company,dc=local"
    group_base_dn: "ou=groups,dc=company,dc=local"
  kerberos:
    enabled: true
    keytab_file: "/etc/security/keytabs/sql-explorer.keytab"
    service_principal: "HTTP/sql-explorer.company.local@COMPANY.LOCAL"

clusters:
  - id: "trino-analytics"
    name: "Production Trino Cluster"
    type: "trino"
    host: "trino.company.local"
    port: 8443
    use_ssl: true
    impersonation:
      enabled: true
      method: "x-trino-user"
    acl:
      allowed_groups: ["*"]

  - id: "hive-cdp"
    name: "Cloudera CDP HiveServer2"
    type: "hive"
    host: "hive.company.local"
    port: 10000
    auth:
      type: "kerberos"
      kerberos_service_name: "hive"
    impersonation:
      enabled: true
      method: "doAs"
    acl:
      allowed_groups: ["data-engineers"]

ai:
  enabled: true
  provider: "openai_compatible" # openai_compatible (Ollama / vLLM) или mock (автономный режим)
  base_url: "http://localhost:11434/v1"
  model: "qwen2.5-coder:7b"
  timeout_seconds: 30
```

---

## ☸️ Развертывание в Kubernetes (Helm)

В каталог `helm/sql-explorer` включен готовый Helm-чарт со строгим харденингом безопасности:
- Контейнер от непривилегированного пользователя (`UID 10001`, `readOnlyRootFilesystem`).
- Сетевая изоляция через **NetworkPolicy** (только порты 8000, 53, 88, 636, Trino, Hive).
- Автоматическая инициализация Kerberos-билета (`kinit`) через `docker-entrypoint.sh`.
- PersistentVolumeClaim для сохранения истории запросов и черного списка токенов.

```bash
# Установка чарта
helm upgrade --install sql-explorer ./helm/sql-explorer \
  --namespace analytics \
  --create-namespace \
  -f custom-values.yaml
```

Подробное руководство по параметрам чарта см. в **[helm/sql-explorer/README.md](helm/sql-explorer/README.md)**.

---

## 🧪 Тестирование

Запуск модульных и интеграционных тестов безопасности, API и движков:
```bash
# Запуск через pytest из корня проекта
pytest

# Запуск тестов внутри Docker-контейнера
docker exec sql-demo-explorer pytest
```

Проверка типов и синтаксиса фронтенда:
```bash
cd frontend
npm run check
```

---

## 📁 Структура проекта

```
sql-explorer/
├── backend/                     # Бэкенд FastAPI (см. backend/README.md)
│   ├── app/
│   │   ├── api/                 # REST API роутеры (auth, clusters, catalog, queries)
│   │   ├── core/                # Конфигурация, безопасность, токены, LDAP, Kerberos
│   │   ├── db/                  # Сессии SQLAlchemy, модели истории и сохраненных скриптов
│   │   ├── models/              # Pydantic-схемы данных
│   │   └── services/            # Движки выполнения (TrinoEngine, HiveEngine, QueryManager)
│   ├── tests/                   # Автоматические тесты на pytest
│   ├── docker-entrypoint.sh     # Инициализация Kerberos (kinit) и запуск сервиса
│   ├── requirements.txt         # Зависимости Python
│   └── README.md                # Документация бэкенда и API
├── frontend/                    # Фронтенд Svelte 5 (см. frontend/README.md)
│   ├── src/
│   │   ├── components/          # UI-компоненты (Header, Sidebar, SqlEditor, ResultsGrid, QueueView)
│   │   ├── api/                 # Клиентский HTTP и SSE сервис
│   │   ├── utils/               # Парсер мульти-запросов и форматирование
│   │   ├── App.svelte           # Главный компонент интерфейса
│   │   └── types.ts             # TypeScript интерфейсы
│   ├── package.json             # Зависимости и скрипты сборки
│   ├── vite.config.ts           # Конфигурация Vite и dev-прокси
│   └── README.md                # Документация фронтенда
├── demo/                        # Полный демо-стенд (Docker Compose, Trino, Hive, Metastore, KDC, LDAP)
│   ├── docker-compose.yaml     # Описание сервисов демо-стенда
│   ├── start-demo.sh            # Скрипт быстрого запуска
│   ├── stop-demo.sh             # Скрипт остановки и очистки
│   └── config/                  # Конфигурационные файлы демо-режима
├── helm/sql-explorer/           # Production Helm-чарт для развертывания в Kubernetes
│   ├── Chart.yaml               # Описание и метаданные чарта
│   ├── values.yaml              # Параметры по умолчанию
│   ├── templates/               # Манифесты K8s (Deployment, Service, Ingress, PVC, NetworkPolicy)
│   └── README.md                # Документация чарта и параметров values
├── config/                      # Файлы конфигурации приложения (config.yaml)
├── Dockerfile                   # Multi-stage Dockerfile SQL Explorer
├── docker-compose.yml           # Базовый docker-compose сценарий
├── pytest.ini                   # Конфигурация тестов pytest
├── DEMO.md                      # Подробное руководство по демо-стенду
└── README.md                    # Главная документация проекта
```

---

## 📄 Лицензия

Распространяется под лицензией Apache License 2.0.
