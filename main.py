import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from admin_api import router
from services.broker import consume_shop_events
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    broker_task = asyncio.create_task(consume_shop_events())
    yield
    broker_task.cancel()


app = FastAPI(title="Auto Parts Admin API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8020, reload=True)
