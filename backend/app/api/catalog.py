import logging
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.app.config import settings, ClusterConfig
from backend.app.core.security import get_current_user, UserSession
from backend.app.core.acl import check_cluster_access
from backend.app.services.trino_engine import TrinoExecutionEngine
from backend.app.services.hive_engine import HiveExecutionEngine
from backend.app.services.mock_engine import MockExecutionEngine

logger = logging.getLogger("catalog_api")
router = APIRouter(prefix="/catalog", tags=["catalog"])

def _get_cluster_or_404(cluster_id: str, user: UserSession) -> ClusterConfig:
    cluster = next((c for c in settings.clusters if c.id == cluster_id), None)
    if not cluster:
        raise HTTPException(status_code=404, detail="Кластер не найден")
    if not check_cluster_access(user, cluster):
        raise HTTPException(status_code=403, detail="Доступ к данному кластеру запрещен ACL")
    return cluster

def _get_engine(cluster: ClusterConfig):
    if cluster.type == "trino":
        return TrinoExecutionEngine(cluster)
    elif cluster.type == "hive":
        return HiveExecutionEngine(cluster)
    else:
        return MockExecutionEngine(cluster)

@router.get("/{cluster_id}/catalogs", response_model=List[str])
async def get_catalogs(cluster_id: str, current_user: UserSession = Depends(get_current_user)):
    cluster = _get_cluster_or_404(cluster_id, current_user)
    engine = _get_engine(cluster)
    try:
        if hasattr(engine, "get_catalogs"):
            return await engine.get_catalogs(current_user.username)
        return ["default"]
    except Exception as e:
        logger.warning(f"Не удалось получить каталоги для {cluster_id}: {e}, возвращаем mock/default")
        mock = MockExecutionEngine(cluster)
        return await mock.get_catalogs(current_user.username)

@router.get("/{cluster_id}/schemas", response_model=List[str])
async def get_schemas(
    cluster_id: str,
    catalog: str = Query(default="hive"),
    current_user: UserSession = Depends(get_current_user)
):
    cluster = _get_cluster_or_404(cluster_id, current_user)
    engine = _get_engine(cluster)
    try:
        if cluster.type == "trino" and hasattr(engine, "get_schemas"):
            return await engine.get_schemas(current_user.username, catalog)
        elif cluster.type == "hive" and hasattr(engine, "get_schemas"):
            return await engine.get_schemas(current_user.username)
        mock = MockExecutionEngine(cluster)
        return await mock.get_schemas(current_user.username, catalog)
    except Exception as e:
        logger.warning(f"Не удалось получить схемы для {cluster_id}: {e}, возврат mock")
        mock = MockExecutionEngine(cluster)
        return await mock.get_schemas(current_user.username, catalog)

@router.get("/{cluster_id}/tables", response_model=List[str])
async def get_tables(
    cluster_id: str,
    catalog: str = Query(default="hive"),
    schema: str = Query(default="default"),
    current_user: UserSession = Depends(get_current_user)
):
    cluster = _get_cluster_or_404(cluster_id, current_user)
    engine = _get_engine(cluster)
    try:
        if cluster.type == "trino" and hasattr(engine, "get_tables"):
            return await engine.get_tables(current_user.username, catalog, schema)
        elif cluster.type == "hive" and hasattr(engine, "get_tables"):
            return await engine.get_tables(current_user.username, schema)
        mock = MockExecutionEngine(cluster)
        return await mock.get_tables(current_user.username, catalog, schema)
    except Exception as e:
        logger.warning(f"Не удалось получить таблицы для {cluster_id}: {e}, возврат mock")
        mock = MockExecutionEngine(cluster)
        return await mock.get_tables(current_user.username, catalog, schema)

@router.get("/{cluster_id}/columns")
async def get_columns(
    cluster_id: str,
    catalog: str = Query(default="hive"),
    schema: str = Query(default="default"),
    table: str = Query(...),
    current_user: UserSession = Depends(get_current_user)
):
    cluster = _get_cluster_or_404(cluster_id, current_user)
    engine = _get_engine(cluster)
    try:
        if cluster.type == "trino" and hasattr(engine, "get_columns"):
            return await engine.get_columns(current_user.username, catalog, schema, table)
        elif cluster.type == "hive" and hasattr(engine, "get_columns"):
            return await engine.get_columns(current_user.username, schema, table)
        mock = MockExecutionEngine(cluster)
        return await mock.get_columns(current_user.username, catalog, schema, table)
    except Exception as e:
        logger.warning(f"Не удалось получить колонки для {cluster_id}: {e}, возврат mock")
        mock = MockExecutionEngine(cluster)
        return await mock.get_columns(current_user.username, catalog, schema, table)
