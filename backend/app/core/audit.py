import json
import logging
import datetime
from collections import deque
from typing import Optional, Dict, Any

logger = logging.getLogger("security.audit")

# Кольцевой буфер для инспекции недавних событий безопасности (используется в тестах и мониторинге)
recent_audit_events: deque = deque(maxlen=200)

class AuditEventType:
    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    AUTH_RATE_LIMITED = "AUTH_RATE_LIMITED"
    AUTH_LOGOUT = "AUTH_LOGOUT"
    QUERY_EXECUTED = "QUERY_EXECUTED"
    QUERY_CANCELLED = "QUERY_CANCELLED"
    ACCESS_DENIED_ACL = "ACCESS_DENIED_ACL"
    ACCESS_DENIED_BOLA = "ACCESS_DENIED_BOLA"

def log_audit_event(
    event_type: str,
    username: str,
    client_ip: str,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None
):
    """
    Формирует структурированное JSON-событие аудита информационной безопасности.
    """
    event = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event_type": event_type,
        "username": username,
        "client_ip": client_ip,
        "status": status,
        "details": details or {}
    }
    recent_audit_events.append(event)
    logger.info(json.dumps(event, ensure_ascii=False))
