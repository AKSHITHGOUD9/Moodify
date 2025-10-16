"""Authentication API routes"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import secrets
import logging

from ..config import settings
from ..core.spotify import SpotifyService
from ..utils.exceptions import AuthenticationError

logger = logging.getLogger(__name__)
router = APIRouter()

def get_spotify_service():
    return SpotifyService()

def get_spotify_token(request: Request) -> str:
    """Extract Spotify token from request"""
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Spotify token required")
    return token

@router.get("/login")
@router.head("/login")
async def login():
    """Initiate Spotify OAuth login"""
    try:
        spotify_service = get_spotify_service()
        state = secrets.token_urlsafe(32)
        auth_url = spotify_service.oauth.get_authorize_url(state=state)
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Login initiation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate login")

@router.get("/callback")
async def callback(request: Request):
    """Handle Spotify OAuth callback"""
    try:
        logger.info(f"Callback received: {request.url}")
        spotify_service = get_spotify_service()
        code = request.query_params.get("code")
        logger.info(f"Authorization code: {code[:10] if code else 'None'}...")
        
        if not code:
            logger.error("No authorization code received")
            raise HTTPException(status_code=400, detail="Authorization code missing")
        
        logger.info("Exchanging code for token...")
        token_info = spotify_service.oauth.get_access_token(code)
        access_token = token_info['access_token']
        logger.info(f"Token received: {access_token[:10]}...")
        
        redirect_url = f"{settings.POST_LOGIN_REDIRECT}?token={access_token}"
        logger.info(f"Redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Authentication failed")

@router.get("/me")
async def get_current_user(token: str = Depends(get_spotify_token)):
    """Get current user information"""
    try:
        spotify_service = get_spotify_service()
        user = spotify_service.get_user_profile(token)
        return user
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(status_code=401, detail="Invalid token or user not found")

@router.post("/logout")
async def logout(request: Request):
    """Logout user and clear session"""
    try:
        request.session.clear()
        
        from ..utils.cache import user_profile_cache, album_covers_cache
        user_profile_cache.clear()
        album_covers_cache.clear()
        
        logger.info("User logged out successfully - all caches cleared")
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")
