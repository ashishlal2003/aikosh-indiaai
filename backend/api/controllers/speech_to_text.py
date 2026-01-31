from dotenv import load_dotenv
import os
import requests
from fastapi import HTTPException, File, UploadFile

class SpeechToTextController:
    def __init__(self):
        load_dotenv()
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024)) 

    def transcribe(self, file: UploadFile = File(...)):
        if file.content_type not in ["audio/wav", "audio/mp3", "audio/webm", "audio/mpeg", "audio/mp4", "audio/m4a"]:
             raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
        
        if file.size > self.max_file_size:
            raise HTTPException(status_code=400, detail="File too large")
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}"
        }
        
        data = {
            "model": "whisper-large-v3-turbo"
        }
        
        files = {
            "file": (file.filename, file.file, file.content_type)
        }

        try:
            response = requests.post(url, headers=headers, data=data, files=files)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_detail = response.json() if response and response.content else str(e)
            raise HTTPException(status_code=500, detail=f"Transcription failed: {error_detail}")