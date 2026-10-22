import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from .database import Base, SessionLocal, engine
from .routers import auth, exchanges, skills, users
from .seed import seed


def init_db() -> None:
    # БД в соседнем контейнере может подниматься дольше API — ждём её
    for attempt in range(30):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except OperationalError:
            if attempt == 29:
                raise
            time.sleep(1)
    with SessionLocal() as db:
        seed(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="SkillSwap API",
    description="Платформа обмена навыками: «научу тому, что умею, — научусь тому, что хочу».",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(skills.router)
app.include_router(exchanges.router)
app.include_router(users.router)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}
