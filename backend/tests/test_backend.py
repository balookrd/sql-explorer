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
