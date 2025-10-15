"""Helper utility functions"""

import re
from typing import List, Dict, Any, Optional

def format_duration(milliseconds: int) -> str:
    """Convert milliseconds to MM:SS format"""
    seconds = milliseconds // 1000
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"

def extract_track_info(track_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract essential track information from Spotify API response"""
    return {
        'id': track_data.get('id'),
        'name': track_data.get('name'),
        'artists': [{'name': artist['name'], 'id': artist['id']} for artist in track_data.get('artists', [])],
        'album': {
            'name': track_data.get('album', {}).get('name'),
            'id': track_data.get('album', {}).get('id'),
            'images': track_data.get('album', {}).get('images', [])
        },
        'duration_ms': track_data.get('duration_ms', 0),
        'preview_url': track_data.get('preview_url'),
        'external_urls': track_data.get('external_urls', {}),
        'album_image': track_data.get('album', {}).get('images', [{}])[0].get('url') if track_data.get('album', {}).get('images') else None
    }

def clean_query(query: str) -> str:
    """Clean and normalize search query"""
    return re.sub(r'[^\w\s]', '', query.lower().strip())

def is_valid_spotify_id(track_id: str) -> bool:
    """Validate Spotify track ID format"""
    return bool(re.match(r'^[a-zA-Z0-9]{22}$', track_id))
