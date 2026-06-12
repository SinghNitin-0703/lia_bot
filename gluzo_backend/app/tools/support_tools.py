import json
import logging
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Order, User

logger = logging.getLogger(__name__)

def escalate_to_human(name: str, contact_info: str, problem_summary: str) -> str:
    """
    Sends the customer's personal data and a summary of their problem to the human customer care team.
    Always use this tool for ANY customer support issue (returns, tracking, complaints, etc.).
    
    Args:
        name: The customer's full name.
        contact_info: The customer's email or phone number.
        problem_summary: A brief summary of the customer's issue.
    """
    logger.info(f"Escalating to human: Name: {name}, Contact: {contact_info}, Problem: {problem_summary}")
    
    return json.dumps({
        "status": "Success",
        "message": "Your request has been successfully forwarded to our customer care team. They will contact you shortly.",
        "ticket_details": {
            "name": name,
            "contact": contact_info,
            "issue": problem_summary
        }
    }, indent=2)


async def update_user_profile(session_id: str, name: str = "", skin_type: str = "", skin_issues: str = "") -> str:
    """
    Saves or updates the user's personal profile in the database.
    Use this tool secretly whenever the user mentions their name, skin type, or skin issues.
    
    Args:
        session_id: The user's session ID.
        name: The user's name (if mentioned).
        skin_type: The user's skin type, e.g., 'dry', 'oily', 'combination' (if mentioned).
        skin_issues: Any skin concerns or allergies, e.g., 'acne', 'rosacea', 'allergic to vitamin c' (if mentioned).
    """
    logger.info(f"Updating profile for {session_id} - Name: {name}, Skin: {skin_type}, Issues: {skin_issues}")
    
    try:
        async with AsyncSessionLocal() as session:
            # 1. Find the user in the database, or create them if they don't exist
            result = await session.execute(select(User).where(User.session_id == session_id))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.info(f"User {session_id} not found. Creating a new user profile on the fly.")
                user = User(session_id=session_id, has_ordered=False, preferences="{}")
                session.add(user)
                await session.flush()  # assign an ID without committing yet
                
            # 2. Load existing preferences so we don't overwrite old data
            try:
                # Parse the JSON string into a Python dictionary
                # If it's empty, create a new dictionary
                current_prefs = json.loads(user.preferences) if user.preferences and user.preferences != "{}" else {}
            except json.JSONDecodeError:
                current_prefs = {}
                
            # 3. Update only the fields that were provided by the AI
            if name:
                current_prefs["name"] = name
            if skin_type:
                current_prefs["skin_type"] = skin_type
            if skin_issues:
                current_prefs["skin_issues"] = skin_issues
                
            # 4. Save it back to the user object as a JSON string
            user.preferences = json.dumps(current_prefs)
            
            # 5. Commit the changes to the database
            await session.commit()
            
            return json.dumps({
                "status": "Success",
                "message": "User profile updated successfully."
            })
            
    except Exception as e:
        logger.error(f"Error updating user profile for {session_id}: {e}", exc_info=True)
        return json.dumps({"error": "Failed to update database."})
