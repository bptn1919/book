from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .models import get_db, init_db

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with get_db() as conn:
        conn.execute(
            "UPDATE projects SET step_state='FAILED', step_started_at=NULL "
            "WHERE step_state='RUNNING'"
        )
    yield


app = FastAPI(title="Book Illustration Studio", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
