"""Spotify API service wrapper"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import List, Dict, Any, Optional
import logging

from ..config import settings
from ..utils.exceptions import SpotifyAPIError

logger = logging.getLogger(__name__)

class SpotifyService:
    def __init__(self):
        self._oauth = None
    
    @property
    def oauth(self):
        if self._oauth is None:
            self._oauth = SpotifyOAuth(
                client_id=settings.SPOTIFY_CLIENT_ID,
                client_secret=settings.SPOTIFY_CLIENT_SECRET,
                redirect_uri=settings.SPOTIFY_REDIRECT_URI,
                scope="user-read-private user-read-email user-top-read user-read-recently-played playlist-read-private playlist-modify-public playlist-modify-private user-read-playback-state user-modify-playback-state user-read-playback-position user-library-read"
            )
        return self._oauth
    
    def get_spotify_client(self, access_token: str) -> spotipy.Spotify:
        """Create authenticated Spotify client"""
        try:
            return spotipy.Spotify(auth=access_token)
        except Exception as e:
            logger.error(f"Failed to create Spotify client: {e}")
            raise SpotifyAPIError(f"Authentication failed: {str(e)}")
    
    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            sp = self.get_spotify_client(access_token)
            return sp.current_user()
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            raise SpotifyAPIError(f"Failed to fetch user profile: {str(e)}")
    
    def get_user_top_tracks(self, access_token: str, limit: int = 50, time_range: str = "medium_term") -> List[Dict[str, Any]]:
        """Get user's top tracks"""
        try:
            sp = self.get_spotify_client(access_token)
            results = sp.current_user_top_tracks(limit=limit, time_range=time_range)
            return results.get('items', [])
        except Exception as e:
            logger.error(f"Failed to get top tracks: {e}")
            raise SpotifyAPIError(f"Failed to fetch top tracks: {str(e)}")
    
    def get_user_top_artists(self, access_token: str, limit: int = 50, time_range: str = "medium_term") -> List[Dict[str, Any]]:
        """Get user's top artists"""
        try:
            sp = self.get_spotify_client(access_token)
            results = sp.current_user_top_artists(limit=limit, time_range=time_range)
            return results.get('items', [])
        except Exception as e:
            logger.error(f"Failed to get top artists: {e}")
            raise SpotifyAPIError(f"Failed to fetch top artists: {str(e)}")
    
    def search_tracks(self, access_token: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for tracks"""
        try:
            sp = self.get_spotify_client(access_token)
            results = sp.search(q=query, type='track', limit=limit)
            return results.get('tracks', {}).get('items', [])
        except Exception as e:
            logger.error(f"Failed to search tracks: {e}")
            raise SpotifyAPIError(f"Search failed: {str(e)}")
    
    def create_playlist(self, access_token: str, user_id: str, name: str, track_ids: List[str]) -> Dict[str, Any]:
        """Create a playlist with tracks"""
        try:
            sp = self.get_spotify_client(access_token)
            
            playlist = sp.user_playlist_create(
                user=user_id,
                name=name,
                public=True,
                description="Created by Moodify - AI-powered music discovery"
            )
            
            if track_ids:
                sp.playlist_add_items(playlist['id'], track_ids)
            
            return {
                'id': playlist['id'],
                'name': playlist['name'],
                'tracks_added': len(track_ids),
                'external_urls': playlist['external_urls']
            }
        except Exception as e:
            logger.error(f"Failed to create playlist: {e}")
            raise SpotifyAPIError(f"Playlist creation failed: {str(e)}")
    
    def get_recently_played(self, access_token: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently played tracks"""
        try:
            sp = self.get_spotify_client(access_token)
            results = sp.current_user_recently_played(limit=limit)
            return [item['track'] for item in results.get('items', [])]
        except Exception as e:
            logger.error(f"Failed to get recently played: {e}")
            raise SpotifyAPIError(f"Failed to fetch recently played: {str(e)}")
