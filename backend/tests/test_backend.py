import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.db.session import init_db

@pytest.mark.asyncio
async def test_health():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_auth_and_acl_flow():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Попытка входа с неверным паролем
        bad_login = await client.post("/api/auth/login", json={"username": "analyst_user", "password": "wrong"})
        assert bad_login.status_code == 401

        # 2. Успешный вход под analyst_user (группа bi-analysts)
        login_resp = await client.post("/api/auth/login", json={"username": "analyst_user", "password": "password123"})
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Проверка текущего пользователя
        me_resp = await client.get("/api/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "analyst_user"

        # 4. Проверка доступных кластеров (analyst имеет bi-analysts, не должен видеть Hive HDP, где только data-engineers)
        clusters_resp = await client.get("/api/clusters", headers=headers)
        assert clusters_resp.status_code == 200
        clusters = clusters_resp.json()
        cluster_ids = [c["id"] for c in clusters]
        assert "trino-analytics" in cluster_ids
        assert "hive-apache" in cluster_ids
        assert "hive-hortonworks" not in cluster_ids  # Запрещен ACL для analyst_user!

        # 5. Выполнение запроса
        exec_resp = await client.post(
            "/api/queries/execute",
            headers=headers,
            json={"cluster_id": "trino-analytics", "query": "SELECT * FROM tpch.sf1.customer"}
        )
        assert exec_resp.status_code == 200
        query_id = exec_resp.json()["query_id"]
        assert query_id is not None

        # 6. Проверка истории
        history_resp = await client.get("/api/queries/history", headers=headers)
        assert history_resp.status_code == 200
        history_items = history_resp.json()
        assert len(history_items) > 0
        assert history_items[0]["id"] == query_id

@pytest.mark.asyncio
async def test_queue_persistence_and_cancel():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post("/api/auth/login", json={"username": "analyst_user", "password": "password123"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Запуск запроса
        exec_resp = await client.post(
            "/api/queries/execute",
            headers=headers,
            json={"cluster_id": "trino-analytics", "query": "SELECT * FROM tpch.sf1.customer"}
        )
        assert exec_resp.status_code == 200
        query_id = exec_resp.json()["query_id"]

        # 2. Проверка появления в очереди
        queue_resp = await client.get("/api/queries/queue", headers=headers)
        assert queue_resp.status_code == 200
        queue_items = queue_resp.json()
        assert any(item["id"] == query_id for item in queue_items)

        # 3. Тест удаления из очереди с остановкой
        delete_resp = await client.delete(f"/api/queries/queue/{query_id}", headers=headers)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["status"] == "ok"

        # 4. Проверяем, что запрос удален из очереди
        queue_after = await client.get("/api/queries/queue", headers=headers)
        assert not any(item["id"] == query_id for item in queue_after.json())

@pytest.mark.asyncio
async def test_security_catalog_sql_injection_rejected():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Авторизуемся
        login_resp = await client.post("/api/auth/login", json={"username": "analyst_user", "password": "password123"})
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        # 1. Попытка внедрения в параметр catalog
        bad_catalog_resp = await client.get(
            "/api/catalog/trino-analytics/schemas?catalog=hive;DROP%20TABLE%20users;--",
            headers=headers
        )
        assert bad_catalog_resp.status_code == 400
        assert "Недопустимые символы" in bad_catalog_resp.json()["detail"]

        # 2. Попытка внедрения в параметр schema
        bad_schema_resp = await client.get(
            "/api/catalog/trino-analytics/tables?catalog=hive&schema=default'--",
            headers=headers
        )
        assert bad_schema_resp.status_code == 400

        # 3. Попытка внедрения в параметр table
        bad_table_resp = await client.get(
            "/api/catalog/trino-analytics/columns?catalog=hive&schema=default&table=users;--",
            headers=headers
        )
        assert bad_table_resp.status_code == 400

@pytest.mark.asyncio
async def test_security_stream_bola_protection():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Запуск запроса пользователем analyst_user
        login_analyst = await client.post("/api/auth/login", json={"username": "analyst_user", "password": "password123"})
        analyst_headers = {"Authorization": f"Bearer {login_analyst.json()['access_token']}"}

        exec_resp = await client.post(
            "/api/queries/execute",
            headers=analyst_headers,
            json={"cluster_id": "trino-analytics", "query": "SELECT * FROM tpch.sf1.customer"}
        )
        assert exec_resp.status_code == 200
        query_id = exec_resp.json()["query_id"]

        # 2. Вход под другим пользователем de_user
        login_de = await client.post("/api/auth/login", json={"username": "de_user", "password": "password123"})
        de_headers = {"Authorization": f"Bearer {login_de.json()['access_token']}"}

        # 3. de_user пытается подключиться к стриму analyst_user -> ожидаем 403 Forbidden!
        stream_resp = await client.get(f"/api/queries/{query_id}/stream", headers=de_headers)
        assert stream_resp.status_code == 403
        assert "Доступ к чужому стриму" in stream_resp.json()["detail"]

@pytest.mark.asyncio
async def test_security_spa_path_traversal():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Попытка запросить файл конфигурации через обход пути
        resp = await client.get("/../../config/config.yaml")
        # Должен возвращаться либо 404, либо fallback на index.html, но ни в коем случае не config.yaml
        if resp.status_code == 200:
            assert "server:" not in resp.text
            assert "bind_password" not in resp.text

@pytest.mark.asyncio
async def test_security_headers_present():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

@pytest.mark.asyncio
async def test_security_token_revocation_on_logout():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Вход
        login_resp = await client.post("/api/auth/login", json={"username": "analyst_user", "password": "password123"})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Проверяем, что токен работает
        me_before = await client.get("/api/auth/me", headers=headers)
        assert me_before.status_code == 200

        # 3. Выход (отзыв токена)
        logout_resp = await client.post("/api/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

        # 4. Повторный запрос с отозванным токеном должен вернуть 401 Unauthorized
        me_after = await client.get("/api/auth/me", headers=headers)
        assert me_after.status_code == 401
        assert "Токен отозван" in me_after.json()["detail"]

        # 5. Проверяем персистентность (эмуляция другой реплики/пода: очищаем L1 in-memory кэш)
        from backend.app.core.security import _revoked_tokens_cache
        _revoked_tokens_cache.clear()

        me_after_cache_clear = await client.get("/api/auth/me", headers=headers)
        assert me_after_cache_clear.status_code == 401
        assert "Токен отозван" in me_after_cache_clear.json()["detail"]

@pytest.mark.asyncio
async def test_security_login_rate_limiting():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_user = "brute_force_target_user"
        # Выполняем 5 неудачных попыток входа
        for _ in range(5):
            bad_resp = await client.post("/api/auth/login", json={"username": test_user, "password": "wrongpassword"})
            assert bad_resp.status_code == 401

        # 6-я попытка должна быть заблокирована лимитером (429 Too Many Requests)
        rate_limited_resp = await client.post("/api/auth/login", json={"username": test_user, "password": "wrongpassword"})
        assert rate_limited_resp.status_code == 429
        assert "Слишком много" in rate_limited_resp.json()["detail"]

@pytest.mark.asyncio
async def test_security_audit_logging():
    from backend.app.core.audit import recent_audit_events, AuditEventType
    recent_audit_events.clear()

    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Успешный вход
        login_resp = await client.post("/api/auth/login", json={"username": "analyst_user", "password": "password123"})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        login_events = [e for e in recent_audit_events if e["event_type"] == AuditEventType.AUTH_LOGIN_SUCCESS and e["username"] == "analyst_user"]
        assert len(login_events) >= 1

        # 2. Выполнение запроса
        exec_resp = await client.post(
            "/api/queries/execute",
            headers=headers,
            json={"cluster_id": "trino-analytics", "query": "SELECT 1;"}
        )
        assert exec_resp.status_code == 200
        query_id = exec_resp.json()["query_id"]

        exec_events = [e for e in recent_audit_events if e["event_type"] == AuditEventType.QUERY_EXECUTED and e["details"].get("query_id") == query_id]
        assert len(exec_events) >= 1

        # 3. Попытка BOLA другим пользователем
        login_de = await client.post("/api/auth/login", json={"username": "de_user", "password": "password123"})
        de_headers = {"Authorization": f"Bearer {login_de.json()['access_token']}"}

        bola_resp = await client.get(f"/api/queries/{query_id}/stream", headers=de_headers)
        assert bola_resp.status_code == 403

        bola_events = [e for e in recent_audit_events if e["event_type"] == AuditEventType.ACCESS_DENIED_BOLA and e["username"] == "de_user"]
        assert len(bola_events) >= 1

        # 4. Выход из системы
        logout_resp = await client.post("/api/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

        logout_events = [e for e in recent_audit_events if e["event_type"] == AuditEventType.AUTH_LOGOUT and e["username"] == "analyst_user"]
        assert len(logout_events) >= 1

@pytest.mark.asyncio
async def test_security_csp_header_present():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "worker-src 'self' blob:" in csp

