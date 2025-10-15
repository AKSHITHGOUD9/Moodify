"""User-related data models"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class User(BaseModel):
    id: str
    display_name: str
    email: str
    country: str
    followers: int
    images: List[Dict[str, str]]

class UserProfile(BaseModel):
    user_id: str
    top_artists: List[str]
    top_genres: List[str]
    total_tracks: int
    cache_timestamp: float
