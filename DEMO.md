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
docker compose -f demo/docker-compose.demo.yml up -d --build
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

---

## Архитектура и сетевые порты

| Сервис | Хост в сети Docker | Внешний порт | Описание |
| :--- | :--- | :--- | :--- |
| **SQL Explorer** | `sql-explorer` | `8000` | Web UI & REST API |
| **Trino Coordinator** | `trino-coordinator` | `8080` | Trino HTTP / Kerberos API |
| **HiveServer2** | `hive-server` | `10000` | Thrift HiveServer2 RPC |
| **Hive Metastore** | `hive-metastore` | `9083` | Thrift Metastore RPC |
| **PostgreSQL** | `postgres-meta` | `5432` | БД метаданных Hive Metastore |
| **OpenLDAP** | `openldap` | `389` | Каталог пользователей и групп |
| **MIT Kerberos KDC**| `kdc` | `88` | Аутентификация Kerberos / TGT |
