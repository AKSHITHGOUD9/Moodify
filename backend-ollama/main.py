"""
Moodify Backend - Local LLM Version (Ollama)
===========================================

AI-Powered Music Discovery Platform using local Ollama LLM.
This version uses Ollama running locally for AI-powered recommendations.

Features:
- Spotify OAuth authentication
- Local Ollama LLM integration (llama3.2:3b)
- Music history analysis
- Intelligent track selection
- Spotify recommendations

Author: Moodify Development Team
Version: 1.0.0
"""

# =============================================================================
# IMPORTS
# =============================================================================

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

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Spotify API configuration
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/callback")

# Security configuration
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_urlsafe(32))

# CORS configuration
FRONTEND_URLS = os.getenv("FRONTEND_URLS", "http://127.0.0.1:5173").split(",")
POST_LOGIN_REDIRECT = os.getenv("POST_LOGIN_REDIRECT", "http://127.0.0.1:5173/")

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

# Initialize FastAPI app
app = FastAPI(
    title="Moodify API - Local LLM",
    description="AI-Powered Music Discovery Platform with Local Ollama LLM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=60 * 60 * 24 * 7,  # 7 days
    https_only=False,
    same_site="lax"
)

# =============================================================================
# SPOTIFY INTEGRATION
# =============================================================================

def get_spotify_oauth():
    """Get Spotify OAuth configuration"""
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-read-private user-read-email user-top-read user-read-recently-played playlist-read-private playlist-modify-public playlist-modify-private user-read-playback-state user-modify-playback-state user-read-playback-position user-library-read"
    )

async def _ensure_token(request: Request):
    """Ensure we have a valid Spotify token"""
    session = request.session
    
    if "spotify_token_info" in session:
        token_info = session["spotify_token_info"]
        
        # Check if token is expired
        if time.time() > token_info.get("expires_at", 0):
            try:
                oauth = get_spotify_oauth()
                token_info = oauth.refresh_access_token(token_info["refresh_token"])
                session["spotify_token_info"] = token_info
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                return None
        
        return spotipy.Spotify(auth=token_info["access_token"])
    
    return None

# =============================================================================
# LLM INTEGRATION (Ollama)
# =============================================================================

async def query_ollama_for_history_selection(query: str, music_history: List[Dict]) -> List[str]:
    """
    Use local Ollama LLM to select 10 songs from user's history that match the query
    """
    try:
        # Prepare diverse music history for the LLM
        diverse_history = music_history[:25]  # Limit to 25 tracks for efficiency
        
        # Create history text for LLM
        history_text = "\n".join([
            f"ID: {track['id']}, Name: {track['name']}, Artists: {', '.join(track['artists'])}, Album: {track['album']}"
            for track in diverse_history
        ])
        
        # Create prompt for Ollama
        prompt = f"""Select exactly 10 songs from the user's music history that best match this query: "{query}"

MATCHING CRITERIA:
1. Language match (if query mentions specific language)
2. Genre match (pop, rock, classical, etc.)
3. Mood match (happy, sad, energetic, etc.)
4. Era match (old, new, 80s, 90s, etc.)
5. Artist name match
6. Song title relevance

USER'S MUSIC HISTORY:
{history_text}

INSTRUCTIONS:
- Analyze the query and find the most relevant songs
- Prioritize songs that match multiple criteria
- If query mentions "hindi" or "bollywood", prioritize Hindi songs
- If query mentions "telugu", prioritize Telugu songs
- If query mentions "old", prioritize older songs
- Return exactly 10 track IDs in JSON format

RESPONSE FORMAT (JSON only, no other text):
["id1","id2","id3","id4","id5","id6","id7","id8","id9","id10"]"""
        
        # Call Ollama
        ollama_url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3.2:3b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_ctx": 8192,
                "num_predict": 500
            }
        }
        
        response = requests.post(ollama_url, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        llm_response = result.get('response', '').strip()
        
        # Parse the JSON response
        try:
            cleaned_response = llm_response.replace('```json', '').replace('```', '').strip()
            json_start = cleaned_response.find('[')
            json_end = cleaned_response.rfind(']') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = cleaned_response[json_start:json_end]
                selected_ids = json.loads(json_str)
                
                # Validate track IDs
                if isinstance(selected_ids, list) and len(selected_ids) > 0:
                    valid_ids = [id for id in selected_ids if isinstance(id, str) and len(id) == 22]
                    
                    if len(valid_ids) >= 5:
                        logger.info(f"Ollama selected {len(valid_ids)} valid track IDs from history")
                        return valid_ids[:10]
                    else:
                        logger.warning(f"Ollama returned only {len(valid_ids)} valid IDs")
                        return [track['id'] for track in music_history[:10]]
                else:
                    raise ValueError("Invalid JSON array format")
            else:
                raise ValueError("No JSON array found in LLM response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Ollama response: {e}")
            logger.error(f"Ollama response: {llm_response}")
            return [track['id'] for track in music_history[:10]]
            
    except Exception as e:
        logger.error(f"Error querying Ollama: {e}")
        return [track['id'] for track in music_history[:10]]

# =============================================================================
# MUSIC DATA FUNCTIONS
# =============================================================================

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
        
        # Remove duplicates
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
        recommendations = await asyncio.to_thread(
            sp.recommendations,
            seed_tracks=seed_track_ids[:5],  # Spotify allows max 5 seed tracks
            limit=20,
            market='US'
        )
        
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

async def get_fallback_recommendations(sp, query: str) -> List[Dict]:
    """Get recommendations for new users with no music history using search-based approach"""
    try:
        logger.info(f"Getting fallback recommendations for query: {query}")
        
        # Use search-based recommendations instead of Spotify's recommendation API
        logger.info("Using search-based fallback recommendations")
        new_tracks = await get_search_based_recommendations(sp, query)
        
        if new_tracks:
            logger.info(f"Generated {len(new_tracks)} search-based recommendations")
            return new_tracks
        else:
            # Fallback to generic popular tracks
            logger.info("Using generic popular tracks as final fallback")
            return await get_generic_popular_tracks(sp)
        
    except Exception as e:
        logger.error(f"Error getting fallback recommendations: {e}")
        return []

async def get_search_based_recommendations(sp, query: str) -> List[Dict]:
    """Get recommendations using search-based approach instead of Spotify's recommendation API"""
    try:
        logger.info(f"Searching for tracks matching query: {query}")
        
        # Search for tracks based on the query
        search_results = await asyncio.to_thread(
            sp.search,
            q=query,
            type="track",
            limit=20,
            market='US'
        )
        
        new_tracks = []
        if search_results and 'tracks' in search_results and 'items' in search_results['tracks']:
            for track in search_results['tracks']['items']:
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
        
        logger.info(f"Found {len(new_tracks)} tracks from search")
        return new_tracks
        
    except Exception as e:
        logger.error(f"Error getting search-based recommendations: {e}")
        return []

async def get_generic_popular_tracks(sp) -> List[Dict]:
    """Get generic popular tracks as final fallback"""
    try:
        logger.info("Getting generic popular tracks as final fallback")
        
        # Search for very popular artists
        popular_artists = ["Ed Sheeran", "Taylor Swift", "The Weeknd", "Ariana Grande", "Drake"]
        all_tracks = []
        
        for artist in popular_artists:
            try:
                search_results = await asyncio.to_thread(
                    sp.search,
                    q=f"artist:{artist}",
                    type="track",
                    limit=4,
                    market='US'
                )
                
                if search_results and 'tracks' in search_results and 'items' in search_results['tracks']:
                    for track in search_results['tracks']['items']:
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
                            
                            all_tracks.append(track_data)
                            
                        if len(all_tracks) >= 20:
                            break
                            
                if len(all_tracks) >= 20:
                    break
                    
            except Exception as e:
                logger.warning(f"Could not search for artist {artist}: {e}")
                continue
        
        logger.info(f"Found {len(all_tracks)} generic popular tracks")
        return all_tracks[:20]  # Return max 20 tracks
        
    except Exception as e:
        logger.error(f"Error getting generic popular tracks: {e}")
        return []

async def get_fallback_seed_tracks(query: str) -> List[str]:
    """Get seed tracks based on query analysis for new users"""
    try:
        query_lower = query.lower()
        
        # Define popular tracks for different categories
        fallback_tracks = {
            'hindi': [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Popular Hindi song
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another popular Hindi song
            ],
            'telugu': [
                '5X4FZ9DpLhPcWqME6bT8et',  # Popular Telugu song
                '2Qd7ZE9kFfGj9V9Lv03XzU',  # Another popular Telugu song
            ],
            'english': [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Popular English song
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another popular English song
            ],
            'sad': [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Popular sad song
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another popular sad song
            ],
            'happy': [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Popular happy song
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another popular happy song
            ],
            'party': [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Popular party song
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another popular party song
            ]
        }
        
        # Find matching category
        for category, tracks in fallback_tracks.items():
            if category in query_lower:
                return tracks
        
        # Default to popular English tracks
        return fallback_tracks['english']
        
    except Exception as e:
        logger.error(f"Error getting fallback seed tracks: {e}")
        return []

async def get_trending_tracks(sp) -> List[str]:
    """Get trending/popular tracks as fallback seeds"""
    try:
        trending_ids = []
        
        # Strategy 1: Get new releases
        try:
            new_releases = await asyncio.to_thread(sp.new_releases, limit=10)
            if new_releases and 'albums' in new_releases:
                for album in new_releases['albums']['items']:
                    if album.get('tracks', {}).get('items'):
                        # Get first track from each album
                        track = album['tracks']['items'][0]
                        if track.get('id'):
                            trending_ids.append(track['id'])
        except Exception as e:
            logger.warning(f"Could not get new releases: {e}")
        
        # Strategy 2: Get featured playlists if new releases failed
        if not trending_ids:
            try:
                featured_playlists = await asyncio.to_thread(sp.featured_playlists, limit=5)
                if featured_playlists and 'playlists' in featured_playlists:
                    for playlist in featured_playlists['playlists']['items']:
                        if playlist.get('id'):
                            # Get tracks from featured playlist
                            playlist_tracks = await asyncio.to_thread(sp.playlist_tracks, playlist['id'], limit=5)
                            if playlist_tracks and 'items' in playlist_tracks:
                                for item in playlist_tracks['items']:
                                    if item.get('track') and item['track'].get('id'):
                                        trending_ids.append(item['track']['id'])
                                        if len(trending_ids) >= 5:
                                            break
                        if len(trending_ids) >= 5:
                            break
            except Exception as e:
                logger.warning(f"Could not get featured playlists: {e}")
        
        # Strategy 3: Use very popular tracks as last resort
        if not trending_ids:
            logger.info("Using hardcoded popular tracks as last resort")
            trending_ids = [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Very popular track
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another very popular track
                '1rqqCSm0Qe4I9rUvXuYlaT',  # Another very popular track
            ]
        
        logger.info(f"Found {len(trending_ids)} trending tracks")
        return trending_ids[:5]  # Return max 5 trending tracks
        
    except Exception as e:
        logger.error(f"Error getting trending tracks: {e}")
        return []

async def get_user_listening_profile(sp) -> Dict:
    """Analyze user's listening profile to understand their preferences"""
    try:
        # Get user's top tracks and artists
        top_tracks = await asyncio.to_thread(sp.current_user_top_tracks, limit=30, time_range='short_term')
        top_artists = await asyncio.to_thread(sp.current_user_top_artists, limit=15, time_range='short_term')
        
        # Analyze genres from top artists
        genre_counts = {}
        for artist in top_artists['items']:
            for genre in artist['genres']:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        # Get most common genres
        top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Analyze audio features of top tracks
        track_ids = [track['id'] for track in top_tracks['items'] if track['id']]
        
        if track_ids:
            audio_features = await asyncio.to_thread(sp.audio_features, track_ids)
            valid_features = [f for f in audio_features if f]
            
            if valid_features:
                # Calculate average audio features
                feature_sums = {
                    'energy': sum(f['energy'] for f in valid_features),
                    'tempo': sum(f['tempo'] for f in valid_features),
                    'valence': sum(f['valence'] for f in valid_features),
                    'danceability': sum(f['danceability'] for f in valid_features)
                }
                
                count = len(valid_features)
                avg_features = {k: v / count for k, v in feature_sums.items()}
            else:
                avg_features = {}
        else:
            avg_features = {}
        
        return {
            "top_genres": [genre for genre, count in top_genres],
            "genre_counts": dict(top_genres),
            "avg_audio_features": avg_features,
            "total_tracks_analyzed": len(track_ids)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing user profile: {e}")
        return {}

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Moodify API - Local LLM Version", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "llm": "ollama"}

@app.get("/login")
async def login():
    """Initiate Spotify OAuth login"""
    try:
        auth_manager = get_spotify_oauth()
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
        
        auth_manager = get_spotify_oauth()
        token_info = auth_manager.get_access_token(code)
        
        if not token_info:
            logger.error("Failed to get access token")
            return RedirectResponse(url=f"{POST_LOGIN_REDIRECT}?error=token_failed")
        
        # Store token in session
        request.session["spotify_token_info"] = token_info
        
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

@app.get("/me")
async def get_user(request: Request):
    """Get current user information"""
    try:
        sp = await _ensure_token(request)
        if not sp:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
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

@app.get("/api/spotify-token")
async def get_spotify_token(request: Request):
    """Get Spotify access token for Web SDK"""
    try:
        sp = await _ensure_token(request)
        if not sp:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get the current token from the session
        session = request.session
        if "spotify_token_info" in session:
            token_info = session["spotify_token_info"]
            return {"access_token": token_info["access_token"]}
        else:
            raise HTTPException(status_code=401, detail="No token found")
    except Exception as e:
        logger.error(f"Error getting Spotify token: {e}")
        raise HTTPException(status_code=500, detail="Failed to get token")

@app.get("/api/top-tracks")
async def get_top_tracks(request: Request):
    """Get user's top tracks for analytics"""
    sp = await _ensure_token(request)
    if not sp:
        return {"error": "Not authenticated"}
    
    try:
        # Get user's top tracks (short term - last 4 weeks)
        top_tracks = await asyncio.to_thread(sp.current_user_top_tracks, limit=20, offset=0, time_range='short_term')
        
        # Get user's top artists
        top_artists = await asyncio.to_thread(sp.current_user_top_artists, limit=10, offset=0, time_range='short_term')
        
        # Get user's recently played
        recent_tracks = await asyncio.to_thread(sp.current_user_recently_played, limit=20)
        
        # Process tracks for analytics
        processed_tracks = []
        for track in top_tracks['items']:
            processed_tracks.append({
                'id': track['id'],
                'name': track['name'],
                'artists': [artist['name'] for artist in track['artists']],
                'album': track['album']['name'],
                'album_image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'external_url': track['external_urls']['spotify'],
                'popularity': track['popularity'],
                'duration_ms': track['duration_ms']
            })
        
        # Process artists for analytics
        processed_artists = []
        for artist in top_artists['items']:
            processed_artists.append({
                'id': artist['id'],
                'name': artist['name'],
                'image': artist['images'][0]['url'] if artist['images'] else None,
                'popularity': artist['popularity'],
                'genres': artist['genres']
            })
        
        # Process recent tracks
        processed_recent = []
        for item in recent_tracks['items']:
            track = item['track']
            processed_recent.append({
                'id': track['id'],
                'name': track['name'],
                'artists': [artist['name'] for artist in track['artists']],
                'album': track['album']['name'],
                'album_image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'played_at': item['played_at']
            })
        
        return {
            "top_tracks": processed_tracks,
            "top_artists": processed_artists,
            "recent_tracks": processed_recent,
            "total_tracks": len(processed_tracks),
            "total_artists": len(processed_artists)
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/user-profile")
async def get_user_profile_analysis(request: Request):
    """Get detailed user profile analysis"""
    sp = await _ensure_token(request)
    if not sp:
        return {"error": "Not authenticated"}
    
    try:
        # Get user's listening profile
        user_profile = await get_user_listening_profile(sp)
        return user_profile
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/my-playlists")
async def get_user_playlists(request: Request):
    """Get user's playlists"""
    sp = await _ensure_token(request)
    if not sp:
        return {"error": "Not authenticated"}
    
    try:
        # Get user's playlists
        playlists = await asyncio.to_thread(sp.current_user_playlists, limit=50)
        
        playlist_list = []
        for playlist in playlists['items']:
            playlist_list.append({
                'id': playlist['id'],
                'name': playlist['name'],
                'url': playlist['external_urls']['spotify'],
                'tracks_count': playlist['tracks']['total'],
                'public': playlist['public'],
                'owner': playlist['owner']['display_name'],
                'image': playlist['images'][0]['url'] if playlist['images'] else None
            })
        
        return {
            "playlists": playlist_list,
            "total": len(playlist_list)
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/album-covers")
async def get_album_covers(request: Request):
    """Get album covers from user's listening history"""
    sp = await _ensure_token(request)
    if not sp:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    try:
        # Get user's top tracks from different time ranges
        album_covers = set()  # Use set to avoid duplicates
        
        # Get top tracks from different time ranges with higher limits
        time_ranges = ['short_term', 'medium_term', 'long_term']
        
        for time_range in time_ranges:
            try:
                top_tracks = await asyncio.to_thread(sp.current_user_top_tracks, time_range=time_range, limit=50)
                for track in top_tracks['items']:
                    if track['album']['images']:
                        album_covers.add(track['album']['images'][0]['url'])
            except Exception as e:
                logger.warning(f"Failed to fetch {time_range} tracks: {e}")
                continue
        
        # Get recent tracks with higher limit
        try:
            recent_tracks = await asyncio.to_thread(sp.current_user_recently_played, limit=50)
            for track in recent_tracks['items']:
                if track['track']['album']['images']:
                    album_covers.add(track['track']['album']['images'][0]['url'])
        except Exception as e:
            logger.warning(f"Failed to fetch recent tracks: {e}")
        
        # Get user's saved albums
        try:
            saved_albums = await asyncio.to_thread(sp.current_user_saved_albums, limit=50)
            for album in saved_albums['items']:
                if album['album']['images']:
                    album_covers.add(album['album']['images'][0]['url'])
        except Exception as e:
            logger.warning(f"Failed to fetch saved albums: {e}")
        
        # Get user's playlists and their tracks
        try:
            playlists = await asyncio.to_thread(sp.current_user_playlists, limit=20)
            for playlist in playlists['items']:
                try:
                    playlist_tracks = await asyncio.to_thread(sp.playlist_tracks, playlist['id'], limit=50)
                    for track in playlist_tracks['items']:
                        if track['track'] and track['track']['album']['images']:
                            album_covers.add(track['track']['album']['images'][0]['url'])
                except Exception as e:
                    logger.warning(f"Failed to fetch tracks from playlist {playlist['name']}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Failed to fetch playlists: {e}")
        
        # If still not enough, get new releases as fallback
        if len(album_covers) < 200:
            try:
                new_releases = await asyncio.to_thread(sp.new_releases, limit=50)
                for album in new_releases['albums']['items']:
                    if album['images']:
                        album_covers.add(album['images'][0]['url'])
            except Exception as e:
                logger.warning(f"Failed to fetch new releases: {e}")
        
        # Convert set to list and shuffle
        album_covers_list = list(album_covers)
        
        # Debug logging
        logger.info(f"Returning {len(album_covers_list)} unique album cover URLs from user's history")
        
        return JSONResponse({"urls": album_covers_list})
        
    except Exception as e:
        logger.error(f"Error fetching album covers: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/create-playlist")
async def create_custom_playlist(request: Request, playlist_data: dict):
    """Create a custom playlist and add it to user's library"""
    sp = await _ensure_token(request)
    if not sp:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get playlist data
        name = playlist_data.get("name", "Moodify Playlist")
        description = playlist_data.get("description", "AI-generated playlist from Moodify")
        track_ids = playlist_data.get("track_ids", [])
        public = playlist_data.get("public", True)
        
        if not track_ids:
            raise HTTPException(status_code=400, detail="No tracks provided")
        
        # Get current user
        user = await asyncio.to_thread(sp.current_user)
        
        # Create the playlist
        playlist = await asyncio.to_thread(
            sp.user_playlist_create,
            user=user['id'],
            name=name,
            public=public,
            description=description
        )
        
        # Add tracks to playlist
        await asyncio.to_thread(sp.playlist_add_items, playlist['id'], track_ids)
        
        # Add playlist to user's library
        await asyncio.to_thread(sp.user_playlist_follow_playlist, user['id'], playlist['id'])
        
        # Get playlist details
        playlist_details = await asyncio.to_thread(sp.playlist, playlist['id'])
        
        return {
            "success": True,
            "playlist": {
                'id': playlist['id'],
                'name': playlist['name'],
                'url': playlist['external_urls']['spotify'],
                'tracks_added': len(track_ids),
                'description': description,
                'public': public,
                'owner': user['display_name'],
                'total_tracks': playlist_details['tracks']['total']
            },
            "message": f"Playlist '{name}' created successfully with {len(track_ids)} tracks!"
        }
        
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        return {"error": str(e), "success": False}

@app.post("/recommend")
async def recommend_tracks(request: Request, query: dict):
    """Original recommendation endpoint for backward compatibility"""
    try:
        user_query = query.get("query", "").strip()
        if not user_query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        sp = await _ensure_token(request)
        if not sp:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Use the same logic as recommend-v2 but return in old format
        music_history = await get_user_music_history(sp)
        
        # Handle new users with no music history
        if not music_history:
            logger.info("No music history found, using fallback recommendations")
            new_recommendations = await get_fallback_recommendations(sp, user_query)
        else:
            selected_track_ids = await query_ollama_for_history_selection(user_query, music_history)
            new_recommendations = await get_spotify_recommendations(sp, selected_track_ids, user_query)
        
        return {
            "query": user_query,
            "tracks": new_recommendations,
            "total_tracks": len(new_recommendations),
            "method": "Ollama LLM + Spotify Seeds"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")

@app.post("/recommend-v2")
async def get_recommendations_v2(request: Request, data: dict):
    """Get AI-powered music recommendations using local Ollama LLM"""
    try:
        user_query = data.get("query", "").strip()
        if not user_query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        sp = await _ensure_token(request)
        if not sp:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Step 1: Get user's music history
        music_history = await get_user_music_history(sp)
        if not music_history:
            raise HTTPException(status_code=400, detail="No music history found")
        
        # Step 2: Use Ollama LLM to select 10 songs from history
        selected_track_ids = await query_ollama_for_history_selection(user_query, music_history)
        
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
            "method": "Ollama LLM + Spotify Seeds"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")

# =============================================================================
# STATIC FILE SERVING (Production)
# =============================================================================

# Serve static files in production (frontend build)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Serve the frontend app for all non-API routes (MUST BE LAST)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React frontend for all non-API routes"""
        # Serve index.html for all other routes (SPA routing)
        if os.path.exists("static/index.html"):
            from fastapi.responses import FileResponse
            return FileResponse("static/index.html")
        else:
            raise HTTPException(status_code=404, detail="Frontend not built")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
