"""Playlist-related data models"""

from typing import List, Optional
from pydantic import BaseModel

class PlaylistRequest(BaseModel):
    name: str
    track_ids: List[str]
    user_id: str

class Playlist(BaseModel):
    id: str
    name: str
    tracks_added: int
    external_urls: dict
