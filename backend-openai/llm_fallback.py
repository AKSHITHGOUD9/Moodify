"""
LLM Fallback System for Moodify
==============================

This module provides intelligent fallback recommendations when LLM is not available.
Uses keyword matching, genre analysis, and Spotify's built-in recommendation features.

Author: Moodify Development Team
Version: 1.0.0
"""

import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def select_tracks_fallback(query: str, music_history: List[Dict]) -> List[str]:
    """
    Fallback track selection using keyword matching and scoring.
    This replaces LLM functionality when cloud LLM is not available.
    """
    try:
        if not music_history:
            logger.warning("No music history available for fallback selection")
            return []
        
        query_lower = query.lower()
        logger.info(f"Using fallback track selection for query: {query}")
        
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
            'pop': ['pop', 'popular', 'mainstream', 'radio'],
            'rock': ['rock', 'guitar', 'band', 'alternative'],
            'electronic': ['electronic', 'edm', 'dance', 'house', 'techno', 'trance'],
            'hip_hop': ['hip hop', 'rap', 'trap', 'r&b', 'soul'],
            'jazz': ['jazz', 'smooth', 'bebop', 'fusion'],
            'classical': ['classical', 'orchestral', 'symphony', 'piano'],
            'country': ['country', 'folk', 'bluegrass', 'acoustic'],
            'reggae': ['reggae', 'dub', 'ska', 'caribbean'],
            'punk': ['punk', 'hardcore', 'emo', 'alternative'],
            'lofi': ['lofi', 'chill', 'ambient', 'study', 'relaxing']
        }
        
        # Mood keywords
        mood_keywords = {
            'happy': ['happy', 'upbeat', 'cheerful', 'positive', 'joyful', 'energetic'],
            'sad': ['sad', 'melancholy', 'depressing', 'emotional', 'heartbreak'],
            'romantic': ['romantic', 'love', 'intimate', 'passionate', 'relationship'],
            'party': ['party', 'celebration', 'festive', 'dance', 'club'],
            'workout': ['workout', 'gym', 'energy', 'upbeat', 'motivation'],
            'focus': ['focus', 'concentration', 'productivity', 'work', 'study'],
            'sleep': ['sleep', 'relaxing', 'calm', 'peaceful', 'meditation'],
            'nostalgic': ['nostalgic', 'retro', 'vintage', 'throwback', 'old']
        }
        
        # Era keywords
        era_keywords = {
            'old': ['old', 'classic', 'vintage', 'retro', '80s', '90s', '2000s'],
            'new': ['new', 'recent', 'latest', 'modern', 'current', '2020s'],
            '80s': ['80s', 'eighties', '80\'s', '1980s'],
            '90s': ['90s', 'nineties', '90\'s', '1990s'],
            '2000s': ['2000s', '2000\'s', 'early 2000s']
        }
        
        # Score tracks based on query matching
        scored_tracks = []
        
        for track in music_history:
            track_name = track.get('name', '').lower()
            artists = ', '.join(track.get('artists', [])).lower()
            album = track.get('album', '').lower()
            track_text = f"{track_name} {artists} {album}".lower()
            
            match_score = 0
            match_reasons = []
            
            # Check for language matches (highest priority)
            for lang, keywords in language_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    if any(keyword in track_text for keyword in keywords):
                        match_score += 10
                        match_reasons.append(f"language:{lang}")
                        break
            
            # Check for genre matches
            for genre, keywords in genre_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    if any(keyword in track_text for keyword in keywords):
                        match_score += 8
                        match_reasons.append(f"genre:{genre}")
                        break
            
            # Check for mood matches
            for mood, keywords in mood_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    if any(keyword in track_text for keyword in keywords):
                        match_score += 6
                        match_reasons.append(f"mood:{mood}")
                        break
            
            # Check for era matches
            for era, keywords in era_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    if any(keyword in track_text for keyword in keywords):
                        match_score += 4
                        match_reasons.append(f"era:{era}")
                        break
            
            # Check for direct text matches in track name or artist
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 2:  # Only consider words longer than 2 characters
                    if word in track_name:
                        match_score += 5
                        match_reasons.append(f"name_match:{word}")
                    elif word in artists:
                        match_score += 3
                        match_reasons.append(f"artist_match:{word}")
            
            # Add track with match score and reasons
            track_with_score = {
                **track,
                'match_score': match_score,
                'match_reasons': match_reasons
            }
            
            scored_tracks.append(track_with_score)
        
        # Sort by match score (highest first)
        scored_tracks.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Select top tracks
        selected_tracks = scored_tracks[:10]
        
        # Log selection results
        if selected_tracks and selected_tracks[0]['match_score'] > 0:
            logger.info(f"Fallback selected {len(selected_tracks)} tracks with scores:")
            for i, track in enumerate(selected_tracks[:5]):
                logger.info(f"  {i+1}. {track['name']} by {track['artists'][0]} (score: {track['match_score']}, reasons: {track['match_reasons']})")
        else:
            logger.info("No specific matches found, selecting diverse tracks")
            # If no matches, select diverse tracks from different time periods
            selected_tracks = select_diverse_tracks(music_history, 10)
        
        return [track['id'] for track in selected_tracks if track.get('id')]
        
    except Exception as e:
        logger.error(f"Error in fallback track selection: {e}")
        # Return first 10 tracks as last resort
        return [track['id'] for track in music_history[:10] if track.get('id')]

def select_diverse_tracks(music_history: List[Dict], count: int) -> List[Dict]:
    """Select diverse tracks from different time periods and sources"""
    try:
        # Group tracks by time_range
        time_groups = {}
        for track in music_history:
            time_range = track.get('time_range', 'unknown')
            if time_range not in time_groups:
                time_groups[time_range] = []
            time_groups[time_range].append(track)
        
        # Select tracks from each group
        selected = []
        for time_range, tracks in time_groups.items():
            # Take up to 3 tracks from each time period
            selected.extend(tracks[:3])
            if len(selected) >= count:
                break
        
        # If we still need more, add from any remaining tracks
        if len(selected) < count:
            remaining = [t for t in music_history if t not in selected]
            selected.extend(remaining[:count - len(selected)])
        
        return selected[:count]
        
    except Exception as e:
        logger.error(f"Error selecting diverse tracks: {e}")
        return music_history[:count]

