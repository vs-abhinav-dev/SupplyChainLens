from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.analytics import router as analytics_router
from .routes.graph import router as graph_router
from .routes.packages import router as packages_router


def create_app() -> FastAPI:
    """Create and configure the SupplyChainLens FastAPI application."""
    app = FastAPI(
        title="SupplyChainLens API",
        version="0.1.0",
        description="Graph Analytics & Software Supply Chain Intelligence Platform",
    )

    # Enable CORS for local web development (React / Vite)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(packages_router)
    app.include_router(graph_router)
    app.include_router(analytics_router)

    @app.get("/api/health", tags=["system"])
    def health_check():
        return {"status": "ok", "service": "supplychainlens"}

    @app.get("/", tags=["system"])
    def root():
        return {
            "message": "Welcome to SupplyChainLens API",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    return app


app = create_app()
