"""Playlist management API routes"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from ..core.spotify import SpotifyService
from ..api.auth import get_spotify_token
from ..models.playlist import PlaylistRequest, Playlist
from ..utils.exceptions import SpotifyAPIError

logger = logging.getLogger(__name__)
router = APIRouter()

def get_spotify_service():
    return SpotifyService()

@router.post("/create-playlist")
async def create_playlist(
    playlist_request: PlaylistRequest,
    token: str = Depends(get_spotify_token)
) -> Playlist:
    """Create a new playlist"""
    try:
        spotify_service = get_spotify_service()
        user = spotify_service.get_user_profile(token)
        user_id = user['id']
        
        playlist_data = spotify_service.create_playlist(
            access_token=token,
            user_id=user_id,
            name=playlist_request.name,
            track_ids=playlist_request.track_ids
        )
        
        return Playlist(**playlist_data)
        
    except SpotifyAPIError as e:
        logger.error(f"Playlist creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Playlist creation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create playlist")
