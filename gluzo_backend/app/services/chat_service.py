import logging
import base64
from app.cache import session_manager, semantic_cache
from app.agents.router import process_user_query
from app.managers.connection_manager import manager
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models import User
import json

logger = logging.getLogger(__name__)

class ChatService:
    @staticmethod
    async def get_user_preferences(session_id: str) -> str:
        """funxtion summary and flow in very short  """
        """
        Helper to fetch Long-Term Memory (preferences) from the database.
        Returns a formatted string of the user's saved name, skin type, etc.
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(User).where(User.session_id == session_id))
                user = result.scalar_one_or_none()
                if user and user.preferences and user.preferences != "{}":
                    # Convert JSON string back to a dictionary
                    prefs = json.loads(user.preferences)
                    # Format it nicely for the AI to read
                    pref_list = [f"{k.replace('_', ' ').title()}: {v}" for k, v in prefs.items()]
                    return ", ".join(pref_list)
        except Exception as e:
            logger.error(f"Failed to fetch preferences for {session_id}: {e}")
        return "No known preferences yet."

    @staticmethod
    async def get_short_term_memory(session_id: str) -> str:
        """funxtion summary and flow in very short  """
        """
        Helper to fetch Short-Term Memory (the last 5 messages from the live chat).
        This gives the AI context of the current conversation.
        """
        history = await session_manager.get_raw_history(session_id)
        
        # We check if there's 1 or 0 messages because the current message is ALREADY in the history
        if not history or len(history) <= 1:
            return "No previous messages in this session."
            
        # Grab the last 4 messages, EXCLUDING the very last one (which is the current user query)
        recent_history = history[:-1][-4:]
        
        formatted_history = ""
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "AI Assistant"
            formatted_history += f"{role}: {msg['content']}\n"
            
        return formatted_history




    @staticmethod
    def is_personal_query(message: str) -> bool:
        """
        SECURITY FIX: Checks if a query is likely asking for personalized information.
        If it is, we should NOT use the global semantic cache to prevent data leaks.
        """
        # A simple list of words that usually mean the user is talking about themselves or their account
        personal_keywords = [
            "i", "my", "me", "mine", "myself",
            "order", "ord-", "account", "profile", 
            "track", "return", "refund", "cart",
            "name", "address"
        ]
        
        # Make the message lowercase and split it into individual words
        words = message.lower().split()
        
        # Check if any personal word is in the message
        for word in words:
            # Clean punctuation from the word (like "order?" -> "order")
            clean_word = ''.join(char for char in word if char.isalnum() or char == '-')
            if clean_word in personal_keywords:
                return True
                
        return False

    @staticmethod
    async def process_standard_chat(session_id: str, message: str) -> str:
        """funxtion summary and flow in very short  """
        """
        Processes a synchronous chat request from a web frontend.
        """
        # Add the user's message to the session history
        await session_manager.add_to_history(session_id, "user", message)
        
        # SECURITY FIX: Determine if we should even use the cache
        # We don't want to serve someone else's personal info to this user!
        is_personal = ChatService.is_personal_query(message)
        
        # Check the semantic cache first (ONLY if it's a general, non-personal query)
        if not is_personal:
            cached_response = await semantic_cache.get_cached_response(message)
            if cached_response:
                logger.info(f"Cache hit! Returning cached response for session {session_id}")
                await session_manager.add_to_history(session_id, "assistant", cached_response)
                return cached_response
        
        # Get the current items in the user's cart
        cart = await session_manager.get_cart_state(session_id)
        cart_str = ", ".join(cart) if cart else "Empty"
        
        # Fetch our new Memories!
        long_term_memory = await ChatService.get_user_preferences(session_id)
        short_term_memory = await ChatService.get_short_term_memory(session_id)
        
        # Build the context string
        context_str = (
            f"Active Cart: {cart_str}\n\n"
            f"--- LONG-TERM MEMORY (User Profile) ---\n"
            f"{long_term_memory}\n\n"
            f"--- SHORT-TERM MEMORY (Recent Chat History) ---\n"
            f"{short_term_memory}"
        )
        
        # Process the query using our AI agent router
        try:
            logger.info("Processing query with the AI agent...")
            response_text = await process_user_query(session_id, message, context_str)
        except Exception as e:
            # Fallback message if the AI fails
            logger.error(f"Agent execution failed for session {session_id}: {e}", exc_info=True)
            response_text = "I'm having trouble connecting to my brain right now. Please try again later."
            
        # Check if we should recommend any additional products based on what's in the cart
        # Feature removed per user request.
        
        # Save the response to the semantic cache for future use (ONLY if it's general knowledge)
        if not is_personal:
            await semantic_cache.cache_response(message, response_text)
            logger.info("Saved general response to semantic cache.")
        else:
            logger.info("Skipped caching because the query was personalized.")
            
        # Save the assistant's final response to the history
        await session_manager.add_to_history(session_id, "assistant", response_text)
        
        return response_text


