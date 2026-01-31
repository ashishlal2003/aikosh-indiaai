from fastapi import APIRouter, File, UploadFile
from api.controllers.speech_to_text import SpeechToTextController

router = APIRouter()
speech_to_text_controller = SpeechToTextController()

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):    
    return speech_to_text_controller.transcribe(file)