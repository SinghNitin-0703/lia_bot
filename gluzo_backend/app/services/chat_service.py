import logging
import base64
from app.cache import session_manager
from app.agents.router import process_user_query
from app.agents.consultation import contextual_upsell_check
from app.managers.connection_manager import manager
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models import User
import json

logger = logging.getLogger(__name__)

class ChatService:
    @staticmethod
    async def get_user_preferences(session_id: str) -> str:
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
    async def process_standard_chat(session_id: str, message: str) -> str:
        """
        Processes a synchronous chat request from a web frontend.
        """
        # Add the user's message to the session history
        await session_manager.add_to_history(session_id, "user", message)
        
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
        try:
            upsell = await contextual_upsell_check(session_id)
            if upsell:
                logger.info(f"Adding upsell recommendation for session {session_id}")
                response_text += upsell
        except Exception as upsell_error:
            logger.error(f"Upsell check failed: {upsell_error}", exc_info=True)
            
        # Save the assistant's final response to the history
        await session_manager.add_to_history(session_id, "assistant", response_text)
        
        return response_text


