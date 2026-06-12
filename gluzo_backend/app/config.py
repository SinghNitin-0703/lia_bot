from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application identity
    PROJECT_NAME: str = "Gluzo AI E-Commerce"
    
    # External API keys. These are set to None by default so we can check
    # if they are missing at runtime, rather than hardcoding fake keys.
    OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    # API Key for external product data searches
    TAVILY_API_KEY: Optional[str] = None
    
    # API Key for audio-to-text transcription (multilanguage)
    DEEPGRAM_API_KEY: Optional[str] = None
    
    # API Key and Endpoint for Azure Mistral (Image-to-text extraction)
    AZURE_MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_ENDPOINT: str = "https://mistral-document-ai-2512.eastus2.models.ai.azure.com/v1/chat/completions"
    

    
    
    # Base URL for the API server (used for constructing image URLs)
    # Change this to your public domain when deploying (e.g. "https://yourdomain.com")
    BASE_URL: str = "http://localhost:8000"
    
    # Database and Cache configurations
    REDIS_URL: str = "redis://localhost:6379"
    
    # Path pointer to our local dataset
    CSV_FILE_PATH: str = "data/products.csv"
    
    class Config:
        # Instructs Pydantic to read variables from a .env file if present
        env_file = ".env"
        extra = "ignore"

# Create a singleton instance of the settings to be imported across the app
settings = Settings()
