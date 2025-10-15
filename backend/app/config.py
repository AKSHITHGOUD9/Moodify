"""Application configuration and environment settings"""

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Spotify Configuration
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
    SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
    POST_LOGIN_REDIRECT = os.getenv("POST_LOGIN_REDIRECT")
    
    # AI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    HUGGINGFACE_API_KEY = os.getenv("HUGGING_FACE_KEYS")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEYS")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # Server Configuration
    PORT = int(os.getenv("PORT", 8000))
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # CORS Settings
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://moodify-ai-powered.vercel.app",
        "https://moodify.akshithmothkuri.com"
    ]

settings = Settings()
