"""Analytics API routes"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
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
