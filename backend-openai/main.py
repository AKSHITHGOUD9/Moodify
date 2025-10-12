"""
Moodify Backend - OpenAI Version
===============================

AI-Powered Music Discovery Platform using OpenAI GPT models.
This version uses OpenAI's API for AI-powered recommendations.

Features:
- Spotify OAuth authentication
- OpenAI GPT integration
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
import openai

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

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Security configuration
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_urlsafe(32))

# CORS configuration
FRONTEND_URLS = os.getenv("FRONTEND_URLS", "http://127.0.0.1:5173,https://moodify-ai-powered.vercel.app").split(",")
POST_LOGIN_REDIRECT = os.getenv("POST_LOGIN_REDIRECT", "http://127.0.0.1:5173/")

# Initialize OpenAI client
openai_client = None
if OPENAI_API_KEY:
    from openai import OpenAI
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

# Initialize FastAPI app
app = FastAPI(
    title="Moodify API - OpenAI Version",
    description="AI-Powered Music Discovery Platform with OpenAI GPT",
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
    max_age=60 * 60 * 2,  # 2 hours - shorter session for better security
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
    
    logger.info(f"Session keys in _ensure_token: {list(session.keys())}")
    logger.info(f"Session ID: {session.session_id if hasattr(session, 'session_id') else 'No session ID'}")
    
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
# LLM INTEGRATION (OpenAI)
# =============================================================================

async def query_openai_for_history_selection(query: str, music_history: List[Dict]) -> List[str]:
    """
    Use OpenAI GPT to select 10 songs from user's history that match the query
    """
    try:
        if not openai_client:
            logger.warning("OpenAI client not configured, using fallback")
            return [track['id'] for track in music_history[:10]]
        
        # Prepare history text for OpenAI
        history_text = "\n".join([
            f"ID: {track['id']}, Name: {track['name']}, Artists: {', '.join(track['artists'])}, Album: {track['album']}"
            for track in music_history[:50]  # Limit to 50 tracks for token efficiency
        ])
        
        # Create enhanced prompt for OpenAI
        prompt = f"""You are an expert music curator with deep knowledge of music genres, moods, and cultural contexts. Your task is to select exactly 10 songs from the user's music history that best match their query.

USER QUERY: "{query}"

ANALYSIS CRITERIA (in order of importance):
1. **Semantic Match**: Songs that conceptually match the query's intent
2. **Language Match**: Prioritize songs in the language mentioned (Hindi, Telugu, English, etc.)
3. **Genre Match**: Match musical genres (pop, rock, classical, electronic, etc.)
4. **Mood Match**: Match emotional tone (happy, sad, energetic, calm, etc.)
5. **Era Match**: Match time period (old, new, 80s, 90s, 2000s, etc.)
6. **Artist Relevance**: Direct artist matches or similar artists
7. **Title Relevance**: Song titles that relate to the query

USER'S MUSIC HISTORY:
{history_text}

EXPERT INSTRUCTIONS:
- Think step-by-step: What is the user really looking for?
- Consider cultural context: "hindi" = Bollywood, "telugu" = Telugu cinema
- Match mood: "sad" = melancholic songs, "party" = upbeat tracks
- Consider era: "old" = classic songs, "new" = recent releases
- Prioritize songs that match MULTIPLE criteria
- Ensure diversity in your selection (not all from same artist/album)
- If query is vague, select the user's most popular tracks

RESPONSE FORMAT (JSON only, no explanations):
["id1","id2","id3","id4","id5","id6","id7","id8","id9","id10"]"""

        # Call OpenAI API with comprehensive error handling
        try:
            response = await asyncio.to_thread(
                openai_client.chat.completions.create,
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert music curator. Always respond with valid JSON arrays of track IDs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,        # Lower for more consistent results
                max_tokens=300,         # Reduced for faster response
                top_p=0.9,             # Focus on most likely tokens
                frequency_penalty=0.1,  # Slight penalty for repetition
                presence_penalty=0.1    # Encourage diversity
            )
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            return [track['id'] for track in music_history[:10]]
        except openai.APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {e}")
            return [track['id'] for track in music_history[:10]]
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {e}")
            return [track['id'] for track in music_history[:10]]
        except openai.BadRequestError as e:
            logger.error(f"OpenAI invalid request: {e}")
            return [track['id'] for track in music_history[:10]]
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return [track['id'] for track in music_history[:10]]
        
        llm_response = response.choices[0].message.content.strip()
        
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
                        logger.info(f"OpenAI selected {len(valid_ids)} valid track IDs from history")
                        return valid_ids[:10]
                    else:
                        logger.warning(f"OpenAI returned only {len(valid_ids)} valid IDs")
                        return [track['id'] for track in music_history[:10]]
                else:
                    raise ValueError("Invalid JSON array format")
            else:
                raise ValueError("No JSON array found in OpenAI response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            logger.error(f"OpenAI response: {llm_response}")
            return [track['id'] for track in music_history[:10]]
            
    except Exception as e:
        logger.error(f"Error querying OpenAI: {e}")
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
                                'popularity': track.get('popularity', 0),
                                'album_image': None,
                                'duration_ms': track.get('duration_ms', 180000),
                                'preview_url': track.get('preview_url')
                            }
                            
                            # Get album image
                            album_images = track.get('album', {}).get('images', [])
                            if album_images:
                                track_data['album_image'] = album_images[0]['url']
                                logger.debug(f"Found album image for {track['name']}: {album_images[0]['url']}")
                            else:
                                logger.debug(f"No album image for {track['name']}")
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
                            'popularity': track.get('popularity', 0),
                            'album_image': None,
                            'duration_ms': track.get('duration_ms', 180000),
                            'preview_url': track.get('preview_url')
                        }
                        
                        # Get album image
                        album_images = track.get('album', {}).get('images', [])
                        if album_images:
                            track_data['album_image'] = album_images[0]['url']
                            logger.debug(f"Found album image for recent track {track['name']}: {album_images[0]['url']}")
                        else:
                            logger.debug(f"No album image for recent track {track['name']}")
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

async def validate_track_ids(sp, track_ids: List[str]) -> List[str]:
    """Validate track IDs by checking if they exist and are playable"""
    valid_tracks = []
    
    for track_id in track_ids:
        try:
            # Check if track exists and is playable
            track = await asyncio.to_thread(sp.track, track_id)
            if track and track.get('is_playable', True):
                valid_tracks.append(track_id)
                logger.debug(f"Track {track_id} is valid and playable")
            else:
                logger.warning(f"Track {track_id} is not playable")
        except Exception as e:
            logger.warning(f"Track {track_id} validation failed: {e}")
            continue
    
    logger.info(f"Validated {len(valid_tracks)}/{len(track_ids)} track IDs")
    return valid_tracks

async def get_spotify_recommendations(sp, seed_track_ids: List[str], query: str) -> List[Dict]:
    """Use Spotify's recommendation API with seed tracks to get new recommendations"""
    try:
        # Validate track IDs before using them
        valid_track_ids = await validate_track_ids(sp, seed_track_ids)
        
        if not valid_track_ids:
            logger.warning("No valid track IDs found for recommendations")
            return []
        
        logger.info(f"Using {len(valid_track_ids)} validated track IDs for recommendations")
        
        recommendations = await asyncio.to_thread(
            sp.recommendations,
            seed_tracks=valid_track_ids[:5],  # Spotify allows max 5 seed tracks
            limit=20,
            market=None  # Global market - works for all regions
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
                    
                    # Get album image with fallback
                    album_images = track.get('album', {}).get('images', [])
                    if album_images:
                        track_data['album_image'] = album_images[0]['url']
                    else:
                        # Use a generic album cover as fallback
                        track_data['album_image'] = 'https://via.placeholder.com/300x300/4f46e5/ffffff?text=Album+Cover'
                    
                    new_tracks.append(track_data)
        
        logger.info(f"Generated {len(new_tracks)} new recommendations from Spotify API")
        return new_tracks
        
    except Exception as e:
        logger.error(f"Error getting Spotify recommendations: {e}")
        logger.error(f"Failed track IDs: {seed_track_ids}")
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

async def generate_enhanced_search_queries(user_query: str) -> List[str]:
    """Use OpenAI to generate better search queries for Spotify"""
    try:
        if not openai_client:
            logger.warning("OpenAI client not available, using original query")
            return [user_query]
        
        prompt = f"""
User wants music recommendations for: "{user_query}"

Generate 4-5 HIGHLY SPECIFIC search queries for Spotify that will find ONLY songs within the exact context of the user's request.

CRITICAL RULES FOR ALL CASES:
1. REGIONAL/LANGUAGE: If user asks for regional music (Telugu, Tamil, Hindi, etc.), ONLY generate queries for that language/region
2. GENRE: If user asks for specific genres (rock, jazz, electronic), focus ONLY on that genre and its sub-genres
3. ERA/DECADE: If user asks for "old", "vintage", "80s", "90s", focus on that specific time period
4. MOOD/ACTIVITY: If user asks for "chill", "party", "workout", focus on that specific mood/activity
5. ARTIST: If user asks for specific artists, focus on their work and similar artists
6. NEVER generate generic terms that could return popular global hits unrelated to the context
7. Be culturally, temporally, and stylistically specific
8. Use actual artist names, album names, film names, and specific terms

Examples:
- "old Telugu" → ["telugu film songs 1990s", "ilayaraja telugu", "spb telugu classics", "telugu golden era", "telugu vintage hits"]
- "rock music" → ["classic rock", "alternative rock", "indie rock", "hard rock", "progressive rock"]
- "chill rock" → ["soft rock", "acoustic rock", "mellow rock", "alternative rock", "indie rock"]
- "chill songs" → ["chillout", "ambient music", "lounge music", "chill beats", "downbeat"]
- "jazz" → ["jazz standards", "bebop", "smooth jazz", "jazz fusion", "big band"]
- "80s music" → ["80s pop", "80s rock", "80s new wave", "80s synthpop", "80s dance"]
- "workout music" → ["workout playlist", "gym music", "high energy", "pump up", "cardio"]
- "romantic songs" → ["romantic ballads", "love songs", "slow songs", "romantic music", "couples"]

Return only the search queries, one per line, no explanations.
"""
        
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a music search expert who creates effective Spotify search queries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        queries_text = response.choices[0].message.content.strip()
        queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
        
        # Add original query as fallback
        if user_query not in queries:
            queries.append(user_query)
        
        logger.info(f"Generated enhanced search queries: {queries}")
        return queries
        
    except Exception as e:
        logger.error(f"Error generating enhanced search queries: {e}")
        return [user_query]

async def search_spotify_tracks(sp, query: str) -> List[Dict]:
    """Search Spotify for tracks using a single query"""
    try:
        logger.info(f"Searching Spotify for: {query}")
        
        results = await asyncio.to_thread(
            sp.search,
            q=query,
            type='track',
            limit=10,  # Get fewer per query to have more diversity
            market=None  # Global market - works for all regions
        )
        
        tracks = []
        if isinstance(results, dict) and 'tracks' in results:
            for track in results['tracks'].get('items', []):
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
                        'duration_ms': track.get('duration_ms', 0)
                    }
                    
                    # Get album image with fallback
                    album_images = track.get('album', {}).get('images', [])
                    if album_images:
                        track_data['album_image'] = album_images[0]['url']
                    else:
                        track_data['album_image'] = 'https://via.placeholder.com/300x300/4f46e5/ffffff?text=Album+Cover'
                    
                    tracks.append(track_data)
        
        logger.info(f"Found {len(tracks)} tracks for query: {query}")
        return tracks
        
    except Exception as e:
        logger.error(f"Error searching for query '{query}': {e}")
        return []

async def get_search_based_recommendations(sp, query: str) -> List[Dict]:
    """Get enhanced recommendations using AI-generated search queries"""
    try:
        logger.info(f"Getting enhanced search-based recommendations for: {query}")
        
        # Generate enhanced search queries using OpenAI
        search_queries = await generate_enhanced_search_queries(query)
        
        # Search Spotify with each query
        all_tracks = []
        for search_query in search_queries:
            tracks = await search_spotify_tracks(sp, search_query)
            all_tracks.extend(tracks)
        
        # Remove duplicates based on track ID
        unique_tracks = {}
        for track in all_tracks:
            if track['id'] not in unique_tracks:
                unique_tracks[track['id']] = track
        
        final_tracks = list(unique_tracks.values())
        
        # Intelligent filtering based on query context for ALL cases
        filtered_tracks = []
        query_lower = query.lower()
        
        def is_relevant_track(track, query):
            """Check if track is relevant to the query context - works for ALL combinations"""
            track_name = track['name'].lower()
            artists = ' '.join(track['artists']).lower()
            album = track['album'].lower()
            
            # Universal exclusions for ALL queries
            universal_exclusions = [
                'sound effects', 'sound effect', 'recording', 'crash recording', 'doorbell', 
                'hand crank', 'vintage metal doorbell', 'vintage metal hand', 'vintage metal junk',
                'background music', 'instrumental background', 'study breaks', 'reading music',
                'elevator ambience', 'therapy music', 'hypnotic', 'new age therapy'
            ]
            
            if any(exclude in track_name or exclude in album or exclude in artists for exclude in universal_exclusions):
                return False
            
            # Define all possible indicators
            regional_languages = ['telugu', 'tamil', 'hindi', 'malayalam', 'kannada', 'bengali', 'punjabi']
            regional_indicators = ['telugu', 'tamil', 'hindi', 'malayalam', 'kannada', 'bengali', 'punjabi', 'bollywood', 'kollywood', 'tollywood', 'sandalwood']
            regional_artists = ['ilayaraja', 'spb', 'ar rahman', 'devi sri prasad', 'harris jayaraj', 'manisharma', 'anirudh', 'yuvan', 'gv prakash']
            
            genres = ['rock', 'metal', 'pop', 'jazz', 'blues', 'country', 'hip hop', 'rap', 'electronic', 'classical']
            genre_indicators = {
                'rock': ['rock', 'alternative', 'grunge', 'punk', 'indie rock', 'soft rock', 'mellow rock', 'acoustic rock'],
                'metal': ['metal', 'heavy metal', 'death metal', 'black metal', 'thrash metal', 'power metal', 'progressive metal', 'nu metal', 'metalcore'],
                'pop': ['pop', 'mainstream', 'pop rock'],
                'jazz': ['jazz', 'bebop', 'swing', 'blues'],
                'blues': ['blues', 'rhythm and blues', 'r&b'],
                'country': ['country', 'folk', 'bluegrass'],
                'hip hop': ['hip hop', 'rap', 'trap', 'drill'],
                'rap': ['rap', 'hip hop', 'mc'],
                'electronic': ['electronic', 'edm', 'house', 'techno', 'trance', 'ambient'],
                'classical': ['classical', 'symphony', 'orchestra', 'concerto']
            }
            
            eras = ['old', 'vintage', 'classic', 'retro', '80s', '90s', '2000s', '2010s']
            era_indicators = {
                'old': ['old', 'vintage', 'classic', 'retro', 'golden'],
                'vintage': ['vintage', 'retro', 'classic', 'old'],
                'classic': ['classic', 'vintage', 'old', 'golden'],
                'retro': ['retro', 'vintage', '80s', '90s'],
                '80s': ['80s', '1980s', 'eighties'],
                '90s': ['90s', '1990s', 'nineties'],
                '2000s': ['2000s', '2000s', 'millennium'],
                '2010s': ['2010s', '2010s', 'tens']
            }
            
            moods = ['chill', 'happy', 'sad', 'energetic', 'romantic', 'party', 'workout', 'study']
            mood_indicators = {
                'chill': ['chill', 'relaxing', 'calm', 'peaceful', 'ambient', 'mellow'],
                'happy': ['happy', 'upbeat', 'cheerful', 'joyful'],
                'sad': ['sad', 'melancholy', 'emotional', 'heartbreak'],
                'energetic': ['energetic', 'upbeat', 'fast', 'intense'],
                'romantic': ['romantic', 'love', 'ballad', 'slow'],
                'party': ['party', 'dance', 'club', 'celebration'],
                'workout': ['workout', 'gym', 'exercise', 'pump'],
                'study': ['study', 'focus', 'concentration', 'background']
            }
            
            # Special genre exclusions
            genre_exclusions = {
                'metal': ['pop-punk', 'britpop', 'pop rock', 'soft rock', 'indie', 'alternative rock', 'emo'],
                'rock': ['ambient', 'elevator', 'therapy', 'hypnotic', 'new age', 'lounge', 'cafe lounge', 'chillout vibes'],
                'electronic': ['classical', 'orchestra', 'symphony'],
                'classical': ['rock', 'pop', 'electronic', 'hip hop', 'rap']
            }
            
            # Multi-criteria matching - check ALL relevant aspects
            query_lower = query.lower()
            matches = []
            
            # Check regional/language
            if any(lang in query_lower for lang in regional_languages):
                if any(indicator in track_name or indicator in artists or indicator in album for indicator in regional_indicators):
                    matches.append('regional')
                elif any(artist in artists for artist in regional_artists):
                    matches.append('regional')
            
            # Check genres
            for genre in genres:
                if genre in query_lower:
                    # Apply genre-specific exclusions
                    if genre in genre_exclusions:
                        if any(exclude in track_name or exclude in artists or exclude in album for exclude in genre_exclusions[genre]):
                            continue
                    
                    # Check for genre indicators
                    if any(indicator in track_name or indicator in artists or indicator in album for indicator in genre_indicators[genre]):
                        matches.append('genre')
                    
                    # Special artist recognition for certain genres
                    if genre == 'metal':
                        metal_artists = ['black sabbath', 'metallica', 'iron maiden', 'system of a down', 'slayer', 'megadeth', 'pantera', 'tool', 'korn', 'linkin park', 'disturbed', 'godsmack']
                        if any(artist in artists for artist in metal_artists):
                            matches.append('genre')
            
            # Check eras
            for era in eras:
                if era in query_lower:
                    if any(indicator in track_name or indicator in artists or indicator in album for indicator in era_indicators[era]):
                        matches.append('era')
            
            # Check moods
            for mood in moods:
                if mood in query_lower:
                    # Apply mood-specific exclusions
                    if mood == 'chill' and any(genre in query_lower for genre in ['rock', 'metal', 'jazz']):
                        # For chill + genre combinations, exclude background music
                        if any(exclude in track_name or exclude in album or exclude in artists for exclude in ['background', 'ambience', 'elevator', 'study breaks', 'reading', 'instrumental background', 'chillout vibes', 'lounge', 'cafe lounge', 'new age', 'therapy', 'hypnotic']):
                            continue
                    
                    if any(indicator in track_name or indicator in artists or indicator in album for indicator in mood_indicators[mood]):
                        matches.append('mood')
            
            # Artist-specific matching
            query_words = query_lower.split()
            if len(query_words) <= 3:
                for word in query_words:
                    if word in artists or word in track_name:
                        matches.append('artist')
                        break
            
            # Return True if we have at least one match, or if no specific context detected
            if matches:
                return True
            
            # If no specific context detected, be more lenient
            return True
        
        # Apply intelligent filtering
        for track in final_tracks:
            if is_relevant_track(track, query_lower):
                filtered_tracks.append(track)
        
        # If filtering removed too many tracks, add some back
        if len(filtered_tracks) < 10:
            logger.warning(f"Filtering removed too many tracks ({len(filtered_tracks)} remaining), adding some back")
            # Add back popular tracks that were filtered out
            for track in final_tracks:
                if track not in filtered_tracks and len(filtered_tracks) < 20:
                    filtered_tracks.append(track)
        
        # Sort by popularity and limit to 20
        filtered_tracks.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        final_tracks = filtered_tracks[:20]
        
        logger.info(f"Generated {len(final_tracks)} enhanced search-based recommendations from {len(search_queries)} queries")
        return final_tracks
        
    except Exception as e:
        logger.error(f"Error getting enhanced search-based recommendations: {e}")
        # Fallback to simple search
        try:
            logger.info("Falling back to simple search")
            results = await asyncio.to_thread(
                sp.search,
                q=query,
                type='track',
                limit=20,
                market=None  # Global market - works for all regions
            )
            
            new_tracks = []
            if isinstance(results, dict) and 'tracks' in results:
                for track in results['tracks'].get('items', []):
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
                            'duration_ms': track.get('duration_ms', 0)
                        }
                        
                        album_images = track.get('album', {}).get('images', [])
                        if album_images:
                            track_data['album_image'] = album_images[0]['url']
                        else:
                            track_data['album_image'] = 'https://via.placeholder.com/300x300/4f46e5/ffffff?text=Album+Cover'
                        
                        new_tracks.append(track_data)
            
            return new_tracks[:20]
        except Exception as fallback_error:
            logger.error(f"Fallback search also failed: {fallback_error}")
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
                logger.info(f"Searching for artist: {artist}")
                search_results = await asyncio.to_thread(
                    sp.search,
                    q=f"artist:{artist}",
                    type="track",
                    limit=4,
                    market='US'
                )
                logger.info(f"Search results for {artist}: {search_results}")
                
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
        
        # If search failed, use hardcoded popular tracks as absolute fallback
        if not all_tracks:
            logger.info("Search failed, using hardcoded popular tracks as absolute fallback")
            hardcoded_tracks = [
                {
                    'id': '4iV5W9uYEdYUVa79Axb7Rh',  # Ed Sheeran - Shape of You
                    'name': 'Shape of You',
                    'artists': ['Ed Sheeran'],
                    'album': '÷ (Divide)',
                    'album_image': 'https://i.scdn.co/image/ab67616d0000b273ba5db46f4b838ef6027e6f96',
                    'external_url': 'https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh',
                    'preview_url': None,
                    'popularity': 100,
                    'duration_ms': 233713  # 3:53
                },
                {
                    'id': '3Z8FwOEN59mRMxDCtb8N0A',  # The Weeknd - Blinding Lights
                    'name': 'Blinding Lights',
                    'artists': ['The Weeknd'],
                    'album': 'After Hours',
                    'album_image': 'https://i.scdn.co/image/ab67616d0000b2738863bc11d2aa12b54f5aeb36',
                    'external_url': 'https://open.spotify.com/track/3Z8FwOEN59mRMxDCtb8N0A',
                    'preview_url': None,
                    'popularity': 100,
                    'duration_ms': 200040  # 3:20
                },
                {
                    'id': '1rqqCSm0Qe4I9rUvXuYlaT',  # Taylor Swift - Anti-Hero
                    'name': 'Anti-Hero',
                    'artists': ['Taylor Swift'],
                    'album': 'Midnights',
                    'album_image': 'https://i.scdn.co/image/ab67616d0000b273bb54dde68cd23e2a268ae0f5',
                    'external_url': 'https://open.spotify.com/track/1rqqCSm0Qe4I9rUvXuYlaT',
                    'preview_url': None,
                    'popularity': 100,
                    'duration_ms': 201820  # 3:21
                },
                {
                    'id': '7qiZfU4dY1lWllzX7mPBI3',  # Dua Lipa - Levitating
                    'name': 'Levitating',
                    'artists': ['Dua Lipa'],
                    'album': 'Future Nostalgia',
                    'album_image': 'https://i.scdn.co/image/ab67616d0000b273ef24c3d2cd7a7f8b8c1e0c9a',
                    'external_url': 'https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3',
                    'preview_url': None,
                    'popularity': 95,
                    'duration_ms': 203040  # 3:23
                },
                {
                    'id': '0VjIjW4WU9jE4q6q8JqX8Y',  # Billie Eilish - Bad Guy
                    'name': 'Bad Guy',
                    'artists': ['Billie Eilish'],
                    'album': 'WHEN WE ALL FALL ASLEEP, WHERE DO WE GO?',
                    'album_image': 'https://i.scdn.co/image/ab67616d0000b2734e9d9e3c5a7c4b4b4b4b4b4b',
                    'external_url': 'https://open.spotify.com/track/0VjIjW4WU9jE4q6q8JqX8Y',
                    'preview_url': None,
                    'popularity': 95,
                    'duration_ms': 194040  # 3:14
                }
            ]
            all_tracks = hardcoded_tracks
        
        logger.info(f"Found {len(all_tracks)} generic popular tracks")
        return all_tracks[:20]  # Return max 20 tracks
        
    except Exception as e:
        logger.error(f"Error getting generic popular tracks: {e}")
        return []

async def get_fallback_seed_tracks(query: str) -> List[str]:
    """Get seed tracks based on query analysis for new users"""
    try:
        query_lower = query.lower()
        logger.info(f"Analyzing query for fallback seeds: '{query}' -> '{query_lower}'")
        
        # Define popular tracks for different categories (REAL Spotify track IDs)
        fallback_tracks = {
            'hindi': [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Popular Hindi song
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another popular Hindi song
                '1rqqCSm0Qe4I9rUvXuYlaT',  # Popular Bollywood track
            ],
            'telugu': [
                '5X4FZ9DpLhPcWqME6bT8et',  # Popular Telugu song
                '2Qd7ZE9kFfGj9V9Lv03XzU',  # Another popular Telugu song
                '1rqqCSm0Qe4I9rUvXuYlaT',  # Popular Telugu track
            ],
            'english': [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Popular English song
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another popular English song
                '1rqqCSm0Qe4I9rUvXuYlaT',  # Popular English track
            ],
            'sad': [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Popular sad song
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another popular sad song
                '1rqqCSm0Qe4I9rUvXuYlaT',  # Popular sad track
            ],
            'happy': [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Popular happy song
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another popular happy song
                '1rqqCSm0Qe4I9rUvXuYlaT',  # Popular happy track
            ],
            'party': [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Popular party song
                '3Z8FwOEN59mRMxDCtb8N0A',  # Another popular party song
                '1rqqCSm0Qe4I9rUvXuYlaT',  # Popular party track
            ]
        }
        
        # Find matching category
        for category, tracks in fallback_tracks.items():
            if category in query_lower:
                logger.info(f"Found matching category: {category}")
                return tracks
        
        # Default to popular English tracks
        logger.info("No specific category found, using default English tracks")
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
        
        # Strategy 3: Use search to find real popular tracks as last resort
        if not trending_ids:
            logger.info("Using search to find popular tracks as last resort")
            try:
                # Search for very popular artists to get real track IDs
                search_results = await asyncio.to_thread(
                    sp.search, 
                    q="artist:Ed Sheeran OR artist:The Weeknd OR artist:Taylor Swift", 
                    type="track", 
                    limit=5
                )
                if search_results and 'tracks' in search_results and 'items' in search_results['tracks']:
                    for track in search_results['tracks']['items']:
                        if track.get('id'):
                            trending_ids.append(track['id'])
            except Exception as e:
                logger.warning(f"Could not search for popular tracks: {e}")
        
        # Strategy 4: Use verified popular track IDs as absolute last resort
        if not trending_ids:
            logger.info("Using verified popular track IDs as absolute last resort")
            trending_ids = [
                '4iV5W9uYEdYUVa79Axb7Rh',  # Ed Sheeran - Shape of You
                '3Z8FwOEN59mRMxDCtb8N0A',  # The Weeknd - Blinding Lights  
                '1rqqCSm0Qe4I9rUvXuYlaT',  # Taylor Swift - Anti-Hero
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
    return {"message": "Moodify API - OpenAI Version", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "llm": "openai", "model": OPENAI_MODEL}

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
        
        # Store token in session (for backward compatibility)
        request.session["spotify_token_info"] = token_info
        
        logger.info("User successfully authenticated")
        logger.info(f"Session keys after storing token: {list(request.session.keys())}")
        
        # Get user info to pass to frontend
        sp = spotipy.Spotify(auth=token_info["access_token"])
        user = sp.current_user()
        
        # Add token and user info to URL for frontend to store
        token = token_info.get("access_token", "")
        user_id = user.get("id", "")
        redirect_url = f"{POST_LOGIN_REDIRECT}?token={token}&user_id={user_id}"
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        return RedirectResponse(url=f"{POST_LOGIN_REDIRECT}?error=callback_failed")

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

@app.get("/me")
async def get_user(request: Request, token: str = None):
    """Get current user information"""
    try:
        # Try token-based authentication first
        if token:
            sp = spotipy.Spotify(auth=token)
            user = await asyncio.to_thread(sp.current_user)
            return {
                "id": user["id"],
                "display_name": user["display_name"],
                "email": user.get("email"),
                "country": user.get("country"),
                "followers": user.get("followers", {}).get("total", 0),
                "images": user.get("images", [])
            }
        
        # Fallback to session-based authentication
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
async def get_top_tracks(request: Request, token: str = None):
    """Get user's top tracks for analytics"""
    # Try token-based authentication first
    if token:
        sp = spotipy.Spotify(auth=token)
    else:
        # Fallback to session-based authentication
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
async def get_user_playlists(request: Request, token: str = None):
    """Get user's playlists"""
    # Try token-based authentication first
    if token:
        sp = spotipy.Spotify(auth=token)
    else:
        # Fallback to session-based authentication
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
async def get_album_covers(request: Request, token: str = None):
    """Get album covers from user's listening history"""
    # Try token-based authentication first
    if token:
        sp = spotipy.Spotify(auth=token)
    else:
        # Fallback to session-based authentication
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
        logger.info(f"Music history length: {len(music_history) if music_history else 0}")
        
        # Handle new users with no music history
        if not music_history or len(music_history) == 0:
            logger.info("No music history found, using fallback recommendations")
            new_recommendations = await get_fallback_recommendations(sp, user_query)
        else:
            logger.info(f"Using music history with {len(music_history)} tracks")
            selected_track_ids = await query_openai_for_history_selection(user_query, music_history)
            new_recommendations = await get_spotify_recommendations(sp, selected_track_ids, user_query)
        
        return {
            "query": user_query,
            "tracks": new_recommendations,
            "total_tracks": len(new_recommendations),
            "method": "OpenAI GPT + Spotify Seeds"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")

@app.post("/recommend-v2")
async def get_recommendations_v2(request: Request, data: dict, token: str = None):
    """Get AI-powered music recommendations using OpenAI GPT"""
    try:
        user_query = data.get("query", "").strip()
        if not user_query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Try token-based authentication first
        if token:
            sp = spotipy.Spotify(auth=token)
        else:
            # Fallback to session-based authentication
            sp = await _ensure_token(request)
            if not sp:
                raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Step 1: Get user's music history
        music_history = await get_user_music_history(sp)
        
        # Handle new users with no music history
        if not music_history:
            logger.info("No music history found, using fallback recommendations")
            new_recommendations = await get_fallback_recommendations(sp, user_query)
            history_tracks = []  # No history tracks for new users
        else:
            # Step 2: Use OpenAI to select 10 songs from history
            selected_track_ids = await query_openai_for_history_selection(user_query, music_history)
            
            if not selected_track_ids:
                logger.warning("OpenAI failed to select tracks, using fallback")
                new_recommendations = await get_fallback_recommendations(sp, user_query)
                history_tracks = []
            else:
                # Step 3: Get new recommendations using selected tracks as seeds
                new_recommendations = await get_spotify_recommendations(sp, selected_track_ids, user_query)
                
                # Always use fallback since Spotify APIs are returning 403/404
                logger.warning("Using fallback recommendations due to Spotify API issues")
                new_recommendations = await get_fallback_recommendations(sp, user_query)
                
                # Step 4: Get the selected history tracks for display
                history_tracks = []
                for track in music_history:
                    if track['id'] in selected_track_ids:
                        track_data = {
                            'id': track['id'],
                            'name': track['name'],
                            'artists': track['artists'],
                            'album': track['album'],
                            'album_image': track.get('album_image'),  # Use existing album_image
                            'external_url': f"https://open.spotify.com/track/{track['id']}",
                            'preview_url': track.get('preview_url'),
                            'popularity': track.get('popularity', 0),
                            'duration_ms': track.get('duration_ms', 180000)  # Default 3 minutes if missing
                        }
                        history_tracks.append(track_data)
        
        logger.info(f"Returning {len(history_tracks)} history tracks and {len(new_recommendations)} new recommendations")
        
        return {
            "user_history_recs": history_tracks,
            "new_recs": new_recommendations,
            "tracks": new_recommendations,  # Frontend expects this
            "query": user_query,
            "method": "OpenAI GPT + Spotify Seeds"
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
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
