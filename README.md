# SQL Explorer (Trino & Apache Hive / Hortonworks / Cloudera)

Современный корпоративный Web-интерфейс для выполнения SQL-запросов к распределенным движкам **Trino** и **Apache Hive (HiveServer2)** с поддержкой мультикластерности, аутентификации через **LDAPS** и **Kerberos SPNEGO SSO**, сквозной **имперсонации (impersonation / doAs)** и гибкой ролевой модели **ACL**.

---

## Ключевые возможности

- **Мультикластерность**: Поддержка нескольких независимых кластеров Trino и Hive (Hortonworks HDP, Cloudera CDP, чистый Apache Hive) с мгновенным переключением в UI.
- **Enterprise Security**:
  - **Kerberos SPNEGO SSO**: Бесшовный вход без ввода пароля через тикеты Kerberos в браузере.
  - **LDAPS (Active Directory / OpenLDAP / FreeIPA)**: Защищенный вход по логину/паролю с автоматическим получением групп пользователя (`memberOf` и рекурсивно).
  - **Гибкий ACL**: Ограничение доступа к Web-UI и к конкретным кластерам по списку пользователей и/или списку LDAP-групп.
- **Сквозная имперсонация (Impersonation / Proxy User)**:
  - **Trino**: Выполнение запросов от имени реального пользователя через заголовок `X-Trino-User`.
  - **Hive (HiveServer2)**: Выполнение запросов с параметром `hive.server2.proxy.user` (doAs).
  - Обеспечивает соблюдение политик безопасности **Apache Ranger** и **Trino System Access Control** на уровне хранилища данных.
- **Современный Web-UI (Svelte 5 + TypeScript)**:
  - **Monaco Editor** (движок VS Code) с диалектами SQL, подсветкой функций Trino/Hive, шорткатами `Cmd+Enter` / `Ctrl+Enter` и запуском выделенного фрагмента.
  - **Дерево схемы данных (Schema Explorer)**: Интерактивный просмотр Каталогов -> Схем -> Таблиц -> Колонок и типов.
  - **Стриминг результатов**: Server-Sent Events (SSE) в реальном времени с прогрессом и временем выполнения.
  - **Отмена запросов**: Кнопка «Stop» немедленно посылает сигнал отмены в координатор Trino/Hive.
  - **Виртуализированная таблица**: Фильтрация, пагинация, мгновенный экспорт в **CSV** и **JSON**.
  - **История запросов и избранное**: Сохранение сниппетов и истории с метриками.
- **Хранение истории**: Поддержка **SQLite** (из коробки) и **PostgreSQL**.

---

## Архитектура проекта

```
sql-explorer/
├── backend/                  # Python FastAPI Backend
│   ├── app/
│   │   ├── api/              # REST & SSE эндпоинты (auth, clusters, catalog, queries)
│   │   ├── core/             # Безопасность: LDAPS (ldap3), Kerberos (spnego), ACL движок, JWT
│   │   ├── db/               # SQLAlchemy сессии (SQLite & PostgreSQL)
│   │   ├── models/           # Модели данных: QueryHistory, SavedQuery
│   │   ├── services/         # Движки: TrinoEngine, HiveEngine, MockEngine, QueryManager
│   │   ├── config.py         # Загрузка и Pydantic-валидация config.yaml
│   │   └── main.py           # FastAPI app + раздача SPA статики
│   ├── tests/                # Интеграционные тесты API и ACL
│   └── requirements.txt      # Зависимости Python
│
├── frontend/                 # Svelte 5 SPA (Vite + TypeScript)
│   ├── src/
│   │   ├── api/              # Клиент API и обработка SSE потоков
│   │   ├── components/       # Header, Sidebar, SqlEditor, QueryToolbar, ResultsGrid, LoginModal
│   │   ├── types.ts          # Модели TypeScript
│   │   └── App.svelte        # Главный компонент (Svelte 5 Runes)
│   └── package.json
│
├── config/
│   └── config.yaml           # Конфигурация кластеров, LDAP, Kerberos и ACL
├── Dockerfile                # Multi-stage Docker образ (Node -> Python)
└── docker-compose.yml        # Docker Compose сценарий
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

## Запуск в Docker

Сборка и запуск единого контейнера (Frontend + Backend):
```bash
docker build -t sql-explorer:latest .
docker run -d -p 8000:8000 -v $(pwd)/config:/app/config sql-explorer:latest
```
Интерфейс будет доступен в браузере: `http://localhost:8000`.

---

## Фоновая очередь задач и сохранение результатов

1. **Независимое выполнение**: При запуске запрос регистрируется в очереди (`QUEUED` -> `RUNNING`). Пользователь может закрыть браузер, выключить компьютер или переключить вкладку — выполнение на кластере Trino/Hive продолжится на сервере.
2. **Персистентное хранилище**: После завершения результат сохраняется в сжатом виде (`data/results/{query_id}.json.gz`).
3. **Остановка и удаление из очереди**:
   - В интерфейсе на вкладке **«Очередь»** доступна кнопка **«Остановить и удалить»** (`DELETE /api/queries/queue/{query_id}`).
   - Если запрос еще исполняется на кластере, сервер немедленно посылает команду отмены (`cancel`) в координатор Trino/Hive, освобождает ресурсы и удаляет задачу из очереди.
4. **Desktop Notifications**: Интеграция с браузерным Notification API оповещает о готовности результата даже при свернутом окне.
