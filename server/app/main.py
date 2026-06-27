from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.editor import router as editor_router
from app.api.health import router as health_router
from app.api.osm import router as osm_router
from app.api.simulation import router as simulation_router
from app.api.training import router as training_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="UrbanFlow AI Server",
        version="0.1.0",
        description="Backend API for OSM import, city graph generation, traffic simulation and AI control.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(osm_router, prefix="/osm", tags=["osm"])
    app.include_router(simulation_router, prefix="/simulation", tags=["simulation"])
    app.include_router(editor_router, prefix="/editor", tags=["editor"])
    app.include_router(training_router, prefix="/training", tags=["training"])

    return app


app = create_app()