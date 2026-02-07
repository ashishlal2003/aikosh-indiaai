from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from api.routes.speech_to_text import router as speech_to_text_router
from api.routes.chat import router as chat_router
from api.routes.documents import router as documents_router
load_dotenv()

app = FastAPI(
    title="MSME ODR Assistant API",
    description="AI-powered conversational assistant for MSME dispute resolution",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(speech_to_text_router, prefix="/api", tags=["Speech to Text"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(documents_router, prefix="/api", tags=["Documents"])

@app.get("/health")
def health():
    return {"status": "Up and running!"}