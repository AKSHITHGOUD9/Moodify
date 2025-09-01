import os
import secrets
import time
import asyncio
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode
from functools import lru_cache
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import json
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

@lru_cache(maxsize=128)
def get_cached_genre_seeds():
    """Cache Spotify genre seeds to avoid repeated API calls"""
    try:
        oauth = get_spotify_oauth()
        token = oauth.get_cached_token()
        if token:
            sp = spotipy.Spotify(auth=token["access_token"])
            return sp.recommendation_genre_seeds()['genres']
    except Exception as e:
        logger.warning(f"Failed to cache genre seeds: {e}")
    return ["pop", "rock", "electronic", "hip-hop", "jazz"]

def is_token_expired(token_info: Optional[Dict]) -> bool:
    """Check if Spotify token is expired with improved logic"""
    if not token_info:
        return True
    
    # Check if we have an expiration time
    if "expires_at" in token_info:
        return time.time() > token_info["expires_at"]
    
    # Fallback: assume expired if no expiration info
    return True

app = FastAPI(
    title="Moodify API", 
    version="1.0.0",
    description="AI-Powered Music Discovery Platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ] + (os.getenv("FRONTEND_URLS", "").split(",") if os.getenv("FRONTEND_URLS") else []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware - Same-origin configuration
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "your-secret-key"),
    max_age=60 * 60 * 24 * 7,  # 7 days for development
    https_only=False,  # Set to True in production
    same_site="lax"  # Standard same-site policy
)

# Enhanced genre and mood mapping
GENRE_MAPPINGS = {
    # Metal subgenres
    "metal": ["metal", "heavy metal", "death metal", "black metal", "thrash metal", "power metal"],
    "rock": ["rock", "hard rock", "classic rock", "alternative rock", "indie rock"],
    "electronic": ["electronic", "edm", "dance", "house", "techno", "trance", "dubstep"],
    "hip_hop": ["hip hop", "rap", "trap", "r&b", "soul"],
    "pop": ["pop", "pop rock", "indie pop", "synthpop"],
    "jazz": ["jazz", "smooth jazz", "bebop", "fusion"],
    "classical": ["classical", "orchestral", "symphony"],
    "country": ["country", "folk", "bluegrass"],
    "reggae": ["reggae", "dub", "ska"],
    "punk": ["punk", "hardcore", "emo"],
    "lofi": ["lofi", "chill", "ambient", "study"],
    "workout": ["workout", "gym", "energy", "upbeat"],
    "sad": ["sad", "melancholy", "depressing", "emotional"],
    "happy": ["happy", "upbeat", "cheerful", "positive"],
    "romantic": ["romantic", "love", "intimate", "passionate"],
    "party": ["party", "celebration", "festive", "dance"],
    "focus": ["focus", "concentration", "productivity", "work"],
    "sleep": ["sleep", "relaxing", "calm", "peaceful"],
    "nostalgic": ["nostalgic", "retro", "vintage", "throwback"],
    "energetic": ["energetic", "high energy", "intense", "powerful"]
}

# Audio feature mappings for different moods
AUDIO_FEATURE_MAPPINGS = {
    "metal": {"min_energy": 0.8, "max_energy": 1.0, "min_tempo": 120, "max_tempo": 200, "min_valence": 0.2, "max_valence": 0.6},
    "rock": {"min_energy": 0.7, "max_energy": 0.9, "min_tempo": 100, "max_tempo": 160, "min_valence": 0.3, "max_valence": 0.7},
    "electronic": {"min_energy": 0.6, "max_energy": 0.9, "min_tempo": 120, "max_tempo": 140, "min_valence": 0.4, "max_valence": 0.8},
    "hip_hop": {"min_energy": 0.5, "max_energy": 0.8, "min_tempo": 80, "max_tempo": 120, "min_valence": 0.3, "max_valence": 0.7},
    "pop": {"min_energy": 0.5, "max_energy": 0.8, "min_tempo": 100, "max_tempo": 140, "min_valence": 0.4, "max_valence": 0.8},
    "jazz": {"min_energy": 0.3, "max_energy": 0.6, "min_tempo": 60, "max_tempo": 120, "min_valence": 0.4, "max_valence": 0.7},
    "classical": {"min_energy": 0.2, "max_energy": 0.6, "min_tempo": 60, "max_tempo": 140, "min_valence": 0.3, "max_valence": 0.6},
    "country": {"min_energy": 0.4, "max_energy": 0.7, "min_tempo": 80, "max_tempo": 120, "min_valence": 0.4, "max_valence": 0.7},
    "reggae": {"min_energy": 0.4, "max_energy": 0.6, "min_tempo": 80, "max_tempo": 100, "min_valence": 0.5, "max_valence": 0.8},
    "punk": {"min_energy": 0.8, "max_energy": 1.0, "min_tempo": 140, "max_tempo": 180, "min_valence": 0.3, "max_valence": 0.6},
    "lofi": {"min_energy": 0.2, "max_energy": 0.4, "min_tempo": 60, "max_tempo": 90, "min_valence": 0.3, "max_valence": 0.6},
    "workout": {"min_energy": 0.8, "max_energy": 1.0, "min_tempo": 120, "max_tempo": 160, "min_valence": 0.6, "max_valence": 0.9},
    "sad": {"min_energy": 0.2, "max_energy": 0.4, "min_tempo": 60, "max_tempo": 90, "min_valence": 0.1, "max_valence": 0.3},
    "happy": {"min_energy": 0.6, "max_energy": 0.9, "min_tempo": 100, "max_tempo": 140, "min_valence": 0.7, "max_valence": 1.0},
    "romantic": {"min_energy": 0.3, "max_energy": 0.6, "min_tempo": 70, "max_tempo": 110, "min_valence": 0.4, "max_valence": 0.7},
    "party": {"min_energy": 0.8, "max_energy": 1.0, "min_tempo": 120, "max_tempo": 140, "min_valence": 0.7, "max_valence": 1.0},
    "focus": {"min_energy": 0.4, "max_energy": 0.7, "min_tempo": 80, "max_tempo": 120, "min_valence": 0.4, "max_valence": 0.7},
    "sleep": {"min_energy": 0.1, "max_energy": 0.3, "min_tempo": 50, "max_tempo": 80, "min_valence": 0.2, "max_valence": 0.5},
    "nostalgic": {"min_energy": 0.4, "max_energy": 0.7, "min_tempo": 80, "max_tempo": 120, "min_valence": 0.4, "max_valence": 0.7},
    "energetic": {"min_energy": 0.8, "max_energy": 1.0, "min_tempo": 130, "max_tempo": 180, "min_valence": 0.6, "max_valence": 0.9}
}

@lru_cache(maxsize=256)
def enhanced_mood_analysis(query: str) -> Dict:
    """
    Enhanced mood and genre analysis using natural language processing with caching
    """
    query_lower = query.lower().strip()
    
    # Initialize analysis result
    analysis = {
        "detected_genres": [],
        "detected_moods": [],
        "audio_features": {},
        "confidence": 0.0,
        "analysis_text": ""
    }
    
    # Optimized detection using set operations
    detected_genres = set()
    detected_moods = set()
    
    # More efficient keyword matching
    for genre, keywords in GENRE_MAPPINGS.items():
        if any(keyword in query_lower for keyword in keywords):
            if genre in ["sad", "happy", "romantic", "energetic", "focus", "sleep", "nostalgic"]:
                detected_moods.add(genre)
            else:
                detected_genres.add(genre)
    
    # Convert back to lists
    detected_genres = list(detected_genres)
    detected_moods = list(detected_moods)
    all_detected = detected_genres + detected_moods
    
    # Get audio features for the most relevant genre/mood
    if all_detected:
        primary_style = all_detected[0]
        analysis["audio_features"] = AUDIO_FEATURE_MAPPINGS.get(primary_style, {})
        analysis["detected_genres"] = detected_genres
        analysis["detected_moods"] = detected_moods
        analysis["confidence"] = min(len(all_detected) * 0.25 + 0.1, 1.0)
        
        # Generate analysis text
        genre_text = ", ".join(detected_genres[:3]) if detected_genres else "various genres"
        mood_text = ", ".join(detected_moods[:3]) if detected_moods else "mixed emotions"
        analysis["analysis_text"] = f"Detected {genre_text} with {mood_text} vibes"
    
    return analysis

async def get_user_listening_profile(sp) -> Dict:
    """
    Analyze user's listening profile to understand their preferences with async optimization
    """
    try:
        # Concurrent API calls for better performance
        tasks = [
            asyncio.create_task(asyncio.to_thread(sp.current_user_top_tracks, limit=30, time_range='short_term')),
            asyncio.create_task(asyncio.to_thread(sp.current_user_top_artists, limit=15, time_range='short_term'))
        ]
        
        top_tracks, top_artists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        if isinstance(top_tracks, Exception) or isinstance(top_artists, Exception):
            logger.error(f"Error fetching user data: {top_tracks if isinstance(top_tracks, Exception) else top_artists}")
            return {}
        
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
                # Calculate average audio features more efficiently
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

def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope="user-read-private user-read-email user-top-read user-read-recently-played playlist-read-private playlist-modify-public playlist-modify-private"
    )

async def _ensure_token(request: Request):
    """Ensure we have a valid Spotify token"""
    session = request.session
    print(f"DEBUG: _ensure_token called with session keys: {list(session.keys())}")
    
    if "spotify_token_info" not in session:
        print(f"DEBUG: No spotify_token_info in session")
        return None
    
    token_info = session["spotify_token_info"]
    print(f"DEBUG: Found token_info with keys: {list(token_info.keys())}")
    
    # Check if token is expired
    if is_token_expired(token_info):
        print(f"DEBUG: Token is expired, attempting refresh")
        try:
            oauth = get_spotify_oauth()
            token_info = oauth.refresh_access_token(token_info["refresh_token"])
            session["spotify_token_info"] = token_info
            print(f"DEBUG: Token refreshed successfully")
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
    else:
        print(f"DEBUG: Token is still valid")
    
    return spotipy.Spotify(auth=token_info["access_token"])

@app.get("/")
async def root():
    return {"message": "Moodify API - AI-Powered Music Discovery"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/login")
async def login(request: Request):
    """Start Spotify OAuth flow"""
    oauth = get_spotify_oauth()
    auth_url = oauth.get_authorize_url()
    
    # Store state in session
    state = secrets.token_urlsafe(32)
    session = request.session
    if "oauth_states" not in session:
        session["oauth_states"] = []
    session["oauth_states"].append(state)
    
    # Keep only last 5 states
    session["oauth_states"] = session["oauth_states"][-5:]
    
    return RedirectResponse(auth_url)

@app.get("/callback")
async def callback(request: Request, code: str = None, state: str = None):
    """Handle Spotify OAuth callback"""
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code")
    
    oauth = get_spotify_oauth()
    try:
        token_info = oauth.get_access_token(code)
        session = request.session
        session["spotify_token_info"] = token_info
        
        # Redirect to frontend
        frontend_url = os.getenv("POST_LOGIN_REDIRECT", "http://localhost:5173/")
        return RedirectResponse(frontend_url)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

@app.get("/me")
async def get_user_profile(request: Request):
    """Get current user profile"""
    print(f"DEBUG: /me endpoint called with session: {request.session}")
    print(f"DEBUG: Request headers: {dict(request.headers)}")
    
    sp = await _ensure_token(request)
    if not sp:
        print(f"DEBUG: No valid token found")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = sp.current_user()
        print(f"DEBUG: Successfully got user: {user.get('display_name', 'Unknown')}")
        return user
    except Exception as e:
        print(f"DEBUG: Error getting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommend")
async def recommend_tracks(request: Request, query: Dict, background_tasks: BackgroundTasks):
    """Enhanced AI-powered track recommendations with optimized performance"""
    sp = await _ensure_token(request)
    if not sp:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_query = query.get("query", "").strip()
        create_playlist = query.get("create_playlist", False)
        playlist_name = query.get("playlist_name", "").strip()
        
        if not user_query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Enhanced mood analysis (cached)
        analysis = enhanced_mood_analysis(user_query)
        
        # Get user's listening profile asynchronously
        user_profile = await get_user_listening_profile(sp)
        
        # Combine user preferences with query analysis
        audio_features = analysis["audio_features"].copy()
        
        # Adjust based on user's preferences with improved blending
        if user_profile and "avg_audio_features" in user_profile and user_profile["avg_audio_features"]:
            user_avg = user_profile["avg_audio_features"]
            # Blend user preferences with query (75% query, 25% user preference for better personalization)
            blend_ratio = 0.75
            for feature in ["energy", "tempo", "valence"]:
                if feature in audio_features and feature in user_avg:
                    query_val = audio_features.get(f"min_{feature}", audio_features.get(feature, user_avg[feature]))
                    user_val = user_avg[feature]
                    blended_val = query_val * blend_ratio + user_val * (1 - blend_ratio)
                    
                    # Update both min and max if they exist
                    if f"min_{feature}" in audio_features:
                        audio_features[f"min_{feature}"] = max(0, blended_val - 0.1)
                    if f"max_{feature}" in audio_features:
                        audio_features[f"max_{feature}"] = min(1, blended_val + 0.1)
        
        # Get available genre seeds (cached)
        valid_genres = get_cached_genre_seeds()
        
        # Optimized genre selection
        seed_genres = []
        genre_mapping = {
            "hip_hop": "hip-hop",
            "electronic": "electronic",
            "r&b": "r-n-b"
        }
        
        # Map detected genres to Spotify genres
        for genre in analysis["detected_genres"][:3]:  # Limit to top 3
            spotify_genre = genre_mapping.get(genre, genre)
            if spotify_genre in valid_genres and spotify_genre not in seed_genres:
                seed_genres.append(spotify_genre)
        
        # Fallback to user's top genres
        if len(seed_genres) < 2 and user_profile and "top_genres" in user_profile:
            for genre in user_profile["top_genres"][:3]:
                if genre in valid_genres and genre not in seed_genres and len(seed_genres) < 3:
                    seed_genres.append(genre)
        
        # Final fallback
        if not seed_genres:
            seed_genres = ["pop", "rock"]
        
        # Get recommendations with error handling
        try:
            recommendations = await asyncio.to_thread(
                sp.recommendations,
                seed_genres=seed_genres[:2],  # Use max 2 genres for better results
                limit=25,  # Get a few extra for filtering
                **{k: v for k, v in audio_features.items() if v is not None}
            )
        except Exception as rec_error:
            logger.warning(f"Recommendation API failed: {rec_error}, falling back to search")
            # Fallback to search
            search_results = await asyncio.to_thread(sp.search, q=user_query, type='track', limit=20)
            recommendations = {'tracks': search_results['tracks']['items']}
        
        # Process tracks efficiently
        tracks = []
        track_ids = []
        
        for track in recommendations['tracks'][:20]:  # Limit to 20 tracks
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
                
                # Get album image safely
                album_images = track.get('album', {}).get('images', [])
                if album_images:
                    track_data['album_image'] = album_images[0]['url']
                
                tracks.append(track_data)
                track_ids.append(track['id'])
        
        # Create playlist in background if requested
        playlist_info = None
        if create_playlist and track_ids:
            background_tasks.add_task(
                create_playlist_background,
                sp, user_query, playlist_name, track_ids, analysis
            )
            playlist_info = {"status": "creating", "message": "Playlist is being created in the background"}
        
        return JSONResponse({
            "query": user_query,
            "analysis": analysis,
            "user_profile": user_profile,
            "tracks": tracks,
            "playlist_created": create_playlist,
            "playlist_info": playlist_info,
            "total_tracks": len(tracks)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

async def create_playlist_background(sp, user_query: str, playlist_name: str, track_ids: List[str], analysis: Dict):
    """Background task to create playlist"""
    try:
        user = await asyncio.to_thread(sp.current_user)
        
        # Generate playlist name if not provided
        if not playlist_name:
            genre_text = ", ".join(analysis["detected_genres"][:2]) if analysis["detected_genres"] else "Mixed"
            mood_text = ", ".join(analysis["detected_moods"][:2]) if analysis["detected_moods"] else "Vibes"
            playlist_name = f"🎵 {genre_text} {mood_text} - Moodify"
        
        # Create playlist description
        description = f"AI-generated playlist based on: {user_query}"
        if analysis["detected_genres"]:
            description += f" | Genres: {', '.join(analysis['detected_genres'][:3])}"
        if analysis["detected_moods"]:
            description += f" | Moods: {', '.join(analysis['detected_moods'][:3])}"
        
        # Create the playlist
        playlist = await asyncio.to_thread(
            sp.user_playlist_create,
            user=user['id'],
            name=playlist_name,
            public=True,
            description=description
        )
        
        # Add tracks to playlist
        await asyncio.to_thread(sp.playlist_add_items, playlist['id'], track_ids)
        
        logger.info(f"Created playlist: {playlist_name} with {len(track_ids)} tracks")
        
    except Exception as e:
        logger.error(f"Error creating playlist in background: {e}")

@app.get("/api/top-tracks")
async def get_top_tracks(request: Request):
    """Get user's top tracks for analytics"""
    sp = await _ensure_token(request)
    if not sp:
        return {"error": "Not authenticated"}
    
    try:
        # Get user's top tracks (short term - last 4 weeks)
        top_tracks = sp.current_user_top_tracks(limit=20, offset=0, time_range='short_term')
        
        # Get user's top artists
        top_artists = sp.current_user_top_artists(limit=10, offset=0, time_range='short_term')
        
        # Get user's recently played
        recent_tracks = sp.current_user_recently_played(limit=20)
        
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
        profile = get_user_listening_profile(sp)
        return profile
    except Exception as e:
        return {"error": str(e)}

@app.post("/create-playlist")
async def create_custom_playlist(request: Request, playlist_data: Dict):
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
        user = sp.current_user()
        
        # Create the playlist
        playlist = sp.user_playlist_create(
            user=user['id'],
            name=name,
            public=public,
            description=description
        )
        
        # Add tracks to playlist
        sp.playlist_add_items(playlist['id'], track_ids)
        
        # Add playlist to user's library
        sp.user_playlist_follow_playlist(user['id'], playlist['id'])
        
        # Get playlist details
        playlist_details = sp.playlist(playlist['id'])
        
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
        print(f"Error creating playlist: {e}")
        return {"error": str(e), "success": False}

@app.get("/api/my-playlists")
async def get_user_playlists(request: Request):
    """Get user's playlists"""
    sp = await _ensure_token(request)
    if not sp:
        return {"error": "Not authenticated"}
    
    try:
        # Get user's playlists
        playlists = sp.current_user_playlists(limit=50)
        
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


