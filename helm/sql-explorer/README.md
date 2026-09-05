# Helm Chart: SQL Web Explorer

Production Helm chart для развертывания веб-портала аналитических запросов **SQL Web Explorer (Trino & Hive)** в Kubernetes.

## Возможности

- 🚀 **Trino & Hive (HS2)**: готовая интеграция с аналитическими кластерами компании.
- 🔐 **Безопасность**:
  - Kerberos SPNEGO SSO и LDAPS аутентификация.
  - Автоматическая инициализация сервисного билета Kerberos (`kinit`) из Secret keytab с правами `0400`.
  - Проброс реального пользователя (`X-Trino-User` для Trino, `doAs` для Hive).
  - RBAC / ACL правила доступа на уровне кластеров и UI.
- ⚡ **Стриминг результатов**: конфигурация Ingress оптимизирована под Server-Sent Events (отключена буферизация Nginx, увеличены таймауты).
- 💾 **Хранение состояния**: поддержка внешнего PostgreSQL или встроенного SQLite через PersistentVolumeClaim.

## Быстрый старт

### 1. Добавление или локальная установка чарта

```bash
# Установка с дефолтными значениями
helm install my-sql-explorer ./helm/sql-explorer -n analytics --create-namespace
```

### 2. Установка с Kerberos Keytab и внешним PostgreSQL

Создайте файл `custom-values.yaml`:

```yaml
image:
  repository: registry.company.local/analytics/sql-explorer
  tag: "0.1.0"

ingress:
  enabled: true
  hosts:
    - host: sql-explorer.company.local
      paths:
        - path: /
          pathType: Prefix

secrets:
  jwtSecret: "SuperSecretLongRandomKeyForProductionJWTToken12345"
  ldapBindPassword: "SecretServiceAccountPassword"
  # base64 -w 0 /path/to/sql-explorer.keytab
  kerberosKeytabBase64: "BQIAAAA4AA..."

config:
  database:
    url: "postgresql+asyncpg://sql_user:sql_pass@postgres.analytics.svc:5432/sql_explorer"
  auth:
    mode: "hybrid"
    ldap:
      server_uri: "ldaps://dc.company.local:636"
      bind_dn: "cn=svc_sql_explorer,ou=services,dc=company,dc=local"
      user_base_dn: "ou=users,dc=company,dc=local"
      group_base_dn: "ou=groups,dc=company,dc=local"
    kerberos:
      service_principal: "HTTP/sql-explorer.company.local@COMPANY.LOCAL"

kerberos:
  enabled: true
  krb5Conf: |
    [libdefaults]
        default_realm = COMPANY.LOCAL
        dns_lookup_realm = false
        dns_lookup_kdc = true
        ticket_lifetime = 24h
        renew_lifetime = 7d
        forwardable = true

    [realms]
        COMPANY.LOCAL = {
            kdc = kdc.company.local:88
            admin_server = kdc.company.local:749
        }

    [domain_realm]
        .company.local = COMPANY.LOCAL
        company.local = COMPANY.LOCAL
```

Примените установку:

```bash
helm upgrade --install sql-explorer ./helm/sql-explorer \
  -n analytics \
  -f custom-values.yaml
```

## Проверка статуса

```bash
kubectl get pods -n analytics -l app.kubernetes.io/name=sql-explorer
kubectl logs -n analytics -l app.kubernetes.io/name=sql-explorer -c sql-explorer
```
