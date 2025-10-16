"""Analytics API routes"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging

from ..core.analytics import AnalyticsService
from ..api.auth import get_spotify_token
from ..utils.exceptions import SpotifyAPIError

logger = logging.getLogger(__name__)
router = APIRouter()

def get_analytics_service():
    return AnalyticsService()

@router.get("/analytics")
async def get_analytics(token: str = Depends(get_spotify_token)) -> Dict[str, Any]:
    """Get user analytics data"""
    try:
        analytics_service = get_analytics_service()
        analytics = await analytics_service.get_user_analytics(token)
        return analytics
        
    except SpotifyAPIError as e:
        logger.error(f"Analytics generation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate analytics")

@router.get("/playlists")
async def get_user_playlists(token: str = Depends(get_spotify_token)) -> Dict[str, Any]:
    """Get user playlists"""
    try:
        analytics_service = get_analytics_service()
        playlists = await analytics_service.get_user_playlists(token)
        return playlists
        
    except Exception as e:
        logger.error(f"Failed to get playlists: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch playlists")

@router.get("/album-covers")
async def get_album_covers(token: str = Depends(get_spotify_token)) -> Dict[str, List[str]]:
    """Get album cover URLs for background"""
    try:
        analytics_service = get_analytics_service()
        covers = await analytics_service.get_album_covers(token)
        return {"urls": covers}
        
    except Exception as e:
        logger.error(f"Failed to get album covers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch album covers")

@router.get("/my-playlists")
async def get_my_playlists(token: str = Depends(get_spotify_token)) -> Dict[str, Any]:
    """Get user's playlists (alias for /playlists)"""
    try:
        analytics_service = get_analytics_service()
        playlists = await analytics_service.get_user_playlists(token)
        return playlists
        
    except Exception as e:
        logger.error(f"Failed to get playlists: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch playlists")

@router.get("/top-tracks")
async def get_top_tracks(token: str = Depends(get_spotify_token)) -> Dict[str, Any]:
    """Get user's top tracks"""
    try:
        from ..core.spotify import SpotifyService
        spotify_service = SpotifyService()
        top_tracks = spotify_service.get_user_top_tracks(token, limit=20)
        
        return {
            "tracks": top_tracks,
            "total": len(top_tracks)
        }
        
    except Exception as e:
        logger.error(f"Failed to get top tracks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch top tracks")
