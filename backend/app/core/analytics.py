"""Analytics service"""

import logging
from typing import Dict, Any, List

from .spotify import SpotifyService
from ..utils.helpers import format_duration

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        self.spotify_service = SpotifyService()
    
    async def get_user_analytics(self, access_token: str) -> Dict[str, Any]:
        """Get comprehensive user analytics"""
        try:
            user = self.spotify_service.get_user_profile(access_token)
            top_tracks = self.spotify_service.get_user_top_tracks(access_token, limit=20)
            top_artists = self.spotify_service.get_user_top_artists(access_token, limit=10)
            recent_tracks = self.spotify_service.get_recently_played(access_token, limit=20)
            
            return {
                "user": user,
                "top_tracks": self._format_tracks(top_tracks),
                "top_artists": self._format_artists(top_artists),
                "recent_tracks": self._format_tracks(recent_tracks),
                "stats": self._calculate_stats(top_tracks, top_artists, recent_tracks)
            }
            
        except Exception as e:
            logger.error(f"Analytics generation failed: {e}")
            raise
    
    async def get_user_playlists(self, access_token: str) -> Dict[str, Any]:
        """Get user's playlists"""
        try:
            sp = self.spotify_service.get_spotify_client(access_token)
            playlists = sp.current_user_playlists(limit=20)
            
            return {
                "playlists": playlists.get('items', []),
                "total": playlists.get('total', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get playlists: {e}")
            raise
    
    def _format_tracks(self, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format tracks for frontend"""
        formatted = []
        for i, track in enumerate(tracks, 1):
            formatted.append({
                "rank": i,
                "id": track.get('id'),
                "name": track.get('name'),
                "artists": [artist['name'] for artist in track.get('artists', [])],
                "album": track.get('album', {}).get('name'),
                "duration": format_duration(track.get('duration_ms', 0)),
                "album_image": track.get('album', {}).get('images', [{}])[0].get('url'),
                "external_url": track.get('external_urls', {}).get('spotify')
            })
        return formatted
    
    def _format_artists(self, artists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format artists for frontend"""
        formatted = []
        for artist in artists:
            formatted.append({
                "id": artist.get('id'),
                "name": artist.get('name'),
                "genres": artist.get('genres', [])[:3],
                "followers": artist.get('followers', {}).get('total', 0),
                "image": artist.get('images', [{}])[0].get('url'),
                "external_url": artist.get('external_urls', {}).get('spotify')
            })
        return formatted
    
    def _calculate_stats(self, top_tracks: List, top_artists: List, recent_tracks: List) -> Dict[str, Any]:
        """Calculate user statistics"""
        total_playtime = sum(track.get('duration_ms', 0) for track in top_tracks)
        
        genres = []
        for artist in top_artists:
            genres.extend(artist.get('genres', []))
        
        genre_counts = {}
        for genre in genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_tracks": len(top_tracks),
            "total_artists": len(top_artists),
            "total_playtime": format_duration(total_playtime),
            "top_genres": [genre for genre, count in top_genres],
            "recent_plays": len(recent_tracks)
        }
