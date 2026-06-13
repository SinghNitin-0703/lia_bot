import httpx
import logging
from typing import Optional
from app.config import settings
from app.schemas import CompetitorFormulaExtract
from app.database import AsyncSessionLocal
from app.models import Product
from sqlalchemy import select, or_
import json

logger = logging.getLogger(__name__)

async def research_competitor_product(product_name: str) -> CompetitorFormulaExtract:
    """funxtion summary and flow in very short  """
    """
    Uses the Tavily API to look up missing competitor ingredients.
    If the API key is missing or set to a mock, gracefully returns a simulated payload.
    """
    api_key = settings.TAVILY_API_KEY
    
    # ---------------------------------------------------------
    # Production Tavily API Call
    # ---------------------------------------------------------
    try:
        if not api_key:
            raise ValueError("Missing Tavily API key.")
            
        async with httpx.AsyncClient() as client:
            payload = {
                "api_key": api_key,
                "query": f"What are the active chemical ingredients and primary benefits of {product_name} skincare?",
                "search_depth": "advanced"
            }
            response = await client.post("https://api.tavily.com/search", json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Simple summarization strategy: grab snippet from top result
            top_result = data.get("results", [{}])[0].get("content", "")
            
            # In a true production environment, we'd pipe this snippet through an LLM to extract cleanly.
            # Here, we do a basic structural return.
            return CompetitorFormulaExtract(
                product_name=product_name,
                product_type="Analyzed Competitor Product",
                extracted_actives=["Extracted Actives from API"],
                primary_benefit=top_result[:200] + "..." # Truncate snippet
            )
            
    except (httpx.HTTPError, ValueError) as e:
        logger.error(f"Tavily API request failed or missing key: {str(e)}", exc_info=True)
        # Return an empty/error payload so the caller knows it failed
        return CompetitorFormulaExtract(
            product_name=product_name,
            product_type="Unknown",
            extracted_actives=[],
            primary_benefit="Error extracting data from external API."
        )

async def find_competitor_alternative(competitor_product_name: str) -> str:
    """
    Researches a competitor's product using external APIs and finds the closest matching alternative in our catalog based on ingredient overlap.
    Use this tool when a user asks for a specific brand or product that we DO NOT carry (e.g. CeraVe, Cetaphil, The Ordinary).
    
    Args:
        competitor_product_name: The exact name of the competitor's product to research.
        
    # Few-Shot Examples:
    <example>
    User: "Do you have something like CeraVe Hydrating Cleanser?"
    Tool Call: find_competitor_alternative(competitor_product_name="CeraVe Hydrating Cleanser")
    </example>
    """
    # 1. Research competitor via Tavily (or mock)
    competitor_data = await research_competitor_product(competitor_product_name)
    
    if not competitor_data.extracted_actives or "Unable to fetch" in competitor_data.extracted_actives[0]:
        return json.dumps({
            "status": "Error",
            "message": f"Could not extract ingredient data for {competitor_product_name}."
        })
        
    # 2. Find best match in our SQL database
    best_match = None
    max_shared_actives = 0
    shared_actives_list = []
    
    # Build query to ONLY fetch products that contain at least one of the competitor's active ingredients
    conditions = []
    for active in competitor_data.extracted_actives:
        conditions.append(Product.key_ingredients.ilike(f"%{active}%"))
        conditions.append(Product.key_benefits.ilike(f"%{active}%"))
        
    async with AsyncSessionLocal() as session:
        if conditions:
            query = select(Product).where(or_(*conditions))
            result = await session.execute(query)
            relevant_products = result.scalars().all()
        else:
            relevant_products = []
        
        for product in relevant_products:
            shared_count = 0
            current_shared = []
            ingredients = product.key_ingredients.lower()
            benefits = product.key_benefits.lower()
            
            for active in competitor_data.extracted_actives:
                if active.lower() in ingredients or active.lower() in benefits:
                    shared_count += 1
                    current_shared.append(active)
                    
            if shared_count > max_shared_actives:
                max_shared_actives = shared_count
                best_match = product
                shared_actives_list = current_shared
                
    # 3. Calculate percentage and format response
    if best_match and max_shared_actives > 0:
        match_percentage = int((max_shared_actives / len(competitor_data.extracted_actives)) * 100)
        
        # (Removed artificial mock boost)
        return json.dumps({
            "status": "Alternative Found",
            "competitor_product": competitor_data.product_name,
            "competitor_actives": competitor_data.extracted_actives,
            "our_alternative": best_match.name,
            "our_price": best_match.price,
            "shared_ingredients": shared_actives_list,
            "match_confidence": f"{match_percentage}%",
            "alternative_benefits": best_match.key_benefits,
            "our_image_url": best_match.image_urls
        }, indent=2)
        
    return json.dumps({
        "status": "No Alternative Found",
        "message": f"We researched {competitor_product_name} but could not find a suitable alternative in our catalog."
    })
