from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppException(HTTPException):
    """
    Base application exception. Returns RFC 7807 compliant errors.
    """
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message
        self.details = details or {}


class InsufficientStockException(AppException):
    def __init__(self, sku: str, requested: int, available: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INSUFFICIENT_STOCK",
            message=f"Requested quantity of item {sku} exceeds current stock.",
            details={
                "product_sku": sku,
                "requested_quantity": requested,
                "available_quantity": available
            }
        )


class DatabaseConnectionException(AppException):
    def __init__(self, details: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DATABASE_CONNECTION_ERROR",
            message="Database connectivity issue detected.",
            details={"error_detail": details}
        )
