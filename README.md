# SQL Web Explorer (Trino & Apache Hive / Hortonworks / Cloudera)

Современный корпоративный Web-интерфейс для выполнения SQL-запросов к распределенным аналитическим движкам **Trino** и **Apache Hive (HiveServer2)** с поддержкой мультикластерности, аутентификации через **LDAPS** и **Kerberos SPNEGO SSO**, сквозной **имперсонации (impersonation / doAs)**, гибкой ролевой модели **ACL** и деплоя в **Kubernetes (Helm)**.

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
  - Обеспечивает строгое соблюдение политик безопасности **Apache Ranger** и **Trino System Access Control** на уровне хранилища данных.
- **Современный Web-UI (Svelte 5 + TypeScript + Tailwind CSS)**:
  - **Monaco Editor** (движок VS Code) со светлой темой, диалектами SQL, подсветкой синтаксиса Trino/Hive, шорткатами `Cmd+Enter` / `Ctrl+Enter`.
  - **Мульти-запросы**: Выполнение нескольких запросов на одной странице, запуск выделенного фрагмента текста или запроса под текущей позицией курсора.
  - **Дерево схемы данных (Schema Explorer)**: Интерактивный просмотр Каталогов -> Схем -> Таблиц -> Колонок и типов данных.
  - **Стриминг результатов**: Server-Sent Events (SSE) в реальном времени с отображением прогресса и таймингов.
  - **Отмена запросов**: Кнопка «Stop» немедленно посылает сигнал отмены в координатор Trino/Hive и освобождает кластерные ресурсы.
  - **Виртуализированная таблица**: Фильтрация, пагинация, мгновенный экспорт в **CSV** и **JSON**.
  - **Фоновая очередь задач**: Запросы продолжают исполняться на сервере даже при закрытии вкладки; просмотр статусов и загрузка результатов из архива.
  - **Desktop Notifications**: Браузерные уведомления при завершении длительных запросов.
- **Готовность к Production и Kubernetes**:
  - Готовый **Helm Chart** (`helm/sql-explorer`) для развертывания в Kubernetes с поддержкой Ingress, cert-manager, ConfigMap, Secrets и keytab.
  - Поддержка **PostgreSQL** и **SQLite** (с PersistentVolumeClaim) для хранения истории и сохраненных запросов.

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
│   ├── docker-compose.yml      # Trino, Hive, Metastore, OpenLDAP, MIT KDC, SQL Explorer
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
