import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
import base64

from app.schemas import ChatRequest
from app.services.chat_service import ChatService
from app.services.media_service import MediaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

import re

def format_chat_response(response_text: str, extra_fields: dict = None):
    """funxtion summary and flow in very short  """
    """
    Parses the Markdown response from the AI, extracts any image URLs, 
    and structures the JSON for the frontend.
    """
    # Regex to match Markdown images: ![alt](url)
    pattern = r'!\[.*?\]\((.*?)\)'
    urls = re.findall(pattern, response_text)
    
    # Clean up the text by removing the image markdown (so it can be used as a clean caption)
    clean_text = re.sub(pattern, '', response_text).strip()
    # Clean up any excessive newlines left behind
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    
    response_data = {
        "reply": clean_text,
        "has_image": len(urls) > 0,
        "image_urls": urls,
        "first_image_url": urls[0] if urls else None
    }
    
    # Merge any extra fields (like transcripts)
    if extra_fields:
        response_data.update(extra_fields)
        
    return response_data

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """funxtion summary and flow in very short  """
    """
    Standard HTTP endpoint for chat. Used by web frontends.
    """
    try:
        logger.info(f"Received chat request for session {request.session_id}")
        
        # Delegate processing to the ChatService
        response_text = await ChatService.process_standard_chat(request.session_id, request.message)
        
        # Return structured data for frontend
        return format_chat_response(response_text)
        
    except Exception as general_error:
        logger.error(f"Unexpected error in chat_endpoint: {general_error}", exc_info=True)
        return {"reply": "I'm experiencing a temporary technical issue. Please try again in a moment.", "has_image": False}

@router.post("/chat/audio")
async def chat_audio_endpoint(session_id: str = Form(...), file: UploadFile = File(...)):
    """funxtion summary and flow in very short  """
    """
    Endpoint for audio upload chat. 
    It transcribes the spoken audio using Deepgram and passes the text to our AI assistant.
    """
    try:
        logger.info(f"Received audio chat request for session {session_id}")
        
        audio_bytes = await file.read()
        transcript = await MediaService.process_audio_deepgram(audio_bytes)
        
        if not transcript:
            return {"reply": "Sorry, I couldn't understand the audio. Please try speaking clearly or typing instead.", "has_image": False}
            
        modified_message = (
            f"Transcribed Audio: {transcript}\n\n"
            f"User is looking for product name recovered from this text."
        )
        
        response_text = await ChatService.process_standard_chat(session_id, modified_message)
        
        return format_chat_response(response_text, {"transcript": transcript})
        
    except Exception as general_error:
        logger.error(f"Unexpected error in chat_audio_endpoint: {general_error}", exc_info=True)
        return {"reply": "I'm experiencing a temporary technical issue with audio processing. Please try again.", "has_image": False}


@router.post("/chat/image")
async def chat_image_endpoint(session_id: str = Form(...), file: UploadFile = File(...)):
    """funxtion summary and flow in very short  """
    """
    Endpoint for image upload chat. 
    It looks at the image using Azure OpenAI, extracts any text/product names, and asks the AI about it.
    """
    try:
        logger.info(f"Received image chat request for session {session_id}")
        
        image_bytes = await file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        extracted_text = await MediaService.process_image_vision(image_base64)
        
        if not extracted_text:
            return {"reply": "Sorry, I couldn't extract any text from that image. Make sure it's clear and well-lit.", "has_image": False}
            
        modified_message = (
            f"Text extracted from image: {extracted_text}\n\n"
            f"User is looking for product name recovered from this text."
        )
        
        response_text = await ChatService.process_standard_chat(session_id, modified_message)
        
        return format_chat_response(response_text, {"extracted_text": extracted_text})
        
    except Exception as general_error:
        logger.error(f"Unexpected error in chat_image_endpoint: {general_error}", exc_info=True)
        return {"reply": "I'm experiencing a temporary technical issue with image processing. Please try again.", "has_image": False}
