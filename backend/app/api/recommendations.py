"""Recommendations API routes"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging

from ..core.spotify import SpotifyService
from ..core.ai_models import AIService
from ..core.recommendations import RecommendationEngine
from ..api.auth import get_spotify_token
from ..utils.exceptions import SpotifyAPIError, AIAPIError

logger = logging.getLogger(__name__)
router = APIRouter()

def get_recommendation_engine():
    spotify_service = SpotifyService()
    ai_service = AIService()
    return RecommendationEngine(spotify_service, ai_service)

@router.post("/recommend-v2")
async def get_recommendations(
    query: str,
    token: str = Depends(get_spotify_token)
) -> Dict[str, Any]:
    """Get AI-powered music recommendations"""
    try:
        recommendation_engine = get_recommendation_engine()
        recommendations = await recommendation_engine.generate_recommendations(
            query=query,
            access_token=token
        )
        return recommendations
        
    except SpotifyAPIError as e:
        logger.error(f"Spotify API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except AIAPIError as e:
        logger.error(f"AI API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

@router.get("/api/album-covers")
async def get_album_covers(token: str = Depends(get_spotify_token)) -> List[str]:
    """Get user's album covers for background"""
    try:
        recommendation_engine = get_recommendation_engine()
        covers = await recommendation_engine.get_user_album_covers(token)
        return covers
        
    except Exception as e:
        logger.error(f"Failed to get album covers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch album covers")
