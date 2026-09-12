import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .operations import router as operations_router
from .chat import router as chat_router
from .monitoring import router as monitoring_router
from .voice import router as voice_router
from .questionnaire import router as questionnaire_router
from .ai_history import router as ai_history_router
from .ai import router as ai_router
from .auth import router as auth_router
from .cases import router as cases_router
from .database import engine, Base
from . import models


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip().rstrip("/") for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(ai_router)
app.include_router(ai_history_router)
app.include_router(operations_router)
app.include_router(chat_router)
app.include_router(monitoring_router)
app.include_router(voice_router)
app.include_router(questionnaire_router)


@app.get("/")
def root():
    return {"message": "SIH backend is running"}
