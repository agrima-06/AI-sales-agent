from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import AppException
from app.middleware.logging import CorrelationIdMiddleware
from app.api.v1.health import router as health_router

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0",
)

# 1. Register Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)

# 2. Register Routers
app.include_router(health_router, prefix=settings.API_V1_STR, tags=["System Health"])


# 3. Register Custom Exception Handlers for Unified RFC 7807 responses
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": correlation_id
            }
        }
    )


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Enterprise AI Sales Agent API",
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
