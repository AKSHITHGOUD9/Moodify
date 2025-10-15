"""AI models service for recommendations"""

import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

from ..config import settings
from ..utils.exceptions import AIAPIError

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        
    def generate_search_queries(self, user_query: str, user_profile: Dict[str, Any] = None) -> List[str]:
        """Generate specific search queries for Spotify"""
        if not self.openai_client:
            return [user_query]
        
        try:
            profile_context = ""
            if user_profile:
                artists = user_profile.get('top_artists', [])[:10]
                genres = user_profile.get('top_genres', [])[:10]
                profile_context = f"""
User's top artists: {', '.join(artists)}
User's top genres: {', '.join(genres)}
"""
            
            prompt = f"""Generate 5 specific search queries for Spotify based on this request: "{user_query}"

{profile_context}

Return actual song titles with artist names, not generic terms. Examples:
- "Perfect Ed Sheeran"
- "Bohemian Rhapsody Queen"
- "Shape of You Ed Sheeran"

Format as a JSON array of strings."""

            response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                import json
                queries = json.loads(content)
                if isinstance(queries, list):
                    return queries[:5]
            except:
                pass
            
            return [user_query]
            
        except Exception as e:
            logger.error(f"OpenAI query generation failed: {e}")
            return [user_query]
    
    def filter_recommendations(self, tracks: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Filter and rank recommendations based on query"""
        if not tracks:
            return []
        
        if not self.openai_client:
            return tracks[:10]
        
        try:
            track_names = [track.get('name', '') for track in tracks[:20]]
            
            prompt = f"""Rate these songs (1-10) for the query "{query}":
{track_names}

Return JSON with song names as keys and scores as values."""

            response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                import json
                scores = json.loads(content)
                scored_tracks = []
                
                for track in tracks:
                    score = scores.get(track.get('name', ''), 5)
                    scored_tracks.append((track, score))
                
                scored_tracks.sort(key=lambda x: x[1], reverse=True)
                return [track for track, score in scored_tracks[:10]]
                
            except:
                pass
            
            return tracks[:10]
            
        except Exception as e:
            logger.error(f"AI filtering failed: {e}")
            return tracks[:10]
