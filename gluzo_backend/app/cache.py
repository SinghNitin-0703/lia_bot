import logging
import asyncio
from typing import Dict, List, Optional, Any
from cachetools import TTLCache
from app.config import settings

# Set up logging for our cache manager
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Semantic Cache Manager
# ---------------------------------------------------------

class SemanticCacheManager:
    """
    An asynchronous manager for vector search embedding cache.
    It helps us remember answers to questions we've already seen,
    so we don't have to think as hard the next time!
    """
    
    def __init__(self):
        try:
            self.redis_url = settings.REDIS_URL
            
            # In a real production app, we would connect to a real Redis server here.
            # But for now, we use a simple TTLCache to prevent memory leaks.
            # Stores up to 1000 queries for 1 hour (3600 seconds)
            self._mock_cache = TTLCache(maxsize=1000, ttl=3600)
            # FIX for Issue #7: TTLCache race condition
            self._lock = asyncio.Lock()
            
            logger.info("Initialized SemanticCacheManager successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize SemanticCacheManager: {e}", exc_info=True)
            self._mock_cache = TTLCache(maxsize=1000, ttl=3600)
            self._lock = asyncio.Lock()
            
    async def get_cached_response(self, query: str) -> Optional[str]:
        """
        Attempts to find an exact match for a query in our cache.
        Returns the saved response if found, otherwise returns None.
        """
        try:
            # We convert the query to lowercase so it matches exactly
            async with self._lock:
                cached_item = self._mock_cache.get(query.lower())
            
            if cached_item:
                logger.info(f"Cache hit for query: '{query}'")
            else:
                logger.debug(f"Cache miss for query: '{query}'")
                
            return cached_item
        except Exception as e:
            logger.error(f"Error retrieving from cache for query '{query}': {e}", exc_info=True)
            return None
            
    async def cache_response(self, query: str, response: str) -> None:
        """
        Saves a query-response pair to the cache for future use.
        """
        try:
            # Save the answer using the lowercase query as the key
            async with self._lock:
                self._mock_cache[query.lower()] = response
            logger.info(f"Saved response to cache for query: '{query}'")
        except Exception as e:
            logger.error(f"Error saving to cache for query '{query}': {e}", exc_info=True)

# ---------------------------------------------------------
# Session State Manager
# ---------------------------------------------------------

class SessionStateManager:
    """
    Keeps track of what each user is doing during their visit.
    Tracks their shopping cart, the last item they looked at, and their chat history.
    """
    
    def __init__(self):
        # We store everything in a TTLCache to prevent unbounded memory growth.
        # Max 10,000 active sessions, expires after 24 hours (86400 seconds) of inactivity.
        self.sessions = TTLCache(maxsize=10000, ttl=86400)
        # FIX for Issue #7: TTLCache race condition
        self._lock = asyncio.Lock()
        logger.info("Initialized SessionStateManager.")
        
    async def _initialize_session(self, session_id: str) -> None:
        """
        Creates a new empty session for a user if they don't have one yet.
        """
        try:
            async with self._lock:
                if session_id not in self.sessions:
                    self.sessions[session_id] = {
                        "owner_id": session_id,  # Track owner to prevent TTLCache collisions
                        "cart_state": [],
                        "last_viewed_sku": None,
                        "raw_history": []
                    }
                    logger.info(f"Created new session state for user: {session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize session for {session_id}: {e}", exc_info=True)
            
    async def get_cart_state(self, session_id: str) -> List[str]:
        """Returns the list of items in the user's cart."""
        try:
            await self._initialize_session(session_id)
            async with self._lock:
                data = self.sessions[session_id]
                # FIX for Issue #8 (Corrected): Upsell cart internal leak.
                # Validate that the slot hasn't been corrupted or mis-assigned by TTLCache
                if data.get("owner_id") != session_id:
                    logger.warning(f"Session mismatch detected! {session_id} != {data.get('owner_id')}")
                    return []
                return data["cart_state"]
        except Exception as e:
            logger.error(f"Error getting cart state for {session_id}: {e}", exc_info=True)
            return []
            
    async def set_cart_state(self, session_id: str, cart: List[str]) -> None:
        """Updates the list of items in the user's cart."""
        try:
            await self._initialize_session(session_id)
            async with self._lock:
                session_data = self.sessions[session_id]
                session_data["cart_state"] = cart
                self.sessions[session_id] = session_data  # Explicit re-assignment resets TTL
            logger.info(f"Updated cart for {session_id} with {len(cart)} items.")
        except Exception as e:
            logger.error(f"Error setting cart state for {session_id}: {e}", exc_info=True)
            
    async def get_last_viewed_sku(self, session_id: str) -> Optional[str]:
        """Returns the SKU of the last product the user viewed."""
        try:
            await self._initialize_session(session_id)
            async with self._lock:
                return self.sessions[session_id]["last_viewed_sku"]
        except Exception as e:
            logger.error(f"Error getting last viewed SKU for {session_id}: {e}", exc_info=True)
            return None
            
    async def set_last_viewed_sku(self, session_id: str, sku: str) -> None:
        """Saves the SKU of the product the user is currently looking at."""
        try:
            await self._initialize_session(session_id)
            async with self._lock:
                session_data = self.sessions[session_id]
                session_data["last_viewed_sku"] = sku
                self.sessions[session_id] = session_data  # Explicit re-assignment resets TTL
            logger.debug(f"Set last viewed SKU to {sku} for {session_id}")
        except Exception as e:
            logger.error(f"Error setting last viewed SKU for {session_id}: {e}", exc_info=True)
            
    async def add_to_history(self, session_id: str, role: str, message: str) -> None:
        """
        Adds a message to the user's chat history.
        Role is usually 'user' or 'assistant'.
        """
        try:
            await self._initialize_session(session_id)
            async with self._lock:
                session_data = self.sessions[session_id]
                session_data["raw_history"].append({
                    "role": role, 
                    "content": message
                })
                self.sessions[session_id] = session_data  # Explicit re-assignment resets TTL
            logger.debug(f"Added {role} message to history for {session_id}")
        except Exception as e:
            logger.error(f"Error adding to history for {session_id}: {e}", exc_info=True)
            
    async def get_raw_history(self, session_id: str) -> List[Dict[str, str]]:
        """Returns the complete chat history for a user."""
        try:
            await self._initialize_session(session_id)
            async with self._lock:
                return self.sessions[session_id]["raw_history"]
        except Exception as e:
            logger.error(f"Error getting history for {session_id}: {e}", exc_info=True)
            return []

# ---------------------------------------------------------
# Global Instances
# ---------------------------------------------------------
# We create one instance of each manager to be used everywhere in our app
semantic_cache = SemanticCacheManager()
session_manager = SessionStateManager()
