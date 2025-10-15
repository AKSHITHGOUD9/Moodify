"""Custom exceptions for the application"""

class MoodifyException(Exception):
    """Base exception for Moodify application"""
    pass

class SpotifyAPIError(MoodifyException):
    """Spotify API related errors"""
    pass

class AIAPIError(MoodifyException):
    """AI service API related errors"""
    pass

class AuthenticationError(MoodifyException):
    """Authentication related errors"""
    pass

class CacheError(MoodifyException):
    """Cache related errors"""
    pass
