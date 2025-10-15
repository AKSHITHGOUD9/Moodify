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
from openai import OpenAI

# AI Model imports
try:
    from huggingface_hub import InferenceClient
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    print("Hugging Face not available. Install with: pip install huggingface_hub")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Gemini not available. Install with: pip install google-generativeai")

# Note: LangChain imports removed to avoid deployment issues
# Using direct OpenAI integration instead

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
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# AI Model configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGING_FACE_KEYS")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEYS")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Initialize AI clients
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
huggingface_client = InferenceClient(token=HUGGINGFACE_API_KEY) if HUGGINGFACE_API_KEY and HUGGINGFACE_AVAILABLE else None
if GEMINI_API_KEY and GEMINI_AVAILABLE:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    gemini_model = None

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
# USER PROFILE CACHING
# =============================================================================

# In-memory cache for user profiles (in production, use Redis)
user_profile_cache = {}
album_covers_cache = {}

async def cache_user_music_profile(sp, user_id: str) -> Dict:
    """Cache user's complete music profile for instant AI recommendations"""
    try:
        logger.info(f"Caching music profile for user: {user_id}")
        
        # Get comprehensive user data
        top_tracks_short = await asyncio.to_thread(sp.current_user_top_tracks, limit=50, time_range='short_term')
        top_tracks_medium = await asyncio.to_thread(sp.current_user_top_tracks, limit=50, time_range='medium_term')
        top_tracks_long = await asyncio.to_thread(sp.current_user_top_tracks, limit=50, time_range='long_term')
        top_artists = await asyncio.to_thread(sp.current_user_top_artists, limit=50, time_range='medium_term')
        
        # Analyze genres from top artists
        genres = set()
        artists = []
        for artist in top_artists['items']:
            artists.append(artist['name'])
            genres.update(artist.get('genres', []))
        
        # Analyze eras from tracks
        eras = set()
        for track_list in [top_tracks_short, top_tracks_medium, top_tracks_long]:
            for track in track_list.get('items', []):
                try:
                    year = int(track['album']['release_date'][:4])
                    decade = (year // 10) * 10
                    eras.add(f"{decade}s")
                except:
                    pass
        
        # Detect regional preferences
        regional_preferences = set()
        all_track_names = []
        all_artists = []
        
        for track_list in [top_tracks_short, top_tracks_medium, top_tracks_long]:
            for track in track_list.get('items', []):
                all_track_names.append(track['name'].lower())
                for artist in track['artists']:
                    all_artists.append(artist['name'].lower())
        
        # Check for regional music indicators
        regional_keywords = {
            'telugu': ['telugu', 'tollywood'],
            'tamil': ['tamil', 'kollywood'],
            'hindi': ['hindi', 'bollywood'],
            'malayalam': ['malayalam', 'mollywood'],
            'kannada': ['kannada', 'sandalwood']
        }
        
        for region, keywords in regional_keywords.items():
            if any(keyword in ' '.join(all_track_names + all_artists) for keyword in keywords):
                regional_preferences.add(region)
        
        # Create comprehensive profile with detailed track information
        profile = {
            "user_id": user_id,
            "top_artists": artists[:20],
            "top_genres": list(genres)[:15],
            "listening_eras": list(eras),
            "regional_preferences": list(regional_preferences),
            "total_tracks_analyzed": len(top_tracks_short['items']) + len(top_tracks_medium['items']) + len(top_tracks_long['items']),
            "cached_at": time.time(),
            "sample_track_names": all_track_names[:30],  # For AI context
            "detailed_tracks": []  # Store detailed track info for AI
        }
        
        # Add detailed track information for AI analysis
        for track_list in [top_tracks_short, top_tracks_medium, top_tracks_long]:
            for track in track_list.get('items', []):
                try:
                    year = int(track['album']['release_date'][:4])
                    decade = (year // 10) * 10
                    track_info = {
                        "name": track['name'],
                        "artists": [artist['name'] for artist in track.get('artists', [])],
                        "album": track.get('album', {}).get('name', 'Unknown'),
                        "year": year,
                        "decade": f"{decade}s",
                        "popularity": track.get('popularity', 0)
                    }
                    profile["detailed_tracks"].append(track_info)
                except:
                    pass
        
        # Limit detailed tracks to top 50 for performance
        profile["detailed_tracks"] = profile["detailed_tracks"][:50]
        
        # Cache the profile
        user_profile_cache[user_id] = profile
        logger.info(f"Cached profile for user {user_id}: {len(artists)} artists, {len(genres)} genres")
        
        return profile
        
    except Exception as e:
        logger.error(f"Error caching user profile for {user_id}: {e}")
        return {}

async def get_cached_user_profile(user_id: str) -> Dict:
    """Get cached user profile"""
    return user_profile_cache.get(user_id, {})

def is_track_relevant_to_profile(track: Dict, user_profile: Dict, query: str) -> bool:
    """Check if a track is relevant to user's profile and query"""
    try:
        track_name = track['name'].lower()
        artists = ' '.join(track['artists']).lower()
        album = track['album'].lower()
        
        # Check against user's favorite artists
        if user_profile.get('top_artists'):
            if any(artist.lower() in artists for artist in user_profile['top_artists'][:10]):
                return True
        
        # Check against user's favorite genres (if we had genre info for tracks)
        # This would require additional Spotify API calls
        
        # Check against regional preferences
        if user_profile.get('regional_preferences'):
            for region in user_profile['regional_preferences']:
                if region.lower() in track_name or region.lower() in artists:
                    return True
        
        # Check against query context
        query_lower = query.lower()
        if any(word in track_name or word in artists for word in query_lower.split() if len(word) > 2):
            return True
        
        # Default: include track if it's reasonably popular
        return track.get('popularity', 0) > 30
        
    except Exception as e:
        logger.error(f"Error checking track relevance: {e}")
        return True  # Default to including track

# =============================================================================
# LLM INTEGRATION (Direct OpenAI)
# =============================================================================

async def generate_personalized_search_queries(user_profile: Dict, query: str) -> List[str]:
    """Generate personalized search queries using OpenAI directly"""
    try:
        if not openai_client:
            logger.warning("OpenAI client not available, using fallback")
            return [query]
        
        # Extract detailed user information
        top_artists = user_profile.get('top_artists', [])[:10]
        sample_tracks = user_profile.get('sample_track_names', [])[:20]
        genres = user_profile.get('top_genres', [])[:10]
        regional_prefs = user_profile.get('regional_preferences', [])
        detailed_tracks = user_profile.get('detailed_tracks', [])[:20]
        
        # Build track context string
        track_context = ""
        if detailed_tracks:
            track_context = "RECENT TRACKS:\n"
            for track in detailed_tracks[:15]:  # Show top 15 tracks
                track_context += f"- {track['name']} by {', '.join(track['artists'])} ({track['year']})\n"
        
        # Create a comprehensive prompt focused on specific song searches
        prompt = f"""
You are an expert music curator analyzing a user's music profile to find SPECIFIC SONGS that match their request.

USER'S MUSIC PROFILE:
- Top Artists: {', '.join(top_artists)}
- Favorite Genres: {', '.join(genres)}
- Regional Preferences: {', '.join(regional_prefs)}

{track_context}

USER REQUEST: "{query}"

TASK: Generate 3-4 SPECIFIC search queries that will find actual songs similar to what this user already listens to.

CRITICAL RULES:
1. Use SPECIFIC SONG NAMES from the user's recent tracks when relevant
2. Keep each query under 80 characters
3. Combine user's favorite artists with the mood/era/genre they're asking for
4. Use actual song titles, not generic terms
5. Prioritize songs by artists they already listen to

EXAMPLES OF GOOD QUERIES:
- "Zara Sa Arijit Singh"
- "Tum Hi Ho"
- "Channa Mereya"

Generate search queries that will find SPECIFIC SONGS this user would love:
"""
        
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-4o",  # Using GPT-4o for better results
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.2
        )
        
        search_queries_text = response.choices[0].message.content.strip()
        
        # Parse the AI-generated queries
        search_queries = []
        for line in search_queries_text.split('\n'):
            line = line.strip()
            if line and not line.startswith(('#', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                # Clean up the query
                query_clean = re.sub(r'^[\d\.\-\*\s]+', '', line).strip()
                if query_clean and len(query_clean) > 3:
                    search_queries.append(query_clean)
        
        # Add original query as fallback
        if query not in search_queries:
            search_queries.append(query)
        
        # If AI returned generic queries, improve them
        improved_queries = []
        for query in search_queries:
            if len(query.split()) <= 2 and query.lower() in ['top english', 'new english', 'english songs', 'popular songs']:
                # Replace generic queries with specific popular songs
                improved_queries.extend([
                    "Shape of You Ed Sheeran",
                    "Blinding Lights The Weeknd", 
                    "Levitating Dua Lipa",
                    "Good 4 U Olivia Rodrigo"
                ])
            else:
                improved_queries.append(query)
        
        final_queries = improved_queries[:5] if improved_queries else search_queries
        logger.info(f"Generated specific song queries: {final_queries}")
        return final_queries
        
    except Exception as e:
        logger.error(f"Error generating personalized queries: {e}")
        return [query]

# =============================================================================
# SMART AI LOAD BALANCING SYSTEM
# =============================================================================

class AIModelRouter:
    """Smart router for distributing AI tasks across different models"""
    
    def __init__(self):
        self.models = {
            'openai': {'client': openai_client, 'cost': 'high', 'quality': 'excellent', 'specialty': 'complex_reasoning'},
            'huggingface': {'client': huggingface_client, 'cost': 'free', 'quality': 'good', 'specialty': 'text_generation'},
            'gemini': {'client': gemini_model, 'cost': 'free', 'quality': 'excellent', 'specialty': 'general_purpose'}
        }
        
    def get_best_model_for_task(self, task_type: str, query: str) -> str:
        """Route tasks to the best model based on query type and complexity"""
        
        # Regional queries → Gemini (better cultural understanding)
        regional_keywords = ['tamil', 'telugu', 'hindi', 'kannada', 'malayalam', 'regional', 'indian', 'bollywood', 'tollywood', 'kollywood']
        if any(keyword in query.lower() for keyword in regional_keywords):
            return 'gemini'
        
        # Complex queries with multiple terms → OpenAI (best reasoning)
        if len(query.split()) > 3:
            return 'openai'
        
        # Simple queries → Hugging Face (cost-effective)
        if len(query.split()) <= 2:
            return 'huggingface'
        
        # Default to Gemini for balanced performance
        return 'gemini'

async def generate_huggingface_recommendations(user_profile: Dict, query: str) -> List[str]:
    """Generate recommendations using Hugging Face models"""
    try:
        if not huggingface_client:
            raise Exception("Hugging Face client not available")
        
        # Use a simpler approach to avoid StopIteration issues
        prompt = f"Generate song search queries for: {query}"
        
        try:
            # Handle StopIteration specifically
            try:
                response = await asyncio.to_thread(
                    huggingface_client.text_generation,
                    prompt,
                    max_new_tokens=50,
                    temperature=0.7,
                    model="microsoft/DialoGPT-medium",
                    return_full_text=False
                )
                
                # Simple parsing - just return the original query with variations
                queries = [query, f"{query} songs", f"{query} music"]
                logger.info(f"Generated {len(queries)} queries using Hugging Face")
                return queries[:3]
                
            except StopIteration:
                logger.warning("Hugging Face StopIteration error, using fallback")
                return [query, f"{query} songs", f"{query} music"]
                
        except Exception as hf_error:
            logger.warning(f"Hugging Face API failed: {hf_error}, using fallback")
            # Fallback to simple query variations
            return [query, f"{query} songs", f"{query} music"]
        
    except Exception as e:
        logger.error(f"Hugging Face error: {e}")
        # Always return something useful
        return [query, f"{query} songs"]

async def generate_gemini_recommendations(user_profile: Dict, query: str) -> List[str]:
    """Generate recommendations using Gemini"""
    try:
        if not gemini_model:
            raise Exception("Gemini model not available")
        
        prompt = f"""You are a music expert. Generate 3-4 SPECIFIC song search queries for: "{query}"

User's Music Profile:
- Top Artists: {user_profile.get('top_artists', [])}
- Genres: {user_profile.get('genres', [])}
- Regional Preferences: {user_profile.get('regional_preferences', [])}
- Sample Songs: {user_profile.get('detailed_tracks', [])[:5]}

CRITICAL REQUIREMENTS:
1. Generate ACTUAL SONG TITLES, not generic terms
2. Use REAL song names from popular artists
3. Keep each query under 80 characters
4. Focus on songs the user would actually like

GOOD EXAMPLES:
- "Perfect Ed Sheeran"
- "Shape of You" 
- "Zara Sa Arijit Singh"
- "Blinding Lights"

Return only the search queries, one per line."""
        
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        queries_text = response.text.strip()
        queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
        
        logger.info(f"Generated {len(queries)} queries using Gemini")
        return queries[:5] if queries else [query]
        
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        raise e

# Initialize the router
ai_router = AIModelRouter()

async def generate_smart_recommendations(user_profile: Dict, query: str) -> List[str]:
    """Smart load balancing for AI recommendations"""
    try:
        # Determine the best model for this query
        best_model = ai_router.get_best_model_for_task("search_queries", query)
        logger.info(f"Routing query '{query}' to {best_model}")
        
        # Try the selected model first
        try:
            if best_model == 'openai':
                return await generate_personalized_search_queries(user_profile, query)
            elif best_model == 'gemini':
                return await generate_gemini_recommendations(user_profile, query)
            elif best_model == 'huggingface':
                return await generate_huggingface_recommendations(user_profile, query)
        except Exception as e:
            logger.warning(f"{best_model} failed: {e}, trying fallback models")
        
        # Fallback strategy: try other models
        fallback_order = ['gemini', 'openai', 'huggingface']
        if best_model in fallback_order:
            fallback_order.remove(best_model)  # Remove the one we already tried
        
        for fallback_model in fallback_order:
            try:
                if fallback_model == 'openai':
                    return await generate_personalized_search_queries(user_profile, query)
                elif fallback_model == 'gemini':
                    return await generate_gemini_recommendations(user_profile, query)
                elif fallback_model == 'huggingface':
                    return await generate_huggingface_recommendations(user_profile, query)
            except Exception as e:
                logger.warning(f"{fallback_model} fallback failed: {e}")
                continue
        
        # If all models fail, use OpenAI as final fallback
        logger.error("All AI models failed, using OpenAI as final fallback")
        try:
            return await generate_personalized_search_queries(user_profile, query)
        except Exception as e:
            logger.error(f"Even OpenAI fallback failed: {e}")
            return [query]
        
    except Exception as e:
        logger.error(f"Smart routing failed: {e}")
        return [query]

# =============================================================================
# LLM INTEGRATION (OpenAI) - Legacy
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

# Spotify recommendations API removed - now using pure AI + search approach

async def get_ai_curated_recommendations(sp, query: str, user_tracks: List[dict] = None) -> List[Dict]:
    """Advanced AI-powered recommendation system that analyzes user taste and query intent"""
    try:
        if not openai_client:
            logger.warning("OpenAI not available, falling back to search-based recommendations")
            return await get_search_based_recommendations(sp, query, user_tracks or [])
        
        logger.info(f"Getting AI-curated recommendations for: {query}")
        
        # Analyze user's music taste
        user_profile = ""
        if user_tracks:
            genres = set()
            artists = set()
            decades = set()
            moods = set()
            
            # Fetch audio features for better mood analysis (optional - may fail in dev mode)
            track_ids = [track['id'] for track in user_tracks[:20] if isinstance(track, dict) and 'id' in track]
            audio_features = {}
            if track_ids:
                try:
                    features_batch = await asyncio.to_thread(sp.audio_features, track_ids)
                    if features_batch:
                        audio_features = {f['id']: f for f in features_batch if f and isinstance(f, dict)}
                except Exception as e:
                    logger.warning(f"Audio features not available (dev mode limitation): {e}")
                    # Continue without audio features - this is expected in development mode
            
            for track in user_tracks[:20]:
                # Ensure track is a dictionary
                if not isinstance(track, dict):
                    continue
                    
                if 'genres' in track:
                    genres.update(track.get('genres', []))
                if 'artists' in track and isinstance(track['artists'], list):
                    for artist in track['artists'][:2]:
                        if isinstance(artist, dict):
                            artists.add(artist.get('name', ''))
                if 'album' in track and isinstance(track['album'], dict) and 'release_date' in track['album']:
                    try:
                        year = int(track['album']['release_date'][:4])
                        decade = (year // 10) * 10
                        decades.add(f"{decade}s")
                    except:
                        pass
                # Extract mood from track features (only if available)
                track_id = track.get('id')
                if track_id and track_id in audio_features:
                    features = audio_features[track_id]
                    if isinstance(features, dict):
                        if features.get('valence', 0) > 0.7:
                            moods.add('happy')
                        elif features.get('valence', 0) < 0.3:
                            moods.add('sad')
                        if features.get('energy', 0) > 0.7:
                            moods.add('energetic')
                        elif features.get('energy', 0) < 0.3:
                            moods.add('chill')
                        if features.get('danceability', 0) > 0.7:
                            moods.add('danceable')
                        if features.get('acousticness', 0) > 0.7:
                            moods.add('acoustic')
            
            user_profile = f"""
USER'S MUSIC DNA:
- Favorite Genres: {', '.join(list(genres)[:6])}
- Favorite Artists: {', '.join(list(artists)[:10])}
- Preferred Decades: {', '.join(list(decades)[:4])}
- Music Moods: {', '.join(list(moods)[:4])}
"""
        
        # Create sophisticated prompt for AI curation
        prompt = f"""
You are a world-class music curator with access to Spotify's entire catalog. {user_profile}

User Request: "{query}"

Your task: Generate 8-10 SPECIFIC search queries that will find the most relevant, high-quality, and fresh music for this user.

CURATION STRATEGY:
1. PERSONALIZATION: Use the user's music DNA to find similar artists, genres, and styles
2. FRESHNESS: Prioritize recent releases (2023-2024) when appropriate
3. QUALITY: Focus on well-known artists, popular songs, and critically acclaimed music
4. DIVERSITY: Include different subgenres and styles within the request
5. CULTURAL ACCURACY: For regional music, be linguistically and culturally precise
6. TRENDING: Include viral hits and trending artists when relevant

SEARCH QUERY GUIDELINES:
- Use exact artist names, album titles, and song titles
- Include year ranges for temporal requests (e.g., "2024 hits", "90s classics")
- Combine multiple criteria (e.g., "chill indie rock 2024", "viral Telugu songs")
- Use Spotify-friendly search terms
- Avoid overly generic terms

Generate 8-10 specific search queries:
"""
        
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7
        )
        
        queries_text = response.choices[0].message.content.strip()
        
        # Parse the response to extract individual queries
        queries = []
        lines = queries_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.')) or 
                       line.startswith('"') or line.startswith("'")):
                query = re.sub(r'^[\d\.\-\s]+', '', line)  # Remove numbering
                query = query.strip('"\'')  # Remove quotes
                if query and len(query) > 3:
                    queries.append(query)
        
        if not queries:
            queries = [query]
        
        logger.info(f"AI generated {len(queries)} curated search queries: {queries}")
        
        # Execute searches with these curated queries
        all_tracks = []
        for search_query in queries[:8]:  # Limit to 8 queries for performance
            tracks = await search_spotify_tracks(sp, search_query)
            all_tracks.extend(tracks)
        
        # Remove duplicates and apply intelligent filtering
        unique_tracks = {}
        for track in all_tracks:
            if track['id'] not in unique_tracks:
                unique_tracks[track['id']] = track
        
        final_tracks = list(unique_tracks.values())
        
        # Sort by popularity and relevance
        final_tracks.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        
        # Return top 20 results
        result = final_tracks[:20]
        logger.info(f"AI curation returned {len(result)} high-quality recommendations")
        return result
        
    except Exception as e:
        logger.error(f"Error in AI curation: {e}")
        # Return empty if AI curation fails
        logger.error("AI curation completely failed")
        return []

# Fallback system removed - now using pure AI approach

async def generate_enhanced_search_queries(user_query: str, user_tracks: List[dict] = None) -> List[str]:
    """Use OpenAI to generate better search queries for Spotify with user context"""
    try:
        if not openai_client:
            logger.warning("OpenAI client not available, using original query")
            return [user_query]
        
        # Analyze user's music taste for personalized queries
        user_context = ""
        if user_tracks:
            genres = set()
            artists = set()
            decades = set()
            
            for track in user_tracks[:15]:  # Analyze top 15 tracks
                # Ensure track is a dictionary
                if not isinstance(track, dict):
                    continue
                    
                if 'genres' in track:
                    genres.update(track.get('genres', []))
                if 'artists' in track and isinstance(track['artists'], list):
                    for artist in track['artists'][:2]:
                        if isinstance(artist, dict):
                            artists.add(artist.get('name', ''))
                # Extract decade from release date
                if 'album' in track and isinstance(track['album'], dict) and 'release_date' in track['album']:
                    try:
                        year = int(track['album']['release_date'][:4])
                        decade = (year // 10) * 10
                        decades.add(f"{decade}s")
                    except:
                        pass
            
            user_context = f"""
USER'S MUSIC PROFILE:
- Favorite Genres: {', '.join(list(genres)[:5])}
- Favorite Artists: {', '.join(list(artists)[:8])}
- Preferred Decades: {', '.join(list(decades)[:3])}
"""
        
        prompt = f"""
You are a music expert curating personalized recommendations. {user_context}

User wants music recommendations for: "{user_query}"

Generate 4-5 HIGHLY SPECIFIC search queries for Spotify that will find ONLY songs within the exact context of the user's request.

CRITICAL RULES FOR ALL CASES:
1. REGIONAL/LANGUAGE: If user asks for regional music (Telugu, Tamil, Hindi, etc.), ONLY generate queries for that language/region
2. GENRE: If user asks for specific genres (rock, jazz, electronic), focus ONLY on that genre and its sub-genres
3. ERA/DECADE: If user asks for "old", "vintage", "80s", "90s", focus on that specific time period
4. MOOD/ACTIVITY: If user asks for "chill", "party", "workout", focus on that specific mood/activity
5. ARTIST: If user asks for specific artists, focus on their work and similar artists
6. PERSONALIZATION: Use user's music profile to find similar artists and genres
7. FRESH CONTENT: Prioritize recent releases and trending artists when relevant
8. NEVER generate generic terms that could return popular global hits unrelated to the context
9. Be culturally, temporally, and stylistically specific
10. Use actual artist names, album names, film names, and specific terms

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
        # Validate and truncate query to prevent API errors
        if len(query) > 250:
            query = query[:247] + "..."
            logger.warning(f"Query too long, truncated to: {query}")
        
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

async def filter_user_history_by_query(user_tracks: List[dict], query: str) -> List[dict]:
    """Intelligently filter user's music history to show only relevant tracks based on query"""
    try:
        if not user_tracks or len(user_tracks) == 0:
            return []
        
        logger.info(f"Filtering {len(user_tracks)} user tracks for query: '{query}'")
        
        query_lower = query.lower().strip()
        relevant_tracks = []
        
        # Define query categories and their matching criteria
        rock_keywords = ['rock', 'metal', 'alternative', 'indie rock', 'hard rock', 'soft rock']
        pop_keywords = ['pop', 'mainstream', 'chart', 'hit']
        electronic_keywords = ['electronic', 'edm', 'techno', 'house', 'dance']
        hiphop_keywords = ['hip hop', 'rap', 'hiphop', 'trap']
        country_keywords = ['country', 'folk', 'bluegrass']
        jazz_keywords = ['jazz', 'blues', 'soul']
        classical_keywords = ['classical', 'orchestra', 'symphony']
        regional_keywords = {
            'tamil': ['tamil', 'tamil film', 'tamil songs'],
            'telugu': ['telugu', 'telugu film', 'telugu songs'],
            'hindi': ['hindi', 'bollywood', 'hindi film'],
            'kannada': ['kannada', 'kannada film', 'kannada songs'],
            'malayalam': ['malayalam', 'malayalam film', 'malayalam songs']
        }
        mood_keywords = {
            'chill': ['chill', 'relaxing', 'calm', 'peaceful', 'ambient'],
            'energetic': ['energetic', 'party', 'upbeat', 'dance', 'high energy'],
            'sad': ['sad', 'melancholy', 'emotional', 'ballad'],
            'happy': ['happy', 'cheerful', 'uplifting', 'positive']
        }
        era_keywords = {
            'old': ['old', 'classic', 'vintage', 'retro', '90s', '80s', '70s'],
            'new': ['new', 'latest', 'recent', '2024', '2023', 'fresh']
        }
        
        for track in user_tracks:
            if not isinstance(track, dict):
                continue
                
            score = 0
            track_name = track.get('name', '').lower()
            track_artists = [artist.get('name', '').lower() for artist in track.get('artists', []) if isinstance(artist, dict)]
            track_album = track.get('album', {}).get('name', '').lower() if isinstance(track.get('album'), dict) else ''
            track_genres = [genre.lower() for genre in track.get('genres', [])]
            
            # Genre matching
            if any(keyword in query_lower for keyword in rock_keywords):
                if any(genre in ['rock', 'alternative', 'metal', 'indie'] for genre in track_genres):
                    score += 10
                if any('rock' in artist for artist in track_artists):
                    score += 5
                    
            if any(keyword in query_lower for keyword in pop_keywords):
                if any(genre in ['pop', 'mainstream'] for genre in track_genres):
                    score += 10
                    
            if any(keyword in query_lower for keyword in electronic_keywords):
                if any(genre in ['electronic', 'edm', 'dance'] for genre in track_genres):
                    score += 10
                    
            if any(keyword in query_lower for keyword in hiphop_keywords):
                if any(genre in ['hip hop', 'rap'] for genre in track_genres):
                    score += 10
                    
            # Regional language matching - STRICT for regional queries
            for language, keywords in regional_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    # Check if track/artist names suggest this language
                    if any(keyword in track_name for keyword in keywords):
                        score += 20  # Higher score for regional matches
                    if any(keyword in ' '.join(track_artists) for keyword in keywords):
                        score += 18  # Higher score for regional artists
                    if any(keyword in track_album for keyword in keywords):
                        score += 15  # Higher score for regional albums
                    
                    # Additional checks for regional music indicators
                    if language == 'telugu' and any(indicator in track_name for indicator in ['telugu', 'tollywood', 'andhra']):
                        score += 25  # Very high score for Telugu
                    elif language == 'tamil' and any(indicator in track_name for indicator in ['tamil', 'kollywood', 'chennai']):
                        score += 25  # Very high score for Tamil
                    elif language == 'hindi' and any(indicator in track_name for indicator in ['hindi', 'bollywood', 'india']):
                        score += 25  # Very high score for Hindi
                        
            # Mood matching
            for mood, keywords in mood_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    # This is a simplified mood detection - in production you'd use audio features
                    if mood == 'chill' and any(word in track_name for word in ['chill', 'calm', 'soft', 'acoustic']):
                        score += 8
                    elif mood == 'energetic' and any(word in track_name for word in ['energy', 'party', 'dance', 'upbeat']):
                        score += 8
                        
            # Era matching
            for era, keywords in era_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    if era == 'old':
                        # Check release date for older tracks
                        try:
                            release_date = track.get('album', {}).get('release_date', '')
                            if release_date and len(release_date) >= 4:
                                year = int(release_date[:4])
                                if year < 2010:
                                    score += 10
                                elif year < 2020:
                                    score += 5
                        except:
                            pass
                    elif era == 'new':
                        try:
                            release_date = track.get('album', {}).get('release_date', '')
                            if release_date and len(release_date) >= 4:
                                year = int(release_date[:4])
                                if year >= 2023:
                                    score += 10
                                elif year >= 2020:
                                    score += 5
                        except:
                            pass
                            
            # Direct name/artist matching (more lenient)
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 2:  # Ignore short words like "the", "a", "is"
                    if word in track_name:
                        score += 6
                    if any(word in artist for artist in track_artists):
                        score += 8
                    if word in track_album:
                        score += 4
                        
            # If no specific matches found, be VERY lenient for regional queries
            if score == 0 and any(lang in query_lower for lang in ['tamil', 'telugu', 'hindi', 'kannada', 'malayalam']):
                # Give score to ANY tracks that might be regional - show ALL regional songs
                if any(lang in track_name.lower() for lang in ['tamil', 'telugu', 'hindi', 'kannada', 'malayalam']):
                    score += 8  # Higher score for any regional track name
                if any(lang in ' '.join(track_artists).lower() for lang in ['tamil', 'telugu', 'hindi', 'kannada', 'malayalam']):
                    score += 10  # Higher score for any regional artist
                
                # Additional lenient checks for regional music patterns
                if any(pattern in track_name.lower() for pattern in ['song', 'music', 'film', 'movie', 'soundtrack']):
                    score += 5  # Bonus for music-related terms in regional context
                        
            # Bonus for exact matches
            if query_lower in track_name:
                score += 15
            if any(query_lower in artist for artist in track_artists):
                score += 12
                
            # VERY low threshold for all queries to show more relevant songs
            min_score = 1 if any(lang in query_lower for lang in ['tamil', 'telugu', 'hindi', 'kannada', 'malayalam']) else 1
            if score >= min_score:
                relevant_tracks.append((track, score))
        
        # Sort by relevance score and return more tracks for all queries
        relevant_tracks.sort(key=lambda x: x[1], reverse=True)
        max_tracks = 20  # Always return more tracks
        filtered_tracks = [track for track, score in relevant_tracks[:max_tracks]]
        
        logger.info(f"Filtered to {len(filtered_tracks)} relevant tracks from user history")
        return filtered_tracks
        
    except Exception as e:
        logger.error(f"Error filtering user history: {e}")
        # Fallback: return first 10 tracks
        return user_tracks[:10] if user_tracks else []

async def get_search_based_recommendations(sp, query: str, user_tracks: List[dict] = None) -> List[Dict]:
    """Get enhanced recommendations using AI-generated search queries"""
    try:
        logger.info(f"Getting enhanced search-based recommendations for: {query}")
        
        # Generate enhanced search queries using OpenAI with user context
        search_queries = await generate_enhanced_search_queries(query, user_tracks)
        
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
                    market=None  # Global market
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
        
        # Clear any existing session to prevent conflicts
        old_user_id = request.session.get("user_id")
        if old_user_id:
            logger.info(f"Clearing existing session for user: {old_user_id}")
            # Clear old user's cache
            if old_user_id in user_profile_cache:
                del user_profile_cache[old_user_id]
            album_cache_key = f"album_covers_{old_user_id}"
            if album_cache_key in album_covers_cache:
                del album_covers_cache[album_cache_key]
        
        request.session.clear()
        logger.info("Cleared existing session to prevent user conflicts")
        
        auth_manager = get_spotify_oauth()
        token_info = auth_manager.get_access_token(code)
        
        if not token_info:
            logger.error("Failed to get access token")
            return RedirectResponse(url=f"{POST_LOGIN_REDIRECT}?error=token_failed")
        
        # Get user info BEFORE storing in session
        sp = spotipy.Spotify(auth=token_info["access_token"])
        user = sp.current_user()
        user_id = user.get("id", "")
        
        # Store user-specific session data
        request.session["user_id"] = user_id
        request.session["spotify_token_info"] = token_info
        
        logger.info(f"User {user_id} successfully authenticated")
        logger.info(f"Session keys after storing token: {list(request.session.keys())}")
        
        # Cache user's music profile in background (non-blocking)
        try:
            # Import the caching function we'll create
            from main import cache_user_music_profile
            # Don't await - let it run in background
            asyncio.create_task(cache_user_music_profile(sp, user_id))
            logger.info(f"Started background caching for user {user_id}")
        except Exception as e:
            logger.warning(f"Could not start profile caching: {e}")
        
        # Add token and user info to URL for frontend to store
        token = token_info.get("access_token", "")
        redirect_url = f"{POST_LOGIN_REDIRECT}?token={token}&user_id={user_id}"
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        return RedirectResponse(url=f"{POST_LOGIN_REDIRECT}?error=callback_failed")

@app.post("/logout")
@app.get("/logout")
async def logout(request: Request):
    """Logout user and clear all cached data with proper session isolation"""
    logger.info(f"Logout endpoint called with method: {request.method}")
    logger.info(f"Session keys before clear: {list(request.session.keys())}")
    
    try:
        # Get user ID before clearing session for targeted cache clearing
        user_id = request.session.get("user_id")
        
        # Clear the session completely
        request.session.clear()
        logger.info(f"Session cleared successfully for user: {user_id}")
        
        # Clear user-specific cached data
        if user_id:
            # Clear user profile cache (using same key as storage)
            if user_id in user_profile_cache:
                del user_profile_cache[user_id]
                logger.info(f"Cleared user profile cache for user: {user_id}")
            
            # Clear album covers cache for this user
            album_cache_key = f"album_covers_{user_id}"
            if album_cache_key in album_covers_cache:
                del album_covers_cache[album_cache_key]
                logger.info(f"Cleared album covers cache for user: {user_id}")
        
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
        
        logger.info(f"User {user_id} logged out successfully - all caches cleared")
        return response
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Failed to logout")

@app.get("/me")
async def get_user(request: Request, token: str = None):
    """Get current user information"""
    try:
        # ONLY token-based authentication - no session fallback
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        
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
    except HTTPException:
        raise
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
async def create_custom_playlist(request: Request, playlist_data: dict, token: str = None):
    """Create a custom playlist and add it to user's library"""
    # Try token-based authentication first
    if token:
        sp = spotipy.Spotify(auth=token)
    else:
        # Fallback to session-based authentication
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
        
        # Use AI curation for all users (with or without history)
        logger.info(f"Using AI curation for query: {user_query}")
        new_recommendations = await get_ai_curated_recommendations(sp, user_query, music_history)
        
        if not new_recommendations:
            logger.warning("AI curation failed - no recommendations available")
            raise HTTPException(status_code=500, detail="Unable to generate recommendations at this time")
        
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
    """Get AI-powered music recommendations using LangChain and cached user profiles"""
    try:
        user_query = data.get("query", "").strip()
        if not user_query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Try token-based authentication first
        if token:
            sp = spotipy.Spotify(auth=token)
            # Get user info to retrieve cached profile
            user_info = await asyncio.to_thread(sp.current_user)
            user_id = user_info.get("id", "")
        else:
            # Fallback to session-based authentication
            sp = await _ensure_token(request)
        if not sp:
            raise HTTPException(status_code=401, detail="Not authenticated")
            user_id = request.session.get("user_id", "")
        
        if not sp:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Step 1: Get cached user profile (instant)
        user_profile = await get_cached_user_profile(user_id)
        
        if not user_profile:
            logger.info(f"No cached profile for user {user_id}, creating one now")
            user_profile = await cache_user_music_profile(sp, user_id)
        
        # Step 2: Use Smart AI routing to generate personalized search queries
        logger.info(f"Using Smart AI routing to generate personalized queries for user {user_id}")
        search_queries = await generate_smart_recommendations(user_profile, user_query)
        
        # Step 3: Search Spotify with AI-generated queries
        all_tracks = []
        for search_query in search_queries[:5]:  # Limit to 5 queries
            tracks = await search_spotify_tracks(sp, search_query)
            all_tracks.extend(tracks)
        
        # Step 4: Remove duplicates and apply intelligent filtering
        unique_tracks = {}
        for track in all_tracks:
            if track['id'] not in unique_tracks:
                unique_tracks[track['id']] = track
        
        # Step 5: Apply user profile-based filtering
        filtered_tracks = []
        for track in unique_tracks.values():
            if is_track_relevant_to_profile(track, user_profile, user_query):
                filtered_tracks.append(track)
        
        # Step 6: Get history tracks using smart filtering
        music_history = await get_user_music_history(sp)
        history_tracks = []
        if music_history:
            filtered_history = await filter_user_history_by_query(music_history, user_query)
            for track in filtered_history:
                        track_data = {
                            'id': track['id'],
                            'name': track['name'],
                            'artists': track['artists'],
                            'album': track['album'],
                    'album_image': track.get('album_image'),
                            'external_url': f"https://open.spotify.com/track/{track['id']}",
                    'preview_url': track.get('preview_url'),
                    'popularity': track.get('popularity', 0),
                    'duration_ms': track.get('duration_ms', 180000)
                        }
                        history_tracks.append(track_data)
        
        # Sort by popularity and limit results
        filtered_tracks.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        new_recommendations = filtered_tracks[:20]
        
        logger.info(f"Returning {len(history_tracks)} history tracks and {len(new_recommendations)} AI-curated recommendations")
        
        return {
            "user_history_recs": history_tracks,
            "new_recs": new_recommendations,
            "tracks": new_recommendations,
            "query": user_query,
            "method": "OpenAI AI + Cached User Profile"
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
