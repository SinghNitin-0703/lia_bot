import logging
import asyncio
from agno.agent import Agent
from agno.models.azure import AzureOpenAI
from app.config import settings

# Import our specialized sub-agents
from app.agents.search import Product_Search_Agent
from app.agents.support import Customer_Support_Agent
from app.agents.consultation import Skincare_Consultation_Agent
from app.tools.support_tools import update_user_profile

# Set up logging so we can track the routing process
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Supervisor / Router Agent Configuration
# ---------------------------------------------------------

# We define the static structural prompt. 
# By placing this at the top, we optimize for Prompt Caching 
# (the AI can cache these rules across requests to save time and money).
ROUTER_SYSTEM_PROMPT = """
You are the Master Supervisor Agent for Gluzo, a premium skincare e-commerce platform.
Your job is to route the user's request to the correct specialized agent, or handle general queries yourself.

# Available Sub-Agents
1. Product_Search_Agent: Use for finding products, checking prices, applying budget math, and allergen filtering.
2. Customer_Support_Agent: Use for collecting personal info and escalating all customer support issues (order tracking, returns, complaints) to the human care team.
3. Skincare_Consultation_Agent: Use for routine advice and product layering guides.

# Routing Rules
- Analyze the user's intent.
- If the user query is extreme gibberish (e.g., random keystrokes like 'asdfasdfasdf'), do not delegate. Reply directly asking the user to clarify.
- If the user asks about topics outside of skincare, hair, or body care (e.g., math, history, geography, politics, clothes, fashion, etc.), DO NOT delegate. Reply EXACTLY with: "We dont do that here 🙅‍♂️🙅‍♀️"
- If they want to buy something or search the catalog, delegate to Product_Search_Agent.
  **CRITICAL (Search):** Before delegating, you MUST rewrite the `query` to be fully self-contained by resolving any pronouns or references from the [DYNAMIC CONTEXT]. (e.g., if user says "which of those 3 is best", rewrite as "Which is best between Lotus Neem Wash, Tea Tree Wash, and Swiss CC Cream?").
- If they have a problem with an order or need support, delegate to Customer_Support_Agent.
  **CRITICAL (Support):** Rewrite the `query` to include order numbers or details mentioned in the history.
- If they need advice on a routine, delegate to Skincare_Consultation_Agent.
  **CRITICAL (Consultation):** Pass the exact [DYNAMIC CONTEXT] provided to you into the `context_and_history` parameter so the consultation agent can read the full history.
- For simple greetings, you may respond directly.

# CRITICAL DELEGATION RULE
- When you delegate to a sub-agent (like Product_Search_Agent), it will return a detailed markdown response containing the answer (and images).
- ONCE YOU RECEIVE THE OUTPUT FROM THE SUB-AGENT, YOU MUST IMMEDIATELY OUTPUT THAT EXACT MARKDOWN RESPONSE TO THE USER WITHOUT CALLING THE TOOL AGAIN.
- DO NOT summarize or alter the sub-agent's response. DO NOT strip markdown links or images. Simply pass the sub-agent's text directly back to the user.
- NEVER call the same sub-agent more than once per user request.

# Compulsory Data Collection (Name Requirement)
- Check the [DYNAMIC CONTEXT] at the bottom of the prompt.
- If the User's "Name" is NOT listed in the LONG-TERM MEMORY (or if it says "No known preferences yet"):
   - FIRST, check if the user is providing their name in the current `<user_query>`.
   - If they ARE providing their name, IMMEDIATELY call the `update_user_profile` tool to save it. After saving, you may proceed to answer their original request.
   - If they are NOT providing their name, you MUST NOT process their request yet. Instead, politely ask for their name (e.g., "Hi there! Before I help you find that, could I get your name so I can personalize your experience?").

# User Profiling (Secret Task)
- You have access to the `update_user_profile` tool.
- If the user EVER mentions their name, skin type, or skin issues, ALWAYS call the `update_user_profile` tool in the background to save it to their database profile. Do this quietly without making a big deal out of it.

# Examples
User: "I need a moisturizer for dry skin."
Action: Call Product_Search_Agent. Output its result.

User: "Where is order ORD-123?"
Action: Call Customer_Support_Agent. Output its result.
"""

# Wrap the sub-agents in Python functions so they work flawlessly as standard tools.
async def search_products_expert(query: str) -> str:
    """
    Delegate the user's product search query to the Product Search Expert.
    Make sure the `query` is fully rewritten to include all context and resolves pronouns (like 'it', 'above', 'those').
    """
    logger.info(f"Delegating to Product_Search_Agent with query: {query}")
    try:
        response = await Product_Search_Agent.arun(query)
        return response.content if response and response.content else "No results found."
    except Exception as e:
        logger.error(f"Error in Product_Search_Agent: {e}")
        return "I encountered an error searching for products."

async def customer_support_expert(query: str) -> str:
    """
    Delegate the user's customer support/order query to the Customer Support Expert.
    Make sure the `query` is fully rewritten with specific order numbers from context.
    """
    logger.info(f"Delegating to Customer_Support_Agent with query: {query}")
    try:
        response = await Customer_Support_Agent.arun(query)
        return response.content if response and response.content else "Could not process support query."
    except Exception as e:
        logger.error(f"Error in Customer_Support_Agent: {e}")
        return "I encountered an error processing your support request."

async def skincare_consultation_expert(query: str, context_and_history: str) -> str:
    """
    Delegate the user's skincare routine or consultation query to the Skincare Consultation Expert.
    
    Args:
        query: The user's specific request.
        context_and_history: You MUST copy and paste the entire [DYNAMIC CONTEXT] provided to you into this parameter.
    """
    logger.info(f"Delegating to Skincare_Consultation_Agent with query: {query}")
    
    # Combine context and query so the stateless sub-agent has full awareness
    full_prompt = (
        f"--- CONTEXT & HISTORY ---\n"
        f"{context_and_history}\n\n"
        f"--- CURRENT USER QUERY ---\n"
        f"{query}"
    )
    
    try:
        response = await Skincare_Consultation_Agent.arun(full_prompt)
        return response.content if response and response.content else "Could not process consultation query."
    except Exception as e:
        logger.error(f"Error in Skincare_Consultation_Agent: {e}")
        return "I encountered an error during your consultation."

# Create the main Supervisor Agent
Gluzo_Supervisor_Agent = Agent(
    name="SupervisorAgent",
    model=AzureOpenAI(
        id="gpt-4.1-mini-2",
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_version="2024-12-01-preview"
    ),
    description="You are the master router for the Gluzo backend.",
    instructions=ROUTER_SYSTEM_PROMPT,
    tools=[search_products_expert, customer_support_expert, skincare_consultation_expert, update_user_profile],
)

async def process_user_query(session_id: str, query: str, context_string: str) -> str:
    """
    Executes a query against the Supervisor Agent.
    The dynamic context_string is injected at the bottom so the AI knows the user's current situation.
    """
    try:
        logger.info(f"Processing query for session {session_id}")
        
        safe_query = query.replace("<", "").replace(">", "")
        
        full_prompt = (
            f"<user_query>\n{safe_query}\n</user_query>\n\n"
            f"[DYNAMIC CONTEXT]\n"
            f"User Session ID / Phone Number: {session_id}\n"
            f"{context_string}"
        )
        
        response = await Gluzo_Supervisor_Agent.arun(full_prompt)
        
        if not response or not response.content:
            logger.error(f"Agno returned an empty response for session {session_id}. Content filters may have blocked it.")
            return "I'm having a little trouble thinking right now. Could you please try again?"
            
        logger.info(f"Successfully generated response for session {session_id}")
        return response.content
        
    except Exception as e:
        logger.error(f"Error while the Supervisor Agent was processing the query: {e}", exc_info=True)
        return "I'm having a little trouble thinking right now. Could you please try again?"
