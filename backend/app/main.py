import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.config import settings
from backend.app.db.session import init_db
from backend.app.api import auth, clusters, catalog, queries

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация БД (создание таблиц при первом старте)
    await init_db()
    yield

app = FastAPI(
    title="SQL Explorer (Trino & Hive)",
    description="Web-UI для аналитических запросов к Trino и Hive с поддержкой LDAPS/Kerberos, ACL и имперсонации",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение API роутеров
app.include_router(auth.router, prefix="/api")
app.include_router(clusters.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(queries.router, prefix="/api")

@app.get("/api/health")
@app.get("/healthz")
async def health():
    return {
        "status": "healthy",
        "auth_mode": settings.auth.mode,
        "clusters_count": len(settings.clusters)
    }

# Раздача SPA статики (когда frontend собран в frontend/dist)
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.debug
    )
