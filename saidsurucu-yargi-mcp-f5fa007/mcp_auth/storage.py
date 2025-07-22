"""
Persistent storage for OAuth sessions and tokens
"""

import json
import os
import tempfile
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PersistentStorage:
    """File-based persistent storage for OAuth data"""
    
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            # Use system temp directory or environment variable
            storage_dir = os.environ.get('TEMP', tempfile.gettempdir())
        
        self.storage_dir = os.path.join(storage_dir, 'mcp_oauth_storage')
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.sessions_file = os.path.join(self.storage_dir, 'oauth_sessions.json')
        self.tokens_file = os.path.join(self.storage_dir, 'oauth_tokens.json')
        
        logger.info(f"Persistent OAuth storage initialized at: {self.storage_dir}")
    
    def _load_json(self, filepath: str) -> Dict:
        """Load JSON data from file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
        return {}
    
    def _save_json(self, filepath: str, data: Dict):
        """Save JSON data to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")
    
    def get_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all OAuth sessions"""
        data = self._load_json(self.sessions_file)
        # Clean expired sessions
        now = datetime.utcnow().timestamp()
        valid_sessions = {k: v for k, v in data.items() 
                         if v.get('expires_at', 0) > now}
        if len(valid_sessions) != len(data):
            self._save_json(self.sessions_file, valid_sessions)
        return valid_sessions
    
    def set_session(self, session_id: str, data: Dict[str, Any]):
        """Set OAuth session data"""
        sessions = self.get_sessions()
        sessions[session_id] = data
        self._save_json(self.sessions_file, sessions)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get specific OAuth session data"""
        sessions = self.get_sessions()
        return sessions.get(session_id)
    
    def delete_session(self, session_id: str):
        """Delete OAuth session"""
        sessions = self.get_sessions()
        if session_id in sessions:
            del sessions[session_id]
            self._save_json(self.sessions_file, sessions)
    
    def get_tokens(self) -> Dict[str, Dict[str, Any]]:
        """Get all OAuth tokens"""
        data = self._load_json(self.tokens_file)
        # Clean expired tokens
        now = datetime.utcnow().timestamp()
        valid_tokens = {k: v for k, v in data.items() 
                       if v.get('expires_at', 0) > now}
        if len(valid_tokens) != len(data):
            self._save_json(self.tokens_file, valid_tokens)
        return valid_tokens
    
    def set_token(self, token_id: str, token_data: Dict[str, Any]):
        """Set OAuth token data"""
        tokens = self.get_tokens()
        tokens[token_id] = token_data
        self._save_json(self.tokens_file, tokens)
    
    def get_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get specific OAuth token data"""
        tokens = self.get_tokens()
        return tokens.get(token_id)
    
    def delete_token(self, token_id: str):
        """Delete OAuth token"""
        tokens = self.get_tokens()
        if token_id in tokens:
            del tokens[token_id]
            self._save_json(self.tokens_file, tokens)
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions and tokens"""
        # This is handled automatically in get_sessions() and get_tokens()
        sessions = self.get_sessions()
        tokens = self.get_tokens()
        logger.debug(f"Cleanup: {len(sessions)} active sessions, {len(tokens)} active tokens")