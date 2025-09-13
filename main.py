import uvicorn
import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from container import index_controller, cron_scheduler

sys.path.append(str(Path(__file__).parent / "migrations"))
from migrations.migration_runner import run_migrations

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    await cron_scheduler.start()
    yield
    await cron_scheduler.stop()


app = FastAPI(
    title="Hedgineer Equal Weight Stock Index",
    description="Assignment Required Endpoints: Build and retrieve equal-weighted stock index for top 100 US companies",
    version="1.0.0",
    lifespan=lifespan
)

index_controller.register_routes(app)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
