"""Track-related data models"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class Track(BaseModel):
    id: str
    name: str
    artists: List[Dict[str, str]]
    album: Dict[str, Any]
    duration_ms: int = 0
    preview_url: Optional[str] = None
    external_urls: Dict[str, str] = {}
    album_image: Optional[str] = None
    images: Optional[List[Dict[str, str]]] = None

class TrackFeatures(BaseModel):
    track_id: str
    danceability: float
    energy: float
    valence: float
    acousticness: float
    instrumentalness: float
