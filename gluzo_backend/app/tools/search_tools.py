import json
import logging
from rapidfuzz import process, fuzz
from sqlalchemy import select, not_

from app.database import AsyncSessionLocal
from app.models import Product

logger = logging.getLogger(__name__)

from app.search_engine import hybrid_search_engine

async def match_product_term(search_term: str, excluded_ingredients: list[str] = [], max_budget: float = None, sort_by: str = "relevance") -> str:
    """
    Finds products using an Industry Standard Hybrid Search (Vector Semantic + BM25 Lexical) via Reciprocal Rank Fusion.
    Also strictly filters out any products containing excluded_ingredients and applies max_budget if provided.
    
    Args:
        search_term: The complex query, symptom, or exact name of the product the user wants.
        excluded_ingredients: A list of strings representing allergens (e.g. ['fragrance', 'niacinamide']).
        max_budget: Optional float for the maximum allowable price.
        sort_by: Optional sorting strategy: 'relevance', 'popularity', 'price_low', 'price_high'.
    """
    logger.info(f"Initiating Hybrid Search for '{search_term}'. Exclusions: {excluded_ingredients}, Max Budget: {max_budget}, Sort By: {sort_by}")
    
    try:
        # Call the new robust hybrid search engine which fuses Vector and BM25 scores
        top_results = await hybrid_search_engine.search(
            query=search_term, 
            top_k=3, 
            excluded_ingredients=excluded_ingredients,
            max_price=max_budget,
            sort_by=sort_by
        )
        
        if not top_results:
            return json.dumps({"error": "No matching products found that meet the safety and budget criteria."})
            
        # Return the top 3 matches so the AI has options (e.g. to find the most popular one)
        formatted_results = []
        for match in top_results:
            formatted_results.append({
                "matched_name": match["matched_name"],
                "price": match["price"],
                "rating": match.get("rating", 0),
                "review_count": match.get("review_count", 0),
                "key_benefits": match["key_benefits"],
                "how_to_use": match["how_to_use"],
                "image_url": match.get("image_urls", "")
            })
            
        return json.dumps({"top_matches": formatted_results}, indent=2)
            
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}", exc_info=True)
        return json.dumps({"error": "Failed to perform search."})

async def optimize_budget_combinations(
    max_budget: float, 
    product_type_1: str, 
    product_type_2: str, 
    excluded_ingredients: list[str] = None
) -> str:
    """
    Math Engine: Finds the highest-rated combination of two product types under a specific budget cap.
    Takes active discounts into account and strictly filters out allergens.
    """
    try:
        # 1. Setup: If no allergens are provided, use an empty list
        if excluded_ingredients is None:
            excluded_ingredients = []
            
        # 3. Database Fetch: Only download the specific products we need
        # (Replaced raw SQL fetch with Hybrid Search to ensure relevance)
        type_1_candidates = await hybrid_search_engine.search(
            query=product_type_1,
            top_k=20,
            excluded_ingredients=excluded_ingredients
        )
        
        type_2_candidates = await hybrid_search_engine.search(
            query=product_type_2,
            top_k=20,
            excluded_ingredients=excluded_ingredients
        )
            
        logger.info(f"Budget Optimizer found {len(type_1_candidates)} safe candidates for '{product_type_1}' and {len(type_2_candidates)} safe candidates for '{product_type_2}'.")
                
        valid_combinations = []
        
        # 4. Math Engine: Try combining every safe item from category 1 with category 2
        for p1 in type_1_candidates:
            for p2 in type_2_candidates:
                # Prevent recommending the exact same product twice
                if p1["matched_name"] == p2["matched_name"]:
                    continue
                    
                # Calculate the real price (after discounts)
                price_1 = p1["price"] * (1 - (p1.get("discount", 0.0) / 100)) if p1.get("discount") else p1["price"]
                price_2 = p2["price"] * (1 - (p2.get("discount", 0.0) / 100)) if p2.get("discount") else p2["price"]
                total_cost = price_1 + price_2
                
                # If they fit the budget, give them a "Value Score"
                if total_cost <= max_budget:
                    # Value Score = Average rating amplified by total number of reviews
                    rating1 = p1.get("rating", 4.0)
                    rating2 = p2.get("rating", 4.0)
                    reviews1 = p1.get("review_count", 0)
                    reviews2 = p2.get("review_count", 0)
                    
                    value_score = ((rating1 + rating2) / 2) * (reviews1 + reviews2)
                    
                    valid_combinations.append({
                        "item_1": p1["matched_name"],
                        "image_url_1": p1.get("image_urls", ""),
                        "item_2": p2["matched_name"],
                        "image_url_2": p2.get("image_urls", ""),
                        "total_cost": round(total_cost, 2),
                        "value_score": round(value_score, 2)
                    })
                    
        # 5. Error Handling: What if nothing fits the budget?
        if not valid_combinations:
            return json.dumps({
                "error": f"Impossible to find safe combinations of {product_type_1} and {product_type_2} under ₹{max_budget}."
            })
            
        # 6. Sorting: Put the combinations with the highest Value Score at the top
        sorted_combos = sorted(valid_combinations, key=lambda x: x["value_score"], reverse=True)
        
        # Return the top 3 best choices
        return json.dumps({"top_combinations": sorted_combos[:3]}, indent=2)
        
    except Exception as e:
        # Master Error Handler: Catch any unexpected crashes (like database connection issues)
        logger.error(f"Budget optimization failed: {e}", exc_info=True)
        return json.dumps({"error": "An unexpected error occurred while calculating the budget."})
