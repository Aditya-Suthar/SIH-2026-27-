from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from .auth import router as auth_router
from .cases import router as cases_router
from .database import engine, Base
from . import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        try:
            Base.metadata.create_all(bind=engine)
        except SQLAlchemyError:
            raise RuntimeError(
                "Database initialization failed. Check DATABASE_URL, start PostgreSQL, "
                "and ensure the target database exists and is accessible."
            ) from None
        yield
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)

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

app.include_router(auth_router)
app.include_router(cases_router)


@app.get("/")
def root():
    return {"message": "SIH backend is running"}