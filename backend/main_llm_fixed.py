"""
Moodify Backend API - LLM Integration Fixed
==========================================

This version has the LLM integration properly configured for cloud deployment.
Uses cloud LLM providers (OpenAI, Anthropic) with intelligent fallback.

Author: Moodify Development Team
Version: 1.0.0
"""

# Standard library imports
import os
import secrets
import time
import asyncio
import json
import re
import logging
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode
from functools import lru_cache

# Third-party imports
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from dotenv import load_dotenv

# FastAPI and middleware imports
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# Load environment variables
load_dotenv()

# =============================================================================
# CONFIGURATION AND INITIALIZATION
# =============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Spotify API configuration
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/callback")

# Security configuration
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_urlsafe(32))

# CORS configuration
FRONTEND_URLS = os.getenv("FRONTEND_URLS", "http://localhost:5173").split(",")
POST_LOGIN_REDIRECT = os.getenv("POST_LOGIN_REDIRECT", "http://localhost:5173/")

# Initialize FastAPI app
app = FastAPI(
    title="Moodify API",
    description="AI-Powered Music Discovery Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for secure session management
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=60 * 60 * 24 * 7,  # 7 days
    https_only=False,  # Set to True in production
    same_site="lax"
)

# =============================================================================
# STATIC FILE SERVING (Production)
# =============================================================================

# Serve static files in production (frontend build)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Serve the frontend app for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React frontend for all non-API routes"""
        # Don't serve frontend for API routes
        if full_path.startswith(("api/", "login", "callback", "logout", "docs", "redoc", "openapi.json")):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Serve index.html for all other routes (SPA routing)
        if os.path.exists("static/index.html"):
            from fastapi.responses import FileResponse
            return FileResponse("static/index.html")
        else:
            raise HTTPException(status_code=404, detail="Frontend not built")

# =============================================================================
# LLM INTEGRATION
# =============================================================================

async def query_llm_for_history_selection(query: str, music_history: List[Dict]) -> List[str]:
    """
    Use cloud LLM or fallback to select 10 songs from user's history that match the query
    """
    try:
        # Try cloud LLM first
        try:
            from llm_cloud import get_llm_client
            llm_client = get_llm_client()
            return await llm_client.select_tracks(query, music_history)
        except Exception as e:
            logger.warning(f"Cloud LLM not available: {e}, using fallback")
            from llm_fallback import select_tracks_fallback
            return select_tracks_fallback(query, music_history)
    except Exception as e:
        logger.error(f"Error in LLM selection: {e}")
        # Last resort: return first 10 tracks
        return [track['id'] for track in music_history[:10] if track.get('id')]

# =============================================================================
# SPOTIFY INTEGRATION
# =============================================================================

def get_spotify_client(request: Request):
    """Get Spotify client with user's access token"""
    access_token = request.session.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return spotipy.Spotify(auth=access_token)

async def get_user_music_history(sp) -> List[Dict]:
    """Get comprehensive user music history for LLM analysis"""
    try:
        music_history = []
        
        # Get top tracks from different time ranges
        time_ranges = ["short_term", "medium_term", "long_term"]
        for time_range in time_ranges:
            try:
                top_tracks = await asyncio.to_thread(sp.current_user_top_tracks, limit=20, time_range=time_range)
                if top_tracks and 'items' in top_tracks:
                    for track in top_tracks['items']:
                        if track and track.get('id'):
                            track_data = {
                                'id': track['id'],
                                'name': track['name'],
                                'artists': [artist['name'] for artist in track.get('artists', [])],
                                'album': track.get('album', {}).get('name', 'Unknown Album'),
                                'time_range': time_range,
                                'popularity': track.get('popularity', 0)
                            }
                            music_history.append(track_data)
            except Exception as e:
                logger.warning(f"Failed to get top tracks for {time_range}: {e}")
        
        # Get recently played tracks
        try:
            recent_tracks = await asyncio.to_thread(sp.current_user_recently_played, limit=50)
            if recent_tracks and 'items' in recent_tracks:
                for item in recent_tracks['items']:
                    track = item.get('track')
                    if track and track.get('id'):
                        track_data = {
                            'id': track['id'],
                            'name': track['name'],
                            'artists': [artist['name'] for artist in track.get('artists', [])],
                            'album': track.get('album', {}).get('name', 'Unknown Album'),
                            'time_range': 'recent',
                            'popularity': track.get('popularity', 0)
                        }
                        music_history.append(track_data)
        except Exception as e:
            logger.warning(f"Failed to get recently played tracks: {e}")
        
        # Get saved albums
        try:
            saved_albums = await asyncio.to_thread(sp.current_user_saved_albums, limit=20)
            if saved_albums and 'items' in saved_albums:
                for item in saved_albums['items']:
                    album = item.get('album', {})
                    if album.get('tracks') and album['tracks'].get('items'):
                        for track in album['tracks']['items']:
                            if track and track.get('id'):
                                track_data = {
                                    'id': track['id'],
                                    'name': track['name'],
                                    'artists': [artist['name'] for artist in track.get('artists', [])],
                                    'album': album.get('name', 'Unknown Album'),
                                    'time_range': 'saved_album',
                                    'popularity': track.get('popularity', 0)
                                }
                                music_history.append(track_data)
        except Exception as e:
            logger.warning(f"Failed to get saved albums: {e}")
        
        # Remove duplicates based on track ID
        seen_ids = set()
        unique_history = []
        for track in music_history:
            if track['id'] not in seen_ids:
                seen_ids.add(track['id'])
                unique_history.append(track)
        
        logger.info(f"Collected {len(unique_history)} unique tracks from user history")
        return unique_history
        
    except Exception as e:
        logger.error(f"Error getting user music history: {e}")
        return []

async def get_spotify_recommendations(sp, seed_track_ids: List[str], query: str) -> List[Dict]:
    """Use Spotify's recommendation API with seed tracks to get new recommendations"""
    try:
        # Get recommendations using the seed tracks
        recommendations = await asyncio.to_thread(
            sp.recommendations,
            seed_tracks=seed_track_ids[:5],  # Spotify allows max 5 seed tracks
            limit=20,
            market='US'
        )
        
        # Process the recommendations
        new_tracks = []
        if isinstance(recommendations, dict) and 'tracks' in recommendations:
            for track in recommendations['tracks']:
                if track and track.get('id'):
                    track_data = {
                        'id': track['id'],
                        'name': track['name'],
                        'artists': [artist['name'] for artist in track.get('artists', [])],
                        'album': track.get('album', {}).get('name', 'Unknown Album'),
                        'album_image': None,
                        'external_url': track.get('external_urls', {}).get('spotify'),
                        'preview_url': track.get('preview_url'),
                        'popularity': track.get('popularity', 0)
                    }
                    
                    # Get album image
                    album_images = track.get('album', {}).get('images', [])
                    if album_images:
                        track_data['album_image'] = album_images[0]['url']
                    
                    new_tracks.append(track_data)
        
        logger.info(f"Generated {len(new_tracks)} new recommendations")
        return new_tracks
        
    except Exception as e:
        logger.error(f"Error getting Spotify recommendations: {e}")
        return []

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Moodify API is running!", "version": "1.0.0"}

@app.get("/login")
async def login():
    """Initiate Spotify OAuth login"""
    try:
        auth_manager = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope="user-read-recently-played user-top-read user-library-read playlist-modify-public playlist-modify-private"
        )
        
        auth_url = auth_manager.get_authorize_url()
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        logger.error(f"Error initiating login: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/callback")
async def callback(request: Request, code: str = None, error: str = None):
    """Handle Spotify OAuth callback"""
    try:
        if error:
            logger.error(f"OAuth error: {error}")
            return RedirectResponse(url=f"{POST_LOGIN_REDIRECT}?error={error}")
        
        if not code:
            logger.error("No authorization code received")
            return RedirectResponse(url=f"{POST_LOGIN_REDIRECT}?error=no_code")
        
        auth_manager = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope="user-read-recently-played user-top-read user-library-read playlist-modify-public playlist-modify-private"
        )
        
        token_info = auth_manager.get_access_token(code)
        
        if not token_info:
            logger.error("Failed to get access token")
            return RedirectResponse(url=f"{POST_LOGIN_REDIRECT}?error=token_failed")
        
        # Store token in session
        request.session["access_token"] = token_info["access_token"]
        request.session["refresh_token"] = token_info.get("refresh_token")
        request.session["expires_at"] = time.time() + token_info["expires_in"]
        
        logger.info("User successfully authenticated")
        return RedirectResponse(url=POST_LOGIN_REDIRECT)
        
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        return RedirectResponse(url=f"{POST_LOGIN_REDIRECT}?error=callback_failed")

@app.get("/logout")
async def logout(request: Request):
    """Logout user and clear session"""
    try:
        request.session.clear()
        logger.info("User logged out")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return {"message": "Logout completed"}

@app.get("/api/user")
async def get_user(request: Request):
    """Get current user information"""
    try:
        sp = get_spotify_client(request)
        user = await asyncio.to_thread(sp.current_user)
        return {
            "id": user["id"],
            "display_name": user["display_name"],
            "email": user.get("email"),
            "country": user.get("country"),
            "followers": user.get("followers", {}).get("total", 0),
            "images": user.get("images", [])
        }
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(status_code=401, detail="Not authenticated")

@app.post("/api/recommend-v2")
async def get_recommendations_v2(request: Request, data: dict):
    """Get AI-powered music recommendations using cloud LLM"""
    try:
        user_query = data.get("query", "").strip()
        if not user_query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        sp = get_spotify_client(request)
        
        # Step 1: Get user's music history
        music_history = await get_user_music_history(sp)
        if not music_history:
            raise HTTPException(status_code=400, detail="No music history found")
        
        # Step 2: Use LLM to select 10 songs from history
        selected_track_ids = await query_llm_for_history_selection(user_query, music_history)
        
        if not selected_track_ids:
            raise HTTPException(status_code=500, detail="Failed to select tracks from history")
        
        # Step 3: Get new recommendations using selected tracks as seeds
        new_recommendations = await get_spotify_recommendations(sp, selected_track_ids, user_query)
        
        # Step 4: Get the selected history tracks for display
        history_tracks = []
        for track in music_history:
            if track['id'] in selected_track_ids:
                track_data = {
                    'id': track['id'],
                    'name': track['name'],
                    'artists': track['artists'],
                    'album': track['album'],
                    'album_image': None,
                    'external_url': f"https://open.spotify.com/track/{track['id']}",
                    'preview_url': None,
                    'popularity': track.get('popularity', 0)
                }
                history_tracks.append(track_data)
        
        return {
            "user_history_recs": history_tracks,
            "new_recs": new_recommendations,
            "query": user_query,
            "method": "Cloud LLM + Spotify Seeds"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

