from dotenv import load_dotenv
import os
import requests
from fastapi import HTTPException, File, UploadFile

class SpeechToTextController:
    def __init__(self):
        load_dotenv()
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE"))

    def transcribe(self, file: UploadFile = File(...)) -> str:
        if file.content_type not in ["audio/wav", "audio/mp3", "audio/webm"]:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        if file.size > self.max_file_size:
            raise HTTPException(status_code=400, detail="File too large")
        response = requests.post(
            "https://api.groq.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {self.groq_api_key}"},
            data={"file": file.file, "model": "whisper-large-v3"},
        )
        return response.json()