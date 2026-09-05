# Демонстрационный стенд SQL Explorer

Автономный демонстрационный стенд в Docker Compose, разворачивающий:
1. **MIT Kerberos KDC** (Realm `COMPANY.LOCAL`, keytabs, единый `krb5.conf`).
2. **OpenLDAP** (Пользователи `analyst_user`, `de_user`, `admin_user`, сервисная учетная запись, ролевые группы).
3. **Apache Hive 4.0.0** (Hive Metastore на PostgreSQL + HiveServer2 с Kerberos-аутентификацией и имперсонацией `doAs`).
4. **Trino Coordinator** (Kerberos-аутентификация, имперсонация `X-Trino-User`, каталоги `tpch` и `hive`).
5. **SQL Explorer** (FastAPI Backend + Svelte 5 Web UI, интеграция с LDAP, Kerberos SSO/GSSAPI).

---

## Быстрый старт

### Запуск стенда
```bash
./demo/start-demo.sh
```
*Или через docker compose напрямую:*
```bash
docker compose -f demo/docker-compose.yaml up -d --build
```

После запуска откройте веб-интерфейс:
👉 **[http://localhost:8002](http://localhost:8002)**

### Остановка стенда
```bash
./demo/stop-demo.sh
```
Для остановки с удалением томов данных:
```bash
./demo/stop-demo.sh -v
```

---

## Учетные записи и роли

Все пользователи заведены в OpenLDAP и Kerberos:

| Пользователь | Пароль | Роли / Группы LDAP | Назначение и доступные кластеры |
| :--- | :--- | :--- | :--- |
| **`analyst_user`** | `password123` | `bi-analysts` | **BI Аналитик**: доступ к Trino и общему Hive Demo. Не видит защищенный кластер DE Only. |
| **`de_user`** | `password123` | `data-engineers`, `bi-analysts` | **Дата-инженер**: доступ ко всем кластерам Trino и HiveServer2 (doAs). |
| **`admin_user`** | `password123` | `data-platform-admins` | **Администратор**: полный доступ ко всем кластерам и управление SQL Explorer. |

---

## Демонстрационные сценарии проверки

### 1. Проверка ролевой модели (ACL)
1. Войдите под пользователем **`analyst_user`** / `password123`.
2. В выпадающем списке кластеров отображаются:
   - `Trino Cluster (Kerberos + X-Trino-User)`
   - `Hive Server (Demo DB - All Roles)`
   *Кластер `Hive Server (DE Only)` скрыт согласно правилам безопасности.*
3. Выйдите и войдите под **`de_user`** / `password123`.
4. Теперь кластер `Hive Server (DE Only - Kerberos + doAs)` доступен в списке!

### 2. Запросы к Trino (Kerberos + X-Trino-User)
Выберите кластер **Trino Cluster** и выполните запросы к каталогу `tpch`:
```sql
SELECT 
    n.name AS country,
    r.name AS region,
    n.comment
FROM tpch.sf1.nation n
JOIN tpch.sf1.region r ON n.regionkey = r.regionkey
ORDER BY country;
```

```sql
SELECT 
    custkey,
    name,
    mktsegment,
    acctbal
FROM tpch.sf1.customer
ORDER BY acctbal DESC
LIMIT 10;
```

### 3. Запросы к Hive (Kerberos + doAs impersonation)
Выберите кластер **Hive Server (Demo DB - All Roles)** и выполните:
```sql
SELECT * FROM demo_db.sales;
```

```sql
SELECT 
    category, 
    COUNT(*) AS cnt, 
    SUM(amount) AS total_revenue
FROM demo_db.sales
GROUP BY category
ORDER BY total_revenue DESC;
```

```sql
SELECT * FROM demo_db.employees;
```

### 4. Мульти-запросы и запуск под курсором
В редакторе можно ввести сразу несколько запросов:
```sql
SELECT 'first query' AS msg;

SELECT 
    nationkey, 
    name 
FROM tpch.sf1.nation 
LIMIT 5;

SELECT 'third query' AS msg;
```
- **Запуск под курсором**: поставьте курсор внутрь второго запроса и нажмите `Cmd+Enter` (или `Ctrl+Enter`) — выполнится именно этот запрос.
- **Запуск выделения**: выделите мышью любой фрагмент SQL и нажмите «Выполнить» — в координатор отправится только выделенный текст.

---

## Архитектура и сетевые порты

Все контейнеры изолированы в отдельной сети `sql-demo-net` с префиксом `sql-demo-*`, что позволяет запускать стенд параллельно с другими сервисами (например, `hdfs-explorer`):

| Сервис | Контейнер / Хост в Docker | Внешний порт | Описание |
| :--- | :--- | :--- | :--- |
| **SQL Web Explorer** | `sql-demo-explorer` | `8002` | Web UI & REST API (внутри порт 8000) |
| **Trino Coordinator** | `sql-demo-trino` | `8080` (HTTP), `8443` (HTTPS) | Trino API с Kerberos и доступом к Hive и TPCH |
| **HiveServer2** | `sql-demo-hive-server` | `10000`, `10002` (Web) | Apache Hive 4.0.0 HS2 RPC с Kerberos и `doAs` |
| **Hive Metastore** | `sql-demo-hive-metastore` | `9083` | Метастор таблиц Hive |
| **PostgreSQL** | `sql-demo-postgres-meta` | `5432` | БД метаданных Hive Metastore |
| **OpenLDAP** | `sql-demo-ldap` | `1389` | Каталог пользователей и ролевых групп |
| **MIT Kerberos KDC** | `sql-demo-kdc` | `1088` | KDC Realm `COMPANY.LOCAL` |

