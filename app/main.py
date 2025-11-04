from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.auth import initialize_default_groups, initialize_superadmin
from app.core.database import AsyncSessionLocal
from app.services.scheduler import scheduler
from app.services.redis_logger import redis_logger
from app.services.mcp import mcp_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await redis_logger.connect()
    await scheduler.start()

    # Initialize default groups
    async with AsyncSessionLocal() as db:
        await initialize_default_groups(db)

    # Initialize superadmin user
    async with AsyncSessionLocal() as db:
        await initialize_superadmin(db)

    # Initialize MCP client
    async with AsyncSessionLocal() as db:
        await mcp_client.initialize(db)

    yield
    # Shutdown
    await scheduler.stop()
    await redis_logger.disconnect()


app = FastAPI(
    title="SINAS - AI Agent Platform",
    description="Multi-agent AI platform with LLM chat, webhooks, MCP tools, and function execution",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routes
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/scheduler/status")
async def scheduler_status():
    return scheduler.get_scheduler_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)