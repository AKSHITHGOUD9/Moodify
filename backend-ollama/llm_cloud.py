"""
Cloud LLM Integration for Moodify
================================

This module provides cloud-based LLM alternatives to replace local Ollama.
Supports OpenAI, Anthropic, and other cloud providers.

Author: Moodify Development Team
Version: 1.0.0
"""

import os
import requests
import json
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class CloudLLM:
    """Base class for cloud LLM providers"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    async def select_tracks(self, query: str, music_history: List[Dict]) -> List[str]:
        """Select tracks from music history based on query"""
        raise NotImplementedError

class OpenAILLM(CloudLLM):
    """OpenAI GPT integration"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, model)
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    async def select_tracks(self, query: str, music_history: List[Dict]) -> List[str]:
        """Use OpenAI to select tracks from history"""
        try:
            # Prepare history text
            history_text = "\n".join([
                f"ID: {track['id']}, Name: {track['name']}, Artists: {', '.join(track['artists'])}, Album: {track['album']}"
                for track in music_history[:50]  # Limit to 50 tracks for token efficiency
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

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
            
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            llm_response = result['choices'][0]['message']['content'].strip()
            
            # Parse JSON response
            cleaned_response = llm_response.replace('```json', '').replace('```', '').strip()
            track_ids = json.loads(cleaned_response)
            
            # Validate track IDs
            valid_ids = [tid for tid in track_ids if isinstance(tid, str) and len(tid) == 22]
            
            if len(valid_ids) >= 5:  # Need at least 5 valid IDs
                logger.info(f"OpenAI selected {len(valid_ids)} valid track IDs from history")
                return valid_ids[:10]  # Return max 10
            else:
                logger.warning(f"OpenAI returned only {len(valid_ids)} valid IDs")
                return valid_ids
            
        except Exception as e:
            logger.error(f"Error querying OpenAI: {e}")
            return []

class AnthropicLLM(CloudLLM):
    """Anthropic Claude integration"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        super().__init__(api_key, model)
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    async def select_tracks(self, query: str, music_history: List[Dict]) -> List[str]:
        """Use Anthropic Claude to select tracks from history"""
        try:
            # Similar implementation to OpenAI but with Claude's API format
            history_text = "\n".join([
                f"ID: {track['id']}, Name: {track['name']}, Artists: {', '.join(track['artists'])}, Album: {track['album']}"
                for track in music_history[:50]
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

            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": 500,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            llm_response = result['content'][0]['text'].strip()
            
            # Parse JSON response
            cleaned_response = llm_response.replace('```json', '').replace('```', '').strip()
            track_ids = json.loads(cleaned_response)
            
            # Validate track IDs
            valid_ids = [tid for tid in track_ids if isinstance(tid, str) and len(tid) == 22]
            
            if len(valid_ids) >= 5:
                logger.info(f"Anthropic selected {len(valid_ids)} valid track IDs from history")
                return valid_ids[:10]
            else:
                logger.warning(f"Anthropic returned only {len(valid_ids)} valid IDs")
                return valid_ids
            
        except Exception as e:
            logger.error(f"Error querying Anthropic: {e}")
            return []

def get_llm_client():
    """Get the configured LLM client based on environment variables"""
    llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if llm_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return OpenAILLM(api_key, os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))
    
    elif llm_provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        return AnthropicLLM(api_key, os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"))
    
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}")

