from agno.agent import Agent
from agno.models.azure import AzureOpenAI
from app.config import settings
from app.cache import session_manager
from app.schemas import ProductSchema
from app.database import AsyncSessionLocal
from app.models import Product as DBProduct
from sqlalchemy import select, or_
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Skincare Consultation Agent Configuration
# ---------------------------------------------------------

Skincare_Consultation_Agent = Agent(
    name="ConsultationAgent",
    model=AzureOpenAI(
        id="gpt-4.1-mini-2",
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_version="2024-12-01-preview"
    ),
    description="You are an encouraging, knowledgeable skincare expert specializing in product layering.",
    instructions="""
    You are an encouraging, knowledgeable skincare expert. You specialize in explaining how to layer products and creating customized routines.
    
    # Responsibilities
    - Explain product benefits clearly.
    - Provide step-by-step routines.
    - Always check the user's cart state to offer contextual advice.

    # Examples
    User: "How should I layer my Vitamin C and Retinol?"
    Response: "Vitamin C is best used in the morning to protect against free radicals, while Retinol should be used at night to aid in cellular turnover. Never layer them at the same time to avoid irritation!"
    
    User: "What does niacinamide do?"
    Response: "Niacinamide is a fantastic multi-tasking ingredient! It helps build keratin, strengthens your lipid barrier, minimizes redness, and regulates oil production."
    """,
)

async def contextual_upsell_check(session_id: str) -> str:
    """
    Screens the active cart_state. If a heavy active (e.g., BHA) is detected without a barrier repair item,
    injects a recommendation for a repair item (e.g., Plum 2% Niacinamide Gel Cream).
    """
    cart = await session_manager.get_cart_state(session_id)
    if not cart:
        return ""
        
    has_heavy_active = False
    has_barrier_repair = False
    
    async with AsyncSessionLocal() as session:
        # Build conditions to match against either Product ID or Product Name
        conditions = []
        for sku in cart:
            if sku.isdigit():
                conditions.append(DBProduct.id == int(sku))
            conditions.append(DBProduct.name.ilike(sku))
            
        # Only fetch products that are actually in the cart
        query = select(DBProduct).where(or_(*conditions))
        result = await session.execute(query)
        cart_products = result.scalars().all()

        for product in cart_products:
            ingredients = product.key_ingredients.lower()
            benefits = product.key_benefits.lower()
            
            if "bha" in ingredients or "aha" in ingredients or "salicylic" in ingredients or "retinol" in ingredients:
                has_heavy_active = True
                
            if "ceramide" in ingredients or "niacinamide" in ingredients or "barrier" in benefits:
                has_barrier_repair = True
                
    if has_heavy_active and not has_barrier_repair:
        logger.info("Triggered contextual upsell for barrier repair.")
        return "\n\n[SYSTEM UPSELL TRIGGER]: The user has a strong active in their cart but no barrier repair. Naturally inject a recommendation for a hydrating/repair item, like the Plum 2% Niacinamide Gel Cream, to balance their routine."
        
    return ""
