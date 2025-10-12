"""
Moodify Backend API
==================

AI-Powered Music Discovery Platform Backend

This FastAPI application provides:
- Spotify OAuth authentication and session management
- AI-powered music recommendation system using Ollama LLM
- User music history analysis and intelligent track selection
- Spotify API integration for recommendations and playlist creation
- CORS-enabled endpoints for frontend integration

Performance optimizations:
- LRU caching for frequently accessed data
- Async/await for non-blocking operations
- Efficient error handling and logging
- Optimized database queries and API calls

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
# CONFIGURATION AND INITIALIZATION
# =============================================================================

# Configure structured logging for better debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('moodify.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# PERFORMANCE OPTIMIZATIONS (SELECTIVE CACHING)
# =============================================================================

# Cache for album covers with timestamp for freshness
_album_covers_cache = {
    "urls": [],
    "timestamp": 0,
    "ttl": 3600  # 1 hour cache
}

def is_cache_valid() -> bool:
    """Check if album covers cache is still valid"""
    return (time.time() - _album_covers_cache["timestamp"]) < _album_covers_cache["ttl"]

def get_genre_seeds(sp) -> List[str]:
    """
    Get Spotify genre seeds without caching.
    
    Returns:
        List[str]: Available genre seeds from Spotify API
    """
    try:
        return sp.recommendation_genre_seeds()['genres']
    except Exception as e:
        logger.warning(f"Failed to get genre seeds: {e}")
        # Fallback to common genres if API call fails
        return ["pop", "rock", "electronic", "hip-hop", "jazz"]

def is_token_expired(token_info: Optional[Dict]) -> bool:
    """
    Check if Spotify token is expired with improved logic.
    
    This function provides robust token expiration checking with multiple
    fallback mechanisms to ensure reliable authentication state management.
    
    Args:
        token_info (Optional[Dict]): Token information dictionary from Spotify
        
    Returns:
        bool: True if token is expired or invalid, False if valid
    """
    if not token_info:
        return True
    
    # Check if we have an expiration time
    if "expires_at" in token_info:
        return time.time() > token_info["expires_at"]
    
    # Fallback: assume expired if no expiration info
    return True

# =============================================================================
# FASTAPI APPLICATION CONFIGURATION
# =============================================================================

# Initialize FastAPI application with comprehensive metadata
app = FastAPI(
    title="Moodify API", 
    version="1.0.0",
    description="AI-Powered Music Discovery Platform with Spotify Integration",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "auth", "description": "Authentication and session management"},
        {"name": "recommendations", "description": "AI-powered music recommendations"},
        {"name": "playlists", "description": "Playlist creation and management"},
        {"name": "user", "description": "User profile and music history"}
    ]
)

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

# CORS middleware for cross-origin requests from frontend
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

# Session middleware for secure session management
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "your-secret-key"),
    max_age=60 * 60 * 2,  # 2 hours - shorter session for better security
    https_only=False,  # Set to True in production
    same_site="lax"  # Standard same-site policy
)

# =============================================================================
# STATIC FILE SERVING (Production) - MOVED TO END OF FILE
# =============================================================================

# =============================================================================
# MUSIC GENRE AND MOOD MAPPINGS
# =============================================================================

# Comprehensive genre and mood mapping for intelligent music categorization
# This mapping helps the AI system understand user preferences and generate
# more accurate recommendations based on mood and genre keywords
GENRE_MAPPINGS = {
    # Metal subgenres - Aggressive and powerful music
    "metal": ["metal", "heavy metal", "death metal", "black metal", "thrash metal", "power metal"],
    
    # Rock subgenres - Versatile rock music categories
    "rock": ["rock", "hard rock", "classic rock", "alternative rock", "indie rock"],
    
    # Electronic music - Digital and synthesized sounds
    "electronic": ["electronic", "edm", "dance", "house", "techno", "trance", "dubstep"],
    
    # Hip-hop and R&B - Urban and contemporary music
    "hip_hop": ["hip hop", "rap", "trap", "r&b", "soul"],
    
    # Pop music - Mainstream and accessible
    "pop": ["pop", "pop rock", "indie pop", "synthpop"],
    
    # Jazz - Sophisticated and improvisational
    "jazz": ["jazz", "smooth jazz", "bebop", "fusion"],
    
    # Classical - Orchestral and traditional
    "classical": ["classical", "orchestral", "symphony"],
    
    # Country and folk - Rural and traditional
    "country": ["country", "folk", "bluegrass"],
    
    # Reggae - Caribbean and rhythmic
    "reggae": ["reggae", "dub", "ska"],
    
    # Punk - Rebellious and energetic
    "punk": ["punk", "hardcore", "emo"],
    
    # Lo-fi - Relaxed and atmospheric
    "lofi": ["lofi", "chill", "ambient", "study"],
    
    # Workout - High-energy and motivating
    "workout": ["workout", "gym", "energy", "upbeat"],
    
    # Emotional states - Mood-based categorization
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

def enhanced_mood_analysis(query: str) -> Dict:
    """
    Enhanced mood and genre analysis using natural language processing (no caching)
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

async def get_user_music_history(sp) -> List[Dict]:
    """
    Get user's comprehensive music history for LLM analysis.
    
    This function efficiently fetches user's music data from multiple Spotify endpoints
    to create a comprehensive listening history for AI analysis. It uses async operations
    to fetch data in parallel and includes deduplication for optimal performance.
    
    Args:
        sp: Authenticated Spotify client instance
        
    Returns:
        List[Dict]: Comprehensive list of user's music history with metadata
    """
    try:
        # Verify authentication before proceeding
        if not sp or not hasattr(sp, 'current_user'):
            logger.error("Spotify client not properly authenticated")
            return []
        
        # Test authentication with a simple call to ensure validity
        try:
            user_info = await asyncio.to_thread(sp.current_user)
            logger.info(f"Authenticated as user: {user_info.get('display_name', 'Unknown')}")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return []
        
        history = []
        
        # Fetch top tracks from different time ranges for comprehensive analysis
        # This provides a balanced view of user's listening habits over time
        time_ranges = ['short_term', 'medium_term', 'long_term']
        for time_range in time_ranges:
            try:
                top_tracks = await asyncio.to_thread(sp.current_user_top_tracks, time_range=time_range, limit=50)
                for track in top_tracks['items']:
                    history.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artists': [artist['name'] for artist in track['artists']],
                        'album': track['album']['name'],
                        'popularity': track['popularity'],
                        'time_range': time_range
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch {time_range} tracks: {e}")
                continue
        
        # Fetch recently played tracks for current listening patterns
        # This captures the user's most recent musical interests and trends
        try:
            recent_tracks = await asyncio.to_thread(sp.current_user_recently_played, limit=50)
            for item in recent_tracks['items']:
                track = item['track']
                history.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'album': track['album']['name'],
                    'popularity': track['popularity'],
                    'time_range': 'recent'
                })
        except Exception as e:
            logger.warning(f"Failed to fetch recent tracks: {e}")
        
        # Fetch saved albums for deeper musical preferences analysis
        # This includes user-curated content that may contain regional music
        try:
            saved_albums = await asyncio.to_thread(sp.current_user_saved_albums, limit=50)
            for album in saved_albums['items']:
                try:
                    album_tracks = await asyncio.to_thread(sp.album_tracks, album['album']['id'])
                    for track in album_tracks['items']:
                        history.append({
                            'id': track['id'],
                            'name': track['name'],
                            'artists': [artist['name'] for artist in track['artists']],
                            'album': album['album']['name'],
                            'popularity': track.get('popularity', 0),
                            'time_range': 'saved_album'
                        })
                except Exception as e:
                    logger.warning(f"Failed to fetch tracks from album {album['album']['name']}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Failed to fetch saved albums: {e}")
        
        # Get tracks from user's playlists (might contain Telugu music)
        try:
            playlists = await asyncio.to_thread(sp.current_user_playlists, limit=20)
            for playlist in playlists['items']:
                try:
                    playlist_tracks = await asyncio.to_thread(sp.playlist_tracks, playlist['id'], limit=50)
                    for item in playlist_tracks['items']:
                        if item['track'] and item['track'].get('id'):
                            track = item['track']
                            history.append({
                                'id': track['id'],
                                'name': track['name'],
                                'artists': [artist['name'] for artist in track['artists']],
                                'album': track['album']['name'],
                                'popularity': track.get('popularity', 0),
                                'time_range': 'playlist'
                            })
                except Exception as e:
                    logger.warning(f"Failed to fetch tracks from playlist {playlist['name']}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Failed to fetch playlists: {e}")
        
        # Remove duplicates based on track ID
        seen_ids = set()
        unique_history = []
        for track in history:
            if track['id'] not in seen_ids:
                seen_ids.add(track['id'])
                unique_history.append(track)
        
        logger.info(f"Retrieved {len(unique_history)} unique tracks from user history")
        return unique_history
        
    except Exception as e:
        logger.error(f"Error getting user music history: {e}")
        return []

async def query_llm_for_history_selection(query: str, music_history: List[Dict]) -> List[str]:
    """
    Use cloud LLM or fallback to select 10 songs from user's history that match the query
    """
    try:
        # Try cloud LLM first
        try:
            from .llm_cloud import get_llm_client
            llm_client = get_llm_client()
            return await llm_client.select_tracks(query, music_history)
        except Exception as e:
            logger.warning(f"Cloud LLM not available: {e}, using fallback")
            from .llm_fallback import select_tracks_fallback
            return select_tracks_fallback(query, music_history)
    except Exception as e:
        logger.error(f"Error in LLM selection: {e}")
        # Last resort: return first 10 tracks
        return [track['id'] for track in music_history[:10] if track.get('id')]
        # Prepare a diverse music history for the LLM (mix of different time periods and sources)
        # Use intelligent selection based on query analysis
        diverse_history = []
        
        # Analyze query for key concepts
        query_lower = query.lower()
        
        # Language keywords - more comprehensive
        language_keywords = {
            'english': ['english', 'eng', 'american', 'british', 'usa', 'uk'],
            'spanish': ['spanish', 'español', 'latino', 'latin', 'mexican', 'colombian'],
            'telugu': ['telugu', 'telugu', 'andhra', 'hyderabad'],
            'hindi': ['hindi', 'bollywood', 'india', 'indian', 'desi'],
            'tamil': ['tamil', 'tamil', 'chennai', 'tamilnadu'],
            'kannada': ['kannada', 'kannada', 'bangalore', 'karnataka'],
            'french': ['french', 'français', 'france', 'paris'],
            'german': ['german', 'deutsch', 'germany', 'berlin'],
            'japanese': ['japanese', 'japan', 'tokyo', 'anime'],
            'korean': ['korean', 'k-pop', 'korea', 'seoul']
        }
        
        # Genre keywords
        genre_keywords = {
            'pop': ['pop', 'popular'],
            'rock': ['rock', 'alternative', 'indie'],
            'classical': ['classical', 'orchestral', 'symphony'],
            'jazz': ['jazz', 'blues'],
            'electronic': ['electronic', 'edm', 'techno', 'house'],
            'folk': ['folk', 'acoustic'],
            'hip_hop': ['hip hop', 'rap', 'hip-hop'],
            'country': ['country', 'western'],
            'reggae': ['reggae', 'ska'],
            'rnb': ['r&b', 'rnb', 'soul']
        }
        
        # Mood keywords
        mood_keywords = {
            'happy': ['happy', 'upbeat', 'cheerful', 'energetic'],
            'sad': ['sad', 'melancholy', 'emotional', 'depressing'],
            'calm': ['calm', 'peaceful', 'relaxing', 'chill'],
            'romantic': ['romantic', 'love', 'romantic'],
            'angry': ['angry', 'aggressive', 'intense'],
            'nostalgic': ['nostalgic', 'old', 'vintage', 'retro']
        }
        
        # Era keywords
        era_keywords = {
            '80s': ['80s', 'eighties', '1980s'],
            '90s': ['90s', 'nineties', '1990s'],
            '2000s': ['2000s', '2000s', '2000s'],
            'recent': ['recent', 'new', 'latest', 'current'],
            'old': ['old', 'classic', 'vintage', 'traditional']
        }
        
        # Find matching tracks based on query analysis with scoring
        matching_tracks = []
        other_tracks = []
        
        for track in music_history:
            track_name = track['name'].lower()
            artists = ' '.join(track['artists']).lower()
            album = track['album'].lower()
            track_text = f"{track_name} {artists} {album}"
            
            # Calculate match score
            match_score = 0
            match_reasons = []
            
            # Check for language matches (highest priority)
            for lang, keywords in language_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    if any(keyword in track_text for keyword in keywords):
                        match_score += 10  # High score for language match
                        match_reasons.append(f"language:{lang}")
                        break
            
            # Check for genre matches
            for genre, keywords in genre_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    if any(keyword in track_text for keyword in keywords):
                        match_score += 8  # High score for genre match
                        match_reasons.append(f"genre:{genre}")
                        break
            
            # Check for mood matches
            for mood, keywords in mood_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    if any(keyword in track_text for keyword in keywords):
                        match_score += 6  # Medium score for mood match
                        match_reasons.append(f"mood:{mood}")
                        break
            
            # Check for era matches
            for era, keywords in era_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    if any(keyword in track_text for keyword in keywords):
                        match_score += 4  # Medium score for era match
                        match_reasons.append(f"era:{era}")
                        break
            
            # Check for direct text matches in track name or artist
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 2:  # Only consider words longer than 2 characters
                    if word in track_name:
                        match_score += 5  # High score for direct name match
                        match_reasons.append(f"name_match:{word}")
                    elif word in artists:
                        match_score += 3  # Medium score for artist match
                        match_reasons.append(f"artist_match:{word}")
            
            # Add track with match score and reasons
            track_with_score = {
                **track,
                'match_score': match_score,
                'match_reasons': match_reasons
            }
            
            if match_score > 0:
                matching_tracks.append(track_with_score)
            else:
                other_tracks.append(track_with_score)
        
        # Sort matching tracks by score (highest first)
        matching_tracks.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Select diverse history: prioritize matching tracks, then add others
        if matching_tracks:
            # Take up to 15 matching tracks, then add others
            diverse_history = matching_tracks[:15] + other_tracks[:10]
            logger.info(f"Found {len(matching_tracks)} matching tracks for query: {query}")
            logger.info(f"Top matching tracks:")
            for i, track in enumerate(matching_tracks[:5]):
                logger.info(f"  {i+1}. {track['name']} by {track['artists'][0]} (score: {track['match_score']}, reasons: {track['match_reasons']})")
        else:
            # If no specific matches, use diverse selection
            logger.info(f"No specific matches found for query: {query}, using diverse selection")
            if len(music_history) > 50:
                step = len(music_history) // 25
                for i in range(0, len(music_history), step):
                    if len(diverse_history) >= 25:
                        break
                    diverse_history.append(music_history[i])
            else:
                diverse_history = music_history[:25]
        
        # Ensure we have enough tracks for LLM
        if len(diverse_history) < 10:
            # Add more tracks from the original history
            remaining_tracks = [track for track in music_history if track not in diverse_history]
            diverse_history.extend(remaining_tracks[:25-len(diverse_history)])
        
        logger.info(f"Selected {len(diverse_history)} tracks for LLM analysis")
        
        history_text = "\n".join([
            f"{track['name']} by {', '.join(track['artists'])} ({track['id']})"
            for track in diverse_history
        ])
        
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
            "model": "llama3.2:3b",  # Using the better 3B model
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_ctx": 8192,  # Increase context window
                "num_predict": 500  # Increase output length for complete JSON
            }
        }
        
        response = requests.post(ollama_url, json=payload, timeout=60)  # Increase timeout
        response.raise_for_status()
        
        result = response.json()
        llm_response = result.get('response', '').strip()
        
        # Parse the JSON response with better error handling
        try:
            # Clean up the response - remove any markdown formatting and extra text
            cleaned_response = llm_response.replace('```json', '').replace('```', '').strip()
            
            # Find the JSON array in the response
            json_start = cleaned_response.find('[')
            json_end = cleaned_response.rfind(']') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = cleaned_response[json_start:json_end]
                
                # Extract only the valid JSON lines
                lines = json_str.split('\n')
                json_lines = []
                for line in lines:
                    line = line.strip()
                    # Keep lines that look like JSON array elements
                    if (line.startswith('[') or 
                        line.startswith('"') or 
                        line.startswith(',') or 
                        line.startswith(']') or
                        line.startswith('    "') or
                        line.startswith('  "')):
                        json_lines.append(line)
                
                json_str = '\n'.join(json_lines)
                
                # Fix common JSON issues
                if not json_str.startswith('['):
                    json_str = '[' + json_str
                if not json_str.endswith(']'):
                    json_str = json_str + ']'
                
                # Remove trailing commas
                json_str = json_str.replace(',]', ']')
                json_str = json_str.replace(',\n]', '\n]')
                json_str = json_str.replace(',\n  ]', '\n]')
                
                # Try to fix incomplete JSON by finding the last complete ID
                if not json_str.endswith(']'):
                    # Find the last complete ID (22 characters)
                    import re
                    id_matches = re.findall(r'"([a-zA-Z0-9]{22})"', json_str)
                    if id_matches:
                        # Reconstruct JSON with only complete IDs
                        json_str = '[' + ','.join([f'"{id}"' for id in id_matches]) + ']'
                
                selected_ids = json.loads(json_str)
                
                # Validate that we got valid IDs
                if isinstance(selected_ids, list) and len(selected_ids) > 0:
                    # Filter out any invalid IDs (Spotify IDs are 22 characters)
                    valid_ids = [id for id in selected_ids if isinstance(id, str) and len(id) == 22]
                    
                    if len(valid_ids) >= 5:  # At least 5 valid IDs
                        # Take up to 10 valid IDs
                        final_ids = valid_ids[:10]
                        logger.info(f"LLM selected {len(final_ids)} valid track IDs from history")
                        return final_ids
                    else:
                        logger.warning(f"LLM returned only {len(valid_ids)} valid IDs")
                        # Fallback: return first 10 tracks from history
                        return [track['id'] for track in music_history[:10]]
                else:
                    raise ValueError("Invalid JSON array format")
            else:
                raise ValueError("No JSON array found in LLM response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"LLM response: {llm_response}")
            # Fallback: return first 10 tracks from history
            return [track['id'] for track in music_history[:10]]
            
    except Exception as e:
        logger.error(f"Error querying LLM: {e}")
        # Fallback: return first 10 tracks from history
        return [track['id'] for track in music_history[:10]]

async def get_spotify_recommendations(sp, seed_track_ids: List[str], query: str) -> List[Dict]:
    """
    Use Spotify's recommendation API with seed tracks to get new recommendations
    """
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
        
        logger.info(f"Generated {len(new_tracks)} new recommendations from Spotify")
        return new_tracks
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            logger.warning(f"Spotify recommendations API returned 404 - likely insufficient seed data. Seed tracks: {seed_track_ids}")
        else:
            logger.error(f"Error getting Spotify recommendations: {e}")
        # Fallback: return empty list instead of crashing
        return []

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
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "https://localhost:8000/callback"),
        scope="user-read-private user-read-email user-top-read user-read-recently-played playlist-read-private playlist-modify-public playlist-modify-private user-read-playback-state user-modify-playback-state user-read-playback-position user-library-read"
    )

async def _ensure_token(request: Request):
    """Ensure we have a valid Spotify token"""
    session = request.session
    print(f"DEBUG: _ensure_token called with session keys: {list(session.keys())}")
    
    # First check session
    if "spotify_token_info" in session:
        token_info = session["spotify_token_info"]
        print(f"DEBUG: Found token_info in session with keys: {list(token_info.keys())}")
        
        # Check if token is expired
        if is_token_expired(token_info):
            print(f"DEBUG: Session token is expired, attempting refresh")
            try:
                oauth = get_spotify_oauth()
                token_info = oauth.refresh_access_token(token_info["refresh_token"])
                session["spotify_token_info"] = token_info
                print(f"DEBUG: Token refreshed successfully")
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return None
        else:
            print(f"DEBUG: Session token is still valid")
        
        return spotipy.Spotify(auth=token_info["access_token"])
    
    # No cached tokens - user needs to login fresh
    print(f"DEBUG: No valid session token found - user needs to login")
    return None

@app.get("/")
async def root():
    return {"message": "Moodify API - AI-Powered Music Discovery"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/login")
async def login(request: Request):
    """Start Spotify OAuth flow"""
    # Clear any existing session to force fresh authentication
    request.session.clear()
    
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
    
    # Force session cookie to be deleted and redirect
    response = RedirectResponse(auth_url)
    response.delete_cookie("session", path="/", domain=None, secure=False, httponly=True, samesite="lax")
    
    return response

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

@app.post("/logout")
@app.get("/logout")
async def logout(request: Request):
    """Logout user and clear all cached data"""
    logger.info(f"Logout endpoint called with method: {request.method}")
    logger.info(f"Session keys before clear: {list(request.session.keys())}")
    
    try:
        # Clear the session completely
        request.session.clear()
        logger.info("Session cleared successfully")
        
        # Force session to expire immediately by setting negative max_age
        # This ensures the session cookie is deleted from the browser
        response = JSONResponse({"message": "Logged out successfully - all caches cleared"})
        response.delete_cookie("session", path="/", domain=None, secure=False, httponly=True, samesite="lax")
        
        # Clear all cached token files
        import os
        import glob
        
        # Remove .cache files
        cache_files = glob.glob(os.path.join(os.path.dirname(__file__), '.cache*'))
        for cache_file in cache_files:
            if os.path.exists(cache_file):
                os.remove(cache_file)
                logger.info(f"Cleared cached token file: {cache_file}")
        
        # Clear any other cache files
        cache_patterns = ['.cache', '.spotify_cache', '.token_cache']
        for pattern in cache_patterns:
            cache_files = glob.glob(os.path.join(os.path.dirname(__file__), pattern))
            for cache_file in cache_files:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    logger.info(f"Cleared cache file: {cache_file}")
        
        logger.info("User logged out successfully - all caches cleared")
        return response
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Failed to logout")

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

@app.post("/recommend-v2")
async def recommend_tracks_v2(request: Request, query: Dict):
    """
    New LLM-based recommendation system:
    1. LLM selects 10 songs from user's history that match the query
    2. Spotify uses those songs as seed tracks to generate new recommendations
    """
    sp = await _ensure_token(request)
    if not sp:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_query = query.get("query", "").strip()
        if not user_query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        logger.info(f"Processing recommendation request: '{user_query}'")
        
        # Step 1: Get user's music history
        music_history = await get_user_music_history(sp)
        if not music_history:
            # For new accounts with no history, use search-based recommendations
            logger.info("No music history found, using search-based recommendations")
            try:
                # Search for popular tracks based on the query
                search_results = await asyncio.to_thread(
                    sp.search, 
                    q=f"{user_query} music", 
                    type='track', 
                    limit=20,
                    market='US'
                )
                
                if search_results and 'tracks' in search_results and search_results['tracks']['items']:
                    tracks = search_results['tracks']['items']
                    return {
                        "user_history_recs": [],  # Empty for new accounts
                        "new_recs": [
                            {
                                "id": track["id"],
                                "name": track["name"],
                                "artists": [artist["name"] for artist in track["artists"]],
                                "album": track["album"]["name"],
                                "preview_url": track.get("preview_url"),
                                "external_urls": track.get("external_urls", {}),
                                "images": track["album"].get("images", [])
                            }
                            for track in tracks
                        ]
                    }
                else:
                    raise HTTPException(status_code=400, detail="No music history found and unable to generate recommendations. Please listen to some music first or try a different search term.")
            except Exception as e:
                logger.error(f"Search-based recommendation failed: {e}")
                raise HTTPException(status_code=400, detail="No music history found. Please listen to some music first.")
        
        # Step 2: Use LLM to select 10 songs from history
        selected_track_ids = await query_llm_for_history_selection(user_query, music_history)
        
        # Step 3: Get the full track details for selected history songs
        history_tracks = []
        for track in music_history:
            if track['id'] in selected_track_ids:
                # Get additional track details
                try:
                    track_details = await asyncio.to_thread(sp.track, track['id'])
                    history_tracks.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artists': track['artists'],
                        'album': track['album'],
                        'album_image': track_details.get('album', {}).get('images', [{}])[0].get('url'),
                        'external_url': track_details.get('external_urls', {}).get('spotify'),
                        'preview_url': track_details.get('preview_url'),
                        'popularity': track['popularity'],
                        'source': 'history'
                    })
                except Exception as e:
                    logger.warning(f"Failed to get details for track {track['id']}: {e}")
                    # Add basic track info if detailed fetch fails
                    history_tracks.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artists': track['artists'],
                        'album': track['album'],
                        'album_image': None,
                        'external_url': None,
                        'preview_url': None,
                        'popularity': track['popularity'],
                        'source': 'history'
                    })
        
        # Step 4: Use selected tracks as seeds for Spotify recommendations
        new_tracks = await get_spotify_recommendations(sp, selected_track_ids, user_query)
        
        # If Spotify recommendations failed, use intelligent search fallback
        if not new_tracks:
            logger.warning("Spotify recommendations failed, using intelligent search fallback")
            try:
                # Create intelligent search queries based on user input
                search_queries = []
                
                # Analyze the query to create better search terms
                query_lower = user_query.lower()
                if any(word in query_lower for word in ['rock', 'pop', 'jazz', 'classical', 'country', 'hip hop', 'rap', 'electronic', 'indie']):
                    # Genre-based search
                    search_queries.extend([
                        user_query,
                        f"{user_query} songs",
                        f"{user_query} music",
                        f"{user_query} hits"
                    ])
                elif any(word in query_lower for word in ['happy', 'sad', 'energetic', 'calm', 'chill', 'upbeat', 'melancholy']):
                    # Mood-based search
                    search_queries.extend([
                        f"{user_query} music",
                        f"{user_query} songs",
                        f"{user_query} playlist",
                        user_query
                    ])
                elif any(word in query_lower for word in ['workout', 'gym', 'running', 'party', 'dance', 'study', 'focus']):
                    # Activity-based search
                    search_queries.extend([
                        f"{user_query} music",
                        f"{user_query} songs",
                        f"{user_query} playlist",
                        user_query
                    ])
                else:
                    # General search with multiple strategies
                    search_queries.extend([
                        user_query,
                        f"{user_query} music",
                        f"{user_query} songs",
                        f"{user_query} hits",
                        f"{user_query} playlist"
                    ])
                
                # Try each search query until we get results
                for search_query in search_queries:
                    try:
                        logger.info(f"Trying search query: '{search_query}'")
                        search_results = await asyncio.to_thread(sp.search, search_query, type='track', limit=20, market='US')
                        logger.info(f"Search results for '{search_query}': {search_results}")
                        if search_results and 'tracks' in search_results and search_results['tracks']['items']:
                            logger.info(f"Found {len(search_results['tracks']['items'])} tracks for query: '{search_query}'")
                            for track in search_results['tracks']['items']:
                                if track and track.get('id') and len(new_tracks) < 20:
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
                            
                            if new_tracks:
                                logger.info(f"Search fallback successful with query: {search_query}")
                                break
                    except Exception as e:
                        logger.warning(f"Search query '{search_query}' failed: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"All search fallbacks failed: {e}")
        
        # Final safety net - if we still have no tracks, get popular music
        if not new_tracks:
            logger.warning("All fallbacks failed, getting popular music as last resort")
            try:
                search_results = await asyncio.to_thread(sp.search, "popular music", type='track', limit=20, market='US')
                if search_results and 'tracks' in search_results and search_results['tracks']['items']:
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
                                'popularity': track.get('popularity', 0),
                                'source': 'new'
                            }
                            
                            album_images = track.get('album', {}).get('images', [])
                            if album_images:
                                track_data['album_image'] = album_images[0]['url']
                            
                            new_tracks.append(track_data)
            except Exception as e:
                logger.error(f"Even popular music fallback failed: {e}")
        
        # Add source indicator to new tracks
        for track in new_tracks:
            track['source'] = 'new'
        
        logger.info(f"Generated {len(history_tracks)} history recommendations and {len(new_tracks)} new recommendations")
        
        # Combine all tracks for the frontend
        all_tracks = history_tracks + new_tracks
        
        return JSONResponse({
            "query": user_query,
            "tracks": all_tracks,  # Frontend expects 'tracks' property
            "user_history_recs": history_tracks,
            "new_recs": new_tracks,
            "total_history": len(history_tracks),
            "total_new": len(new_tracks),
            "analysis": {
                "method": "LLM + Spotify Seeds",
                "description": f"Selected {len(selected_track_ids)} songs from your history using AI, then generated {len(new_tracks)} new recommendations based on those selections."
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in recommendations v2: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

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
        
        # Enhanced mood analysis (no caching)
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
        
        # Get available genre seeds (no caching)
        valid_genres = get_genre_seeds(sp)
        
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
                market='US',  # Add market parameter
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


@app.get("/api/album-covers")
async def get_album_covers(request: Request):
    """Get album covers from user's listening history with caching and parallel fetching"""
    sp = await _ensure_token(request)
    if not sp:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    # Check cache first for instant response
    if is_cache_valid() and _album_covers_cache["urls"]:
        logger.info(f"Returning {len(_album_covers_cache['urls'])} album covers from cache")
        return JSONResponse({"urls": _album_covers_cache["urls"]})
    
    try:
        logger.info("Cache miss or expired, fetching fresh album covers...")
        album_covers = set()  # Use set to avoid duplicates
        
        # Define async tasks for parallel execution
        async def fetch_top_tracks_range(time_range: str):
            try:
                top_tracks = await asyncio.to_thread(sp.current_user_top_tracks, time_range=time_range, limit=50)
                urls = set()
                for track in top_tracks['items']:
                    if track.get('album', {}).get('images'):
                        urls.add(track['album']['images'][0]['url'])
                return urls
            except Exception as e:
                logger.warning(f"Failed to fetch {time_range} tracks: {e}")
                return set()
        
        async def fetch_recent_tracks():
            try:
                recent_tracks = await asyncio.to_thread(sp.current_user_recently_played, limit=50)
                urls = set()
                for item in recent_tracks['items']:
                    if item.get('track', {}).get('album', {}).get('images'):
                        urls.add(item['track']['album']['images'][0]['url'])
                return urls
            except Exception as e:
                logger.warning(f"Failed to fetch recent tracks: {e}")
                return set()
        
        async def fetch_saved_albums():
            try:
                saved_albums = await asyncio.to_thread(sp.current_user_saved_albums, limit=50)
                urls = set()
                for item in saved_albums['items']:
                    if item.get('album', {}).get('images'):
                        urls.add(item['album']['images'][0]['url'])
                return urls
            except Exception as e:
                logger.warning(f"Failed to fetch saved albums: {e}")
                return set()
        
        async def fetch_playlist_covers():
            try:
                playlists = await asyncio.to_thread(sp.current_user_playlists, limit=20)
                urls = set()
                
                # Create tasks for fetching tracks from each playlist
                async def fetch_playlist_tracks(playlist_id: str, playlist_name: str):
                    try:
                        playlist_tracks = await asyncio.to_thread(sp.playlist_tracks, playlist_id, limit=50)
                        p_urls = set()
                        for track_item in playlist_tracks['items']:
                            track = track_item.get('track')
                            if track and track.get('album', {}).get('images'):
                                p_urls.add(track['album']['images'][0]['url'])
                        return p_urls
                    except Exception as e:
                        logger.warning(f"Failed to fetch tracks from playlist {playlist_name}: {e}")
                        return set()
                
                # Fetch all playlists in parallel
                playlist_tasks = [
                    fetch_playlist_tracks(pl['id'], pl['name']) 
                    for pl in playlists['items']
                ]
                playlist_results = await asyncio.gather(*playlist_tasks, return_exceptions=True)
                
                # Combine all URLs
                for result in playlist_results:
                    if isinstance(result, set):
                        urls.update(result)
                
                return urls
            except Exception as e:
                logger.warning(f"Failed to fetch playlists: {e}")
                return set()
        
        async def fetch_new_releases():
            try:
                new_releases = await asyncio.to_thread(sp.new_releases, limit=50)
                urls = set()
                for album in new_releases['albums']['items']:
                    if album.get('images'):
                        urls.add(album['images'][0]['url'])
                return urls
            except Exception as e:
                logger.warning(f"Failed to fetch new releases: {e}")
                return set()
        
        # Execute all API calls in parallel for maximum speed
        start_time = time.time()
        results = await asyncio.gather(
            fetch_top_tracks_range('short_term'),
            fetch_top_tracks_range('medium_term'),
            fetch_top_tracks_range('long_term'),
            fetch_recent_tracks(),
            fetch_saved_albums(),
            fetch_playlist_covers(),
            fetch_new_releases(),
            return_exceptions=True
        )
        
        # Combine all results
        for result in results:
            if isinstance(result, set):
                album_covers.update(result)
        
        # Convert to list
        album_covers_list = list(album_covers)
        elapsed = time.time() - start_time
        
        # Update cache
        _album_covers_cache["urls"] = album_covers_list
        _album_covers_cache["timestamp"] = time.time()
        
        logger.info(f"Fetched {len(album_covers_list)} unique album covers in {elapsed:.2f}s (cached for 1 hour)")
        
        return JSONResponse({"urls": album_covers_list})
        
    except Exception as e:
        logger.error(f"Error fetching album covers: {e}")
        # Return cached data if available, even if expired
        if _album_covers_cache["urls"]:
            logger.info("Returning stale cache due to error")
            return JSONResponse({"urls": _album_covers_cache["urls"]})
        return JSONResponse({"error": str(e)}, status_code=500)

# =============================================================================
# STATIC FILE SERVING (Production) - AT THE END
# =============================================================================

# Serve static files in production (frontend build)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Serve the frontend app for all non-API routes (MUST BE LAST)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React frontend for all non-API routes"""
        # This route should only catch frontend routes, not API routes
        # All API routes should be defined above this point
        
        # Serve index.html for all other routes (SPA routing)
        if os.path.exists("static/index.html"):
            from fastapi.responses import FileResponse
            return FileResponse("static/index.html")
        else:
            raise HTTPException(status_code=404, detail="Frontend not built")