import logging
import httpx
from app.config import settings

# Set up logging so we can track errors or important events in the console
logger = logging.getLogger(__name__)

class MediaService:
    """
    This service handles all media (audio and image) processing tasks.
    It acts as a bridge between our app and external AI services like Deepgram and Mistral.
    """

    @staticmethod
    async def process_audio_deepgram(audio_bytes: bytes) -> str:
        """
        Takes raw audio data and converts it into text using Deepgram's AI.
        It supports multiple languages automatically.
        """
        
        # 1. Check if we have the secret key needed to talk to Deepgram
        if not settings.DEEPGRAM_API_KEY:
            raise ValueError("Deepgram API key is missing. Please add it to your .env file.")
            
        # 2. Prepare the destination URL
        # We use the 'nova-2' model because it's fast and accurate.
        # 'detect_language=true' tells Deepgram to figure out the language on its own.
        url = "https://api.deepgram.com/v1/listen?model=nova-2&detect_language=true"
        
        # 3. Set up the headers (like putting a stamp and return address on a letter)
        headers = {
            "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
            "Content-Type": "audio/mp3" 
        }
        
        # 4. Make the actual request to Deepgram over the internet
        async with httpx.AsyncClient(timeout=60.0) as client:
            
            # Send the audio data
            response = await client.post(url, headers=headers, content=audio_bytes)
            
            # 5. Check if the request was successful (HTTP status 200 means OK)
            if response.status_code != 200:
                logger.error(f"Deepgram failed with error: {response.text}")
                raise Exception("Failed to transcribe audio using Deepgram.")
                
            # 6. Extract the text from Deepgram's response
            data = response.json()
            
            try:
                # Deepgram buries the transcript deep inside its JSON response, 
                # so we drill down to find exactly what we need.
                transcript = data['results']['channels'][0]['alternatives'][0]['transcript']
                return transcript
                
            except KeyError:
                # If something went wrong and the path above doesn't exist, return empty text
                return ""


    @staticmethod
    async def process_image_mistral(image_base64: str) -> str:
        """
        Takes a base64-encoded image (text representation of an image) 
        and extracts text/product names using Azure OpenAI Vision.
        """
        
        # 1. Check if we have the secret key needed
        if not settings.AZURE_OPENAI_API_KEY:
            raise ValueError("Azure OpenAI API key is missing. Please add it to your .env file.")
            
        # 2. Get the Azure OpenAI URL for gpt-4.1-mini-2
        endpoint = f"{settings.AZURE_OPENAI_ENDPOINT}openai/deployments/gpt-4.1-mini-2/chat/completions?api-version=2024-02-15-preview"
        
        # 3. Set up the headers with our authentication token
        headers = {
            "api-key": settings.AZURE_OPENAI_API_KEY,
            "Content-Type": "application/json"
        }
        
        # 4. Prepare the instructions for Vision model
        # We tell it what to do, and give it the image data
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Extract all text from this image. If you find a product name, specify it clearly."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }
        
        # 5. Make the request to Azure
        async with httpx.AsyncClient(timeout=60.0) as client:
            
            # Send the payload
            response = await client.post(endpoint, headers=headers, json=payload)
            
            # 6. Check for success
            if response.status_code != 200:
                logger.error(f"Image processing failed with error: {response.text}")
                raise Exception("Failed to process image using AI Vision.")
                
            # 7. Extract the answer from the AI's response
            data = response.json()
            
            try:
                # Drill down into the JSON to get the actual text message
                extracted_text = data['choices'][0]['message']['content']
                return extracted_text
                
            except (KeyError, IndexError):
                # Return empty text if we couldn't find the expected data
                return ""
