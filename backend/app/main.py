from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_schema
from app.routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_schema()
    yield


app = FastAPI(title="webstore-backend", lifespan=lifespan)
app.include_router(router)
