"""Recommendation engine"""

import logging
from typing import List, Dict, Any
import asyncio

from .spotify import SpotifyService
from .ai_models import AIService
from ..utils.cache import user_profile_cache, album_covers_cache
from ..utils.helpers import extract_track_info, clean_query

logger = logging.getLogger(__name__)

class RecommendationEngine:
    def __init__(self, spotify_service: SpotifyService, ai_service: AIService):
        self.spotify_service = spotify_service
        self.ai_service = ai_service
    
    async def generate_recommendations(self, query: str, access_token: str) -> Dict[str, Any]:
        """Generate AI-powered recommendations"""
        try:
            user_id = self.spotify_service.get_user_profile(access_token)['id']
            user_profile = self._get_user_profile(user_id, access_token)
            
            ai_queries = self.ai_service.generate_search_queries(query, user_profile)
            
            search_tasks = [
                self.spotify_service.search_tracks(access_token, q, limit=10)
                for q in ai_queries[:5]
            ]
            
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            all_tracks = []
            for result in search_results:
                if isinstance(result, list):
                    all_tracks.extend(result)
            
            unique_tracks = self._deduplicate_tracks(all_tracks)
            filtered_tracks = self.ai_service.filter_recommendations(unique_tracks, query)
            
            history_tracks = self._filter_user_history(access_token, query)
            
            # Format response to match old backend
            new_recommendations = [extract_track_info(track) for track in filtered_tracks[:20]]
            
            return {
                "user_history_recs": history_tracks,
                "new_recs": new_recommendations,
                "tracks": new_recommendations,
                "query": query,
                "method": "AI-Powered Recommendations"
            }
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            raise
    
    async def get_user_album_covers(self, access_token: str) -> List[str]:
        """Get user's album covers for background"""
        try:
            user_id = self.spotify_service.get_user_profile(access_token)['id']
            
            cached_covers = album_covers_cache.get(f"covers_{user_id}")
            if cached_covers:
                return cached_covers
            
            recent_tracks = self.spotify_service.get_recently_played(access_token, limit=50)
            covers = []
            
            for track in recent_tracks:
                album_image = track.get('album', {}).get('images', [{}])[0].get('url')
                if album_image and album_image not in covers:
                    covers.append(album_image)
            
            album_covers_cache.set(f"covers_{user_id}", covers, ttl=3600)
            return covers
            
        except Exception as e:
            logger.error(f"Failed to get album covers: {e}")
            return []
    
    def _get_user_profile(self, user_id: str, access_token: str) -> Dict[str, Any]:
        """Get cached user profile"""
        cached_profile = user_profile_cache.get(f"profile_{user_id}")
        if cached_profile:
            return cached_profile
        
        try:
            top_artists = self.spotify_service.get_user_top_artists(access_token, limit=50)
            top_tracks = self.spotify_service.get_user_top_tracks(access_token, limit=50)
            
            artists = [artist['name'] for artist in top_artists]
            genres = []
            for artist in top_artists:
                genres.extend(artist.get('genres', []))
            
            profile = {
                'top_artists': artists,
                'top_genres': list(set(genres)),
                'total_tracks': len(top_tracks)
            }
            
            user_profile_cache.set(f"profile_{user_id}", profile, ttl=3600)
            return profile
            
        except Exception as e:
            logger.error(f"Failed to build user profile: {e}")
            return {}
    
    def _deduplicate_tracks(self, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate tracks"""
        seen = set()
        unique_tracks = []
        
        for track in tracks:
            if not isinstance(track, dict):
                continue
                
            track_id = track.get('id')
            if track_id and isinstance(track_id, str) and track_id not in seen:
                seen.add(track_id)
                unique_tracks.append(track)
        
        return unique_tracks
    
    def _filter_user_history(self, access_token: str, query: str) -> List[Dict[str, Any]]:
        """Filter user's history based on query"""
        try:
            recent_tracks = self.spotify_service.get_recently_played(access_token, limit=100)
            query_words = set(clean_query(query).split())
            
            relevant_tracks = []
            for track in recent_tracks:
                track_name = track.get('name', '').lower()
                artist_names = ' '.join([artist['name'].lower() for artist in track.get('artists', [])])
                track_text = f"{track_name} {artist_names}"
                
                if any(word in track_text for word in query_words if len(word) > 2):
                    relevant_tracks.append(extract_track_info(track))
            
            return relevant_tracks[:10]
            
        except Exception as e:
            logger.error(f"History filtering failed: {e}")
            return []
