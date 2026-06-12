from pydantic import BaseModel, Field
from typing import List, Optional

# ---------------------------------------------------------
# Core Product Entity
# ---------------------------------------------------------

class ProductSchema(BaseModel):
    """
    This tells our app exactly what a "Product" should look like.
    It acts as a strict checkpoint: if data doesn't match this format, the app will reject it.
    """
    # Represents the 14 columns from our CSV ingestion pipeline
    name: str = Field(..., description="The full name of the product")
    price: float = Field(..., description="Base price in USD")
    discount: float = Field(default=0.0, description="Discount percentage (0-100)")
    
    brand: str = Field(..., description="The brand or manufacturer")
    package: str = Field(..., description="Packaging type (e.g., tube, tub, bottle)")
    size: str = Field(..., description="The physical size/volume of the product")
    
    key_benefits: str = Field(..., description="Primary benefits of using this product")
    key_ingredients: str = Field(..., description="Comma-separated string of main ingredients")
    ideal_for: str = Field(..., description="Target skin types or concerns")
    how_to_use: str = Field(..., description="Instructions for application")
    
    rating: float = Field(default=4.0, description="Average customer rating")
    review_count: int = Field(default=0, description="Total number of customer reviews")
    
    image_paths: str = Field(default="", description="Local paths to product images")
    image_urls: str = Field(default="", description="Remote URLs for product images")
    url: str = Field(default="", description="Direct link to the product page")


# ---------------------------------------------------------
# Advanced Search Models
# ---------------------------------------------------------

class AdvancedSearchIntent(BaseModel):
    """
    This structure is what the AI Router Agent will parse user queries into.
    For example, if a user asks "I want a cheap face wash with no fragrance",
    the AI will fill out this form automatically.
    """
    product_types: List[str] = Field(
        default_factory=list,
        description="List of product categories requested (e.g., ['face wash', 'moisturizer'])"
    )
    
    target_skin_type: Optional[str] = Field(
        default=None,
        description="The specific skin type requested (e.g., 'oily', 'dry', 'sensitive')"
    )
    
    excluded_ingredients: List[str] = Field(
        default_factory=list,
        description="List of allergens or banned ingredients to strip out of search results"
    )
    
    max_total_budget: Optional[float] = Field(
        default=None,
        description="The combined maximum budget cap for the entire query in USD"
    )
    
    sort_by_value: bool = Field(
        default=False,
        description="Triggered to true if the user seeks 'value for money' or 'best deals'"
    )


# ---------------------------------------------------------
# External Extraction Models
# ---------------------------------------------------------

class CompetitorFormulaExtract(BaseModel):
    """
    The structure used by external tools (like the Tavily API) 
    to represent and understand competitor products.
    """
    product_name: str = Field(..., description="The name of the competitor product")
    product_type: str = Field(..., description="The category of the product")
    extracted_actives: List[str] = Field(..., description="A list of active chemical components found")
    primary_benefit: str = Field(..., description="The main selling point or benefit of the product")




# ---------------------------------------------------------
# API Endpoint Models
# ---------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str
    message: str

class BehaviorTriggerRequest(BaseModel):
    session_id: str
    event: str


