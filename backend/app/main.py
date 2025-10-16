"""Main FastAPI application"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .api import auth, recommendations, analytics, playlists

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Moodify API",
    description="AI-Powered Music Discovery Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=False,
    same_site="lax"
)

# Include all API routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(recommendations.router, tags=["Recommendations"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(playlists.router, tags=["Playlists"])

# Debug: Log registered routes
logger.info("Registered analytics routes with /api prefix")
for route in analytics.router.routes:
    logger.info(f"Analytics route: {route.methods} {route.path}")

@app.get("/")
async def root():
    return {"message": "Moodify API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "env_vars_updated": True, 
        "latest_commit": "05f2560",
        "analytics_routes": ["/api/top-tracks", "/api/my-playlists", "/api/album-covers"],
        "build_timestamp": "2025-01-16T01:20:00Z"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
