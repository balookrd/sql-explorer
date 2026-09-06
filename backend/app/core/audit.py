import os
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

AUDIT_LOG_FILE = os.environ.get("AUDIT_LOG_FILE", "")


def audit_log(
    action: str,
    username: str,
    client_ip: str,
    details: Optional[Dict[str, Any]] = None,
    status: str = "SUCCESS",
):
    """
    Записывает структурированное событие аудита безопасности в JSON.
    """
    event = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "action": action,
        "event_type": action,
        "username": username or "anonymous",
        "client_ip": client_ip or "unknown",
        "status": status,
        "details": details or {},
    }
    recent_audit_events.append(event)
    log_line = json.dumps(event, ensure_ascii=False)

    if status == "SUCCESS":
        logger.info(f"[AUDIT] {log_line}")
    elif status == "WARNING":
        logger.warning(f"[AUDIT] {log_line}")
    else:
        logger.error(f"[AUDIT] {log_line}")

    if AUDIT_LOG_FILE:
        try:
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            logger.error(f"Не удалось записать в audit log file: {e}")


def log_audit_event(
    event_type: str,
    username: str,
    client_ip: str,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None
):
    audit_log(action=event_type, username=username, client_ip=client_ip, details=details, status=status)

