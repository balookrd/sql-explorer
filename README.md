# SQL Web Explorer (Trino & Apache Hive / Hortonworks / Cloudera)

Современный корпоративный Web-интерфейс для выполнения SQL-запросов к распределенным аналитическим движкам **Trino** и **Apache Hive (HiveServer2)** с поддержкой мультикластерности, аутентификации через **LDAPS** и **Kerberos SPNEGO SSO**, сквозной **имперсонации (impersonation / doAs)**, гибкой ролевой модели **ACL** и деплоя в **Kubernetes (Helm)**.

---

## Ключевые возможности

- **Мультикластерность**: Поддержка нескольких независимых кластеров Trino и Hive (Hortonworks HDP, Cloudera CDP, чистый Apache Hive) с мгновенным переключением в UI.
- **Enterprise Security & SIEM Audit**:
  - **Kerberos SPNEGO SSO**: Бесшовный вход без ввода пароля через тикеты Kerberos в браузере.
  - **LDAPS (Active Directory / OpenLDAP / FreeIPA)**: Защищенный вход по логину/паролю с автоматическим получением групп пользователя (`memberOf` и рекурсивно).
  - **Гибкий ACL**: Ограничение доступа к Web-UI и к конкретным кластерам по списку пользователей и/или списку LDAP-групп.
  - **Персистентный отзыв токенов (High Availability)**: Двухуровневый черный список токенов в БД (SQLite / PostgreSQL) с автоочисткой и моментальной инвалидацией во всех репликах K8s.
  - **Защита от XSS и CSP**: Полный отказ от `localStorage` для JWT (Zero LocalStorage) + изолирующий заголовок `Content-Security-Policy`.
  - **Аудит безопасности для SIEM/SOC**: Структурированные JSON-логи событий аутентификации, запросов и попыток несанкционированного доступа.
- **Сквозная имперсонация (Impersonation / Proxy User)**:
  - **Trino**: Выполнение запросов от имени реального пользователя через заголовок `X-Trino-User`.
  - **Hive (HiveServer2)**: Выполнение запросов с параметром `hive.server2.proxy.user` (doAs).
  - Обеспечивает строгое соблюдение политик безопасности **Apache Ranger** и **Trino System Access Control** на уровне хранилища данных.
- **Современный Web-UI (Svelte 5 + TypeScript + Tailwind CSS)**:
  - **Monaco Editor** (движок VS Code) со светлой темой, диалектами SQL, подсветкой синтаксиса Trino/Hive, шорткатами `Cmd+Enter` / `Ctrl+Enter`.
  - **Мульти-запросы**: Выполнение нескольких запросов на одной странице, запуск выделенного фрагмента текста или запроса под текущей позицией курсора.
  - **Дерево схемы данных (Schema Explorer)**: Интерактивный просмотр Каталогов -> Схем -> Таблиц -> Колонок и типов данных.
  - **Стриминг результатов**: Server-Sent Events (SSE) в реальном времени с отображением прогресса и таймингов.
  - **Отмена запросов**: Кнопка «Stop» немедленно посылает сигнал отмены в координатор Trino/Hive и освобождает кластерные ресурсы.
  - **Виртуализированная таблица**: Фильтрация, пагинация, мгновенный экспорт в **CSV** и **JSON** с защитой от CSV Formula Injection.
  - **Фоновая очередь задач**: Запросы продолжают исполняться на сервере даже при закрытии вкладки; просмотр статусов и загрузка результатов из архива.
  - **Desktop Notifications**: Браузерные уведомления при завершении длительных запросов.
- **Готовность к Production и Kubernetes**:
  - Готовый **Helm Chart** (`helm/sql-explorer`) для развертывания в Kubernetes с поддержкой Ingress, cert-manager, ConfigMap, Secrets и keytab.
  - Поддержка **PostgreSQL** и **SQLite** (с PersistentVolumeClaim) для хранения истории, сохраненных запросов и реестра отозванных токенов.

---

## Архитектура проекта

```
sql-explorer/
├── backend/                  # Python FastAPI Backend
│   ├── app/
│   │   ├── api/              # REST & SSE эндпоинты (auth, clusters, catalog, queries)
│   │   ├── core/             # Безопасность: LDAPS (ldap3), Kerberos (spnego), ACL, JWT, Audit Logging
│   │   ├── db/               # SQLAlchemy сессии (SQLite & PostgreSQL)
│   │   ├── models/           # Модели данных: QueryHistory, SavedQuery, RevokedToken
│   │   ├── services/         # Движки: TrinoEngine, HiveEngine, MockEngine, QueryManager
│   │   ├── config.py         # Загрузка конфигурации (YAML + 12-factor ENV vars)
│   │   └── main.py           # FastAPI app + healthz + раздача SPA статики
│   ├── tests/                # Интеграционные тесты API и ACL
│   ├── docker-entrypoint.sh  # Инициализация Kerberos (kinit) и запуск
│   └── requirements.txt      # Зависимости Python
│
├── frontend/                 # Svelte 5 SPA (Vite + TypeScript + Tailwind CSS)
│   ├── src/
│   │   ├── api/              # Клиент API и обработка SSE потоков
│   │   ├── components/       # Header, Sidebar, SqlEditor, QueryToolbar, ResultsGrid, QueueView, LoginModal
│   │   ├── utils/            # Парсер мульти-запросов (sqlSplitter.ts)
│   │   ├── types.ts          # Модели TypeScript
│   │   └── App.svelte        # Главный компонент (Svelte 5 Runes)
│   └── package.json
│
├── helm/
│   └── sql-explorer/         # Production Helm-чарт для Kubernetes
│       ├── Chart.yaml        # Метаданные чарта
│       ├── values.yaml       # Параметры развертывания по умолчанию
│       ├── templates/        # Шаблоны Deployment, Service, Ingress, ConfigMap, Secret, PVC
│       └── README.md         # Руководство по установке чарта
│
├── demo/                     # Автономный демонстрационный стенд (Docker Compose)
│   ├── docker-compose.yaml     # Trino, Hive, Metastore, OpenLDAP, MIT KDC, SQL Explorer
│   ├── start-demo.sh         # Скрипт запуска стенда
│   └── stop-demo.sh          # Скрипт остановки стенда
│
├── config/
│   └── config.yaml           # Конфигурация кластеров, LDAP, Kerberos и ACL
├── Dockerfile                # Multi-stage Docker образ (Node.js -> Python)
└── docker-compose.yml        # Базовый Docker Compose сценарий
```

---

## Настройка корпоративной безопасности

### 1. Настройка Kerberos SPNEGO SSO
1. Создайте сервисный principal для Web-сервера в Active Directory / MIT KDC:
   ```bash
   ktpass -princ HTTP/sql-explorer.company.local@COMPANY.LOCAL \
          -mapuser svc_sql_explorer \
          -pass SecretPass \
          -crypto AES256-SHA1 \
          -ptype KRB5_NT_PRINCIPAL \
          -out /etc/security/keytabs/sql-explorer.keytab
   ```
2. В `config/config.yaml` укажите путь к `keytab_file` и имя `service_principal`.
3. На стороне клиентов настройте браузер на доверие домену:
   - **Chrome / Edge**: флаг `--auth-server-whitelist="*.company.local"` (или через GPO `AuthServerWhitelist`).
   - **Firefox**: параметр `network.negotiate-auth.trusted-uris` = `.company.local`.

### 2. Настройка LDAPS
В `config/config.yaml` укажите параметры подключения к Active Directory / OpenLDAP:
```yaml
auth:
  mode: "hybrid" # hybrid (Kerberos + LDAPS), ldaps_only, kerberos_only, mock
  ldap:
    enabled: true
    server_uri: "ldaps://ad.company.local:636"
    use_ssl: true
    bind_dn: "cn=svc_sql_explorer,ou=services,dc=company,dc=local"
    bind_password: "ServicePassword"
    user_base_dn: "ou=users,dc=company,dc=local"
    user_filter: "(&(objectClass=user)(sAMAccountName={username}))"
    group_base_dn: "ou=groups,dc=company,dc=local"
    ca_cert_file: "/etc/ssl/certs/company-ca.crt"
```

### 3. Настройка имперсонации в Trino
Сервисный аккаунт приложения авторизуется на координаторе Trino, а запрос исполняется от имени пользователя через заголовок `X-Trino-User`.

В файле конфигурации Trino `etc/access-control.properties`:
```properties
access-control.name=file
security.config-file=etc/rules.json
```
В файле `etc/rules.json` разрешите сервисному пользователю `svc_sql_explorer` имперсонировать пользователей:
```json
{
  "impersonation": [
    {
      "original_user": "svc_sql_explorer",
      "new_user": ".*",
      "allow": true
    }
  ]
}
```

### 4. Настройка имперсонации в Apache Hive & Hortonworks / Cloudera
В конфигурации Hadoop / Hive (`core-site.xml`) на кластере добавьте права Proxy User для сервисного аккаунта:
```xml
<property>
  <name>hadoop.proxyuser.hive.hosts</name>
  <value>*</value>
</property>
<property>
  <name>hadoop.proxyuser.hive.groups</name>
  <value>*</value>
</property>
```
Backend передает параметр `hive.server2.proxy.user: <username>` при открытии сессии HiveServer2.

---

## Комплексная безопасность (Hardening & Security Controls)

В архитектуру приложения заложены механизмы защиты от распространенных уязвимостей (согласно рекомендациям OWASP Top 10):

1. **Защита от инъекций (Injection Defense)**:
   - **SQL Injection**: На уровне API каталога метаданных ([catalog.py](file:///Users/mvmalykh/IdeaProjects/sql-explorer/backend/app/api/catalog.py)) параметры `catalog`, `schema` и `table` строго валидируются регулярным выражением (`^[a-zA-Z0-9_\-]+$`), а на уровне движков [trino_engine.py](file:///Users/mvmalykh/IdeaProjects/sql-explorer/backend/app/services/trino_engine.py) и [hive_engine.py](file:///Users/mvmalykh/IdeaProjects/sql-explorer/backend/app/services/hive_engine.py) безопасно экранируются и квотируются.
   - **LDAP Injection**: Все пользовательские входные данные экранируются утилитой `escape_filter_chars` библиотеки `ldap3` перед формированием поисковых фильтров `user_filter` и `group_filter`.
   - **CSV / Formula Injection**: При экспорте данных в CSV любые значения ячеек, начинающиеся с формульных спецсимволов (`=`, `+`, `-`, `@`, `\t`, `\r`), автоматически экранируются префиксом `'`, что предотвращает исполнение вредоносных формул и команд DDE в табличных редакторах (Excel, Calc).

2. **Контроль доступа на уровне объектов (BOLA / IDOR Prevention)**:
   - Доступ к стримам выполнения запросов (`GET /api/queries/{query_id}/stream`) и к кэшированным результатам строго разграничен: подписаться на события и просмотреть данные может только владелец запроса (`username`) либо системный администратор (`admin_groups`).

3. **Сетевая безопасность, сессии и токены**:
   - **Защитные HTTP-заголовки (Security Headers & Content-Security-Policy Middleware)**: Сервер автоматически проставляет во все HTTP-ответы заголовки `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy` (с изолированными источниками для Monaco Editor и Web Workers) и `Strict-Transport-Security: max-age=31536000; includeSubDomains` (при HTTPS).
   - **Встроенный Rate Limiting аутентификации**: Эндпоинт `/api/auth/login` защищен скользящим лимитером (до 5 неудачных попыток в минуту на связку `IP:username`). При превышении лимита возвращается `429 Too Many Requests`, предотвращая перебор паролей и блокировку учетных записей в Active Directory.
   - **Отзыв токенов при Logout (Persistent Token Blacklist в SQLite/PostgreSQL)**: При вызове `/api/auth/logout` хэш текущего JWT токена (SHA-256) сохраняется в персистентную базу данных (SQLite или PostgreSQL в зависимости от настроек) и кэшируется в памяти (L1-кэш). Это гарантирует мгновенную инвалидацию токена со статусом `401 Unauthorized` во всех репликах сервиса в Kubernetes при горизонтальном масштабировании. Устаревшие записи автоматически удаляются из базы данных по истечении срока жизни токена (`exp`).
   - **Криптографическая уникальность токенов (RFC 7519)**: Каждый создаваемый JWT снабжается уникальным идентификатором `jti` (`UUIDv4`) и временем выпуска `iat`, исключая коллизии токенов, сгенерированных в одну секунду, и защищая от Replay-атак.
   - **Защита от XSS-кражи токенов (Zero LocalStorage)**: Фронтенд не сохраняет JWT-токен в `localStorage`. Основная сессия поддерживается через безопасные `HttpOnly` Cookie (`credentials: 'include'`), а для заголовков используется только оперативная память JS текущей вкладки.
   - **Устранение утечки токенов в URL**: Потоки Server-Sent Events (`/queries/{query_id}/stream` и `/queries/notifications/stream`) используют сессионные `HttpOnly` Cookie (`withCredentials: true`), исключая передачу токена через query-параметры `?token=...` и его попадание в access-логи прокси-серверов.
   - **CORS**: Заголовок `Access-Control-Allow-Origin` ограничен белым списком доменов из `settings.server.cors_origins` (или переменной `CORS_ORIGINS`).
   - **Path Traversal Protection**: При раздаче статических файлов SPA путь проверяется через `os.path.commonpath`, исключая доступ к файлам вне директории сборки.
   - **TLS/SSL Validation**: Проверка сертификатов координатора Trino и LDAPS-сервера включена по умолчанию (`ssl.CERT_REQUIRED`). Для тестовых сред предусмотрен явный флаг `allow_insecure_ssl: true`.
   - **Сессионные Cookies**: Поддержка флага `secure=True` (через параметр `server.secure_cookies` или env `SECURE_COOKIES=true`) и `HttpOnly` для защиты от перехвата и XSS.
   - **Fail-fast Startup Check**: При запуске в боевых режимах (`hybrid`, `ldaps_only`, `kerberos_only`) сервис проверяет секрет `jwt.secret_key` и аварийно завершает работу, если обнаружен дефолтный ключ.

4. **Контейнерная безопасность (Non-root user)**:
   - Dockerfile и Helm-чарт сконфигурированы для запуска процесса от имени непривилегированного пользователя `appuser` (`UID: 10001`, `GID: 10001`).

5. **Корпоративный аудит безопасности (SIEM/SOC Audit Logging)**:
   - В ядро системы встроен выделенный логгер `security.audit` ([audit.py](file:///Users/mvmalykh/IdeaProjects/sql-explorer/backend/app/core/audit.py)), выводящий события информационной безопасности в структурированном формате JSON:
     - `AUTH_LOGIN_SUCCESS` — успешный вход (пользователь, IP, метод auth: LDAP/Kerberos/Mock, группы).
     - `AUTH_LOGIN_FAILED` — неудачная попытка входа с указанием причины.
     - `AUTH_RATE_LIMITED` — срабатывание лимитера перебора паролей.
     - `AUTH_LOGOUT` — выход пользователя и отзыв токена.
     - `QUERY_EXECUTED` — отправка SQL-запроса на исполнение (query_id, кластер, сниппет SQL, IP).
     - `QUERY_CANCELLED` — отмена или удаление запроса из очереди.
     - `ACCESS_DENIED_ACL` — попытка выполнения запроса к запрещенному кластеру.
     - `ACCESS_DENIED_BOLA` — попытка несанкционированного перехвата чужого SSE-стрима или просмотра чужого кэша результатов.
   - Логи готовы к прямой отправке в OpenSearch, ELK, Splunk, Kafka или Vector.

### Рекомендации по безопасности для Production (Production Checklist)

Перед развертыванием приложения в промышленную эксплуатацию выполните следующие шаги:

- [ ] **Смена криптографических ключей**: Обязательно задайте уникальный криптостойкий ключ `JWT_SECRET_KEY` через переменные окружения или Kubernetes Secret:
  ```bash
  export JWT_SECRET_KEY="$(openssl rand -hex 32)"
  ```
- [ ] **Отключение Mock режима**: Установите `auth.mode: "hybrid"`, `"ldaps_only"` или `"kerberos_only"`. Никогда не используйте `"mock"` в боевом контуре (сработает Fail-fast проверка).
- [ ] **Включение Secure Cookies**: Установите `server.secure_cookies: true` (или `SECURE_COOKIES=true`), чтобы сессионные куки передавались строго по HTTPS.
- [ ] **Белый список CORS**: Задайте боевые домены в `server.cors_origins` (или `CORS_ORIGINS=https://sql-explorer.company.local`).
- [ ] **Проверка сертификатов LDAPS**: Смонтируйте корневой сертификат УЦ компании (`ca_cert_file`) и убедитесь, что `allow_insecure_ssl: false`.
- [ ] **Rate Limiting на уровне Ingress**: Помимо встроенного лимитера приложения, рекомендуется ограничить частоту запросов к `/api/auth/login` на уровне Ingress Controller (например, аннотации `limit-rps: "5"`), обеспечивая эшелонированную защиту.
- [ ] **TLS-терминация**: Обеспечьте работу веб-портала строго по HTTPS с валидным SSL/TLS-сертификатом.

---

## Настройка ACL (Контроль доступа)

В файле `config/config.yaml` настраиваются права доступа:
```yaml
acl:
  # Кто имеет право входа в UI
  ui_access:
    allowed_users: ["*"]
    allowed_groups: ["bi-analysts", "data-engineers", "data-platform-admins"]
    admin_groups: ["data-platform-admins"]

clusters:
  - id: "trino-analytics"
    name: "Trino Analytics (Prod)"
    type: "trino"
    acl:
      allowed_groups: ["bi-analysts", "data-engineers"]
      allowed_users: []

  - id: "hive-hortonworks"
    name: "Hive HDP Cluster"
    type: "hive"
    acl:
      allowed_groups: ["data-engineers"] # Только дата-инженеры
      allowed_users: ["vip_analyst"]
```

---

## Быстрый старт и локальный запуск

### Режим разработки (Dev Mode)

#### 1. Запуск Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m backend.app.main
```
Backend будет доступен по адресу: `http://localhost:8000`.

#### 2. Запуск Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend откроется на `http://localhost:5173` с автоматическим проксированием запросов к бэкенду.

В конфигурации по умолчанию включен режим `auth.mode: "mock"`, позволяющий сразу протестировать вход под разными ролями:
- `analyst_user` / `password123` (группа `bi-analysts` — доступ к Trino и Apache Hive).
- `de_user` / `password123` (группа `data-engineers` — доступ ко всем кластерам, включая Hortonworks HDP).
- `admin_user` / `password123` (Администратор).

---

## Развертывание в Kubernetes (Helm)

Для развертывания в Kubernetes подготовлен готовый Helm-чарт в директории `helm/sql-explorer`:

```bash
# Установка с базовыми параметрами
helm install sql-explorer ./helm/sql-explorer -n analytics --create-namespace
```

### Установка с Kerberos Keytab и внешним PostgreSQL:
```bash
helm upgrade --install sql-explorer ./helm/sql-explorer \
  -n analytics \
  --set image.repository="registry.company.local/analytics/sql-explorer" \
  --set image.tag="0.1.0" \
  --set config.database.url="postgresql+asyncpg://sql_user:sql_pass@postgres.analytics.svc:5432/sql_explorer" \
  --set secrets.jwtSecret="SuperSecretKey123" \
  --set secrets.ldapBindPassword="ServiceAccountPassword" \
  --set secrets.kerberosKeytabBase64="$(base64 -w 0 /path/to/sql-explorer.keytab)" \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host="sql-explorer.company.local"
```

Подробное руководство по параметрам чарта см. в [helm/sql-explorer/README.md](file:///Users/mvmalykh/IdeaProjects/sql-explorer/helm/sql-explorer/README.md).

---

## Автономный демонстрационный стенд (Docker Compose)

В проект включен полностью настроенный керберизированный демо-стенд (`demo/`):
- **MIT Kerberos KDC** (Realm `COMPANY.LOCAL`, keytabs для Trino, Hive и Web-интерфейса).
- **OpenLDAP** (пользователи `analyst_user`, `de_user`, `admin_user`).
- **Trino Coordinator** с Kerberos и каталогами `tpch` и `hive`.
- **Hive Metastore** на PostgreSQL + **HiveServer2** с поддержкой `doAs`.
- **SQL Web Explorer** на порту **8002**.

Запуск одной командой:
```bash
./demo/start-demo.sh
```
Веб-интерфейс будет доступен по адресу: 👉 **[http://localhost:8002](http://localhost:8002)**.  
Подробная инструкция со сценариями тестирования — в [DEMO.md](file:///Users/mvmalykh/IdeaProjects/sql-explorer/DEMO.md).

---

## Запуск в Docker

Сборка и запуск единого контейнера (Frontend + Backend):
```bash
docker build -t sql-explorer:latest .
docker run -d -p 8000:8000 -v $(pwd)/config:/app/config sql-explorer:latest
```
Интерфейс будет доступен в браузере: `http://localhost:8000`.

---

## Возможности редактора и выполнение запросов

- **Мульти-запросы**: В редакторе можно писать цепочки SQL-запросов, разделяя их точкой с запятой `;`.
- **Запуск выделенного фрагмента**: Если в Monaco Editor выделить часть текста и нажать `Cmd+Enter` (или кнопку «Выполнить»), исполнится только выделенный SQL.
- **Запрос под курсором**: Если выделения нет, автоматически находится и исполняется запрос под текущей позицией курсора.
- **Горячие клавиши**:
  - `Cmd+Enter` / `Ctrl+Enter` — запустить запрос.
  - `Cmd+S` / `Ctrl+S` — сохранить запрос в избранное.
  - `Cmd+F` / `Ctrl+F` — поиск и замена в редакторе кода.

---

## Фоновая очередь задач и сохранение результатов

1. **Независимое выполнение**: При запуске запрос регистрируется в очереди (`QUEUED` -> `RUNNING`). Пользователь может закрыть браузер, выключить компьютер или переключить вкладку — выполнение на кластере Trino/Hive продолжится на сервере.
2. **Персистентное хранилище**: После завершения результат сохраняется в сжатом виде (`data/results/{query_id}.json.gz`).
3. **Остановка и удаление из очереди**:
   - В интерфейсе на вкладке **«Очередь»** доступна кнопка **«Остановить и удалить»** (`DELETE /api/queries/queue/{query_id}`).
   - Если запрос еще исполняется на кластере, сервер немедленно посылает команду отмены (`cancel`) в координатор Trino/Hive, освобождает ресурсы и удаляет задачу из очереди.
4. **Desktop Notifications**: Интеграция с браузерным Notification API оповещает о готовности результата даже при свернутом окне.
