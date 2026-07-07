import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

logger = logging.getLogger("app.middleware.logging")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract correlation ID or generate a new one
        correlation_header_name = settings.X_CORRELATION_ID_HEADER
        correlation_id = request.headers.get(correlation_header_name)
        
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Save correlation ID to request state for downstream log references
        request.state.correlation_id = correlation_id

        start_time = time.time()
        
        # Log request receipt
        logger.info(
            f"Incoming request: {request.method} {request.url.path} | "
            f"correlation_id={correlation_id}"
        )

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            # Calculate duration for failed requests
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} | "
                f"duration={duration:.4f}s | error={str(exc)} | correlation_id={correlation_id}",
                exc_info=True
            )
            raise exc

        # Inject correlation ID into response headers
        response.headers[correlation_header_name] = correlation_id
        
        duration = time.time() - start_time
        logger.info(
            f"Finished request: {request.method} {request.url.path} | "
            f"status_code={response.status_code} | duration={duration:.4f}s | "
            f"correlation_id={correlation_id}"
        )

        return response
