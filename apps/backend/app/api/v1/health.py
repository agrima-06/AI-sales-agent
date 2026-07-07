import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
from app.db.session import get_db
from app.core.config import settings
from app.core.exceptions import DatabaseConnectionException

logger = logging.getLogger("app.api.v1.health")
router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
def check_health(db: Session = Depends(get_db)):
    """
    Verifies API, PostgreSQL, and Redis database connections.
    """
    health_status = {
        "status": "healthy",
        "services": {
            "api": "online",
            "postgres": "unknown",
            "redis": "unknown"
        }
    }
    
    # 1. Verify PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["postgres"] = "online"
    except Exception as exc:
        logger.error(f"PostgreSQL connection health check failed: {exc}")
        health_status["services"]["postgres"] = "offline"
        health_status["status"] = "degraded"

    # 2. Verify Redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        redis_client.ping()
        health_status["services"]["redis"] = "online"
    except Exception as exc:
        logger.error(f"Redis connection health check failed: {exc}")
        health_status["services"]["redis"] = "offline"
        health_status["status"] = "degraded"

    if health_status["status"] == "degraded":
        # Returns standard exception payload envelope
        raise DatabaseConnectionException(
            details=f"PostgreSQL: {health_status['services']['postgres']}, Redis: {health_status['services']['redis']}"
        )

    return health_status
