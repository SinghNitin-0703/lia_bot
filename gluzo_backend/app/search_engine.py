import logging
import json
import os
from typing import List, Dict, Any
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Product
from app.config import settings

# Hybrid Search Dependencies
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

# Set up logging for the search engine
logger = logging.getLogger(__name__)

class HybridSearchEngine:
    """
    This class combines two types of search:
    1. Vector Search (Semantic/Meaning based) using ChromaDB
    2. Lexical Search (Keyword based) using BM25
    It fuses the results to give the most accurate product matches.
    """
    
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        
        # 1. Set up the local ChromaDB database for vector storage
        try:
            self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
            logger.info("ChromaDB client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client, possible HNSW corruption: {e}", exc_info=True)
            # FIX for Issue #10 (Corrected): Scope corruption catch.
            # Only attempt auto-recovery (deletion) if the exception looks like actual corruption
            # to prevent wiping the DB due to a missing env var or permissions error.
            error_msg = str(e).lower()
            if "invalid" in error_msg or "corrupt" in error_msg or "hnsw" in error_msg:
                try:
                    import shutil
                    if os.path.exists("./chroma_db"):
                        shutil.rmtree("./chroma_db")
                        logger.warning("Deleted corrupted chroma_db directory.")
                    self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
                    logger.info("Successfully recovered and created new ChromaDB client.")
                except Exception as recovery_err:
                    logger.error(f"Failed to auto-recover ChromaDB: {recovery_err}", exc_info=True)
            else:
                logger.error("Non-corruption error during ChromaDB init. Keeping directory intact.")
            
        # 2. Get the OpenAI API key to generate embeddings (converting text to numbers)
        api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found. Vector search will fallback or fail.")
            
        # 3. Configure the embedding function
        try:
            from chromadb.utils import embedding_functions
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            logger.info("Using default local embeddings for ChromaDB.")
        except Exception as e:
            logger.error(f"Failed to set up embedding function: {e}", exc_info=True)
            self.embedding_fn = None
            
        # 4. Create or load the 'products_collection' inside ChromaDB
        if self.chroma_client and self.embedding_fn:
            try:
                self.collection = self.chroma_client.get_or_create_collection(
                    name="products_collection",
                    embedding_function=self.embedding_fn
                )
            except Exception as e:
                logger.error(f"Failed to get/create ChromaDB collection: {e}", exc_info=True)
            
        # These variables will be set when the engine is initialized
        self.bm25: BM25Okapi = None
        self.product_map: Dict[str, Any] = {}
        self.is_initialized = False

    async def initialize_engine(self):
        """
        Loads products from the SQL database into our Search Engine (ChromaDB and BM25).
        """
        logger.info("Initializing Hybrid Search Engine (Vector + BM25)...")
        
        # 1. Fetch all products from the database
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Product))
                all_products = result.scalars().all()
                
            if not all_products:
                logger.warning("No products found in the database to index.")
                return
        except Exception as db_error:
            logger.error(f"Failed to fetch products from the database for indexing: {db_error}", exc_info=True)
            return

        # Prepare lists to hold data for the search engines
        documents = []
        metadatas = []
        ids = []
        corpus_for_bm25 = []

        # 2. Process each product
        for p in all_products:
            try:
                # We construct a rich text document for the vector embedding to understand the "meaning"
                rich_text = f"{p.name}. Brand: {p.brand}. Benefits: {p.key_benefits}. Ideal for: {p.ideal_for}. Ingredients: {p.key_ingredients}"
                
                # For BM25 (Lexical), we want to focus on exact keywords (name, brand, benefits)
                lexical_text = f"{p.name} {p.brand} {p.key_benefits}".lower()
                
                documents.append(rich_text)
                metadatas.append({"price": p.price, "discount": p.discount, "rating": p.rating, "id": p.id, "name": p.name})
                ids.append(str(p.id))
                
                corpus_for_bm25.append(lexical_text.split())
                
                # Save the product in a dictionary for quick lookup later
                self.product_map[str(p.id)] = p
                
            except Exception as e:
                logger.error(f"Error processing product {p.id} ({p.name}) for indexing: {e}", exc_info=True)

        # 3. Update the Vector Database (ChromaDB)
        try:
            # Using 'upsert' so we update existing products or insert new ones, avoiding duplicates
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info("Successfully updated ChromaDB with vector embeddings.")
        except Exception as chroma_error:
            logger.error(f"Failed to update ChromaDB: {chroma_error}", exc_info=True)
            
        # 4. Build the Lexical Engine (BM25)
        try:
            self.bm25 = BM25Okapi(corpus_for_bm25)
            logger.info("Successfully built BM25 lexical index.")
        except Exception as bm25_error:
            logger.error(f"Failed to build BM25 index: {bm25_error}", exc_info=True)
            
        self.is_initialized = True
        logger.info(f"Hybrid Search Engine is ready with {len(all_products)} products.")

    async def search(self, query: str, top_k: int = 5, excluded_ingredients: List[str] = None, max_price: float = None, sort_by: str = "relevance") -> List[Dict]:
        """
        Executes a dual-track search (Vector + Lexical) and combines the results.
        Strictly filters out any excluded ingredients (allergens).
        sort_by can be: 'relevance', 'popularity', 'price_low', 'price_high'
        """
        # Make sure the engine is initialized before searching
        if not self.is_initialized:
            try:
                await self.initialize_engine()
            except Exception as e:
                logger.error(f"Failed to initialize engine before searching: {e}", exc_info=True)
                return []
                
        # Make sure excluded_ingredients is an empty list if nothing was passed
        if excluded_ingredients is None:
            excluded_ingredients = []
            
        logger.info(f"Executing Hybrid Search for: '{query}'")
        
        # --- TRACK A: Vector Search (Semantic) ---
        vector_ranks = {}
        try:
            # We fetch more results than needed (top_k * 3) because some might be filtered out later
            vector_results = self.collection.query(
                query_texts=[query],
                n_results=top_k * 3
            )
            
            # Record the rank/position of each result from the vector search
            if vector_results['ids'] and vector_results['ids'][0]:
                for rank, prod_id in enumerate(vector_results['ids'][0]):
                    vector_ranks[prod_id] = rank + 1
        except Exception as v_error:
            logger.error(f"Vector search failed: {v_error}", exc_info=True)
                
        # --- TRACK B: Lexical Search (BM25) ---
        lexical_ranks = {}
        try:
            tokenized_query = query.lower().split()
            bm25_scores = self.bm25.get_scores(tokenized_query)
            
            # Sort the scores from highest to lowest
            sorted_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
            
            # Record the rank/position of each result from the lexical search
            all_ids = list(self.product_map.keys())
            for rank, idx in enumerate(sorted_indices[:top_k * 3]):
                prod_id = all_ids[idx]
                lexical_ranks[prod_id] = rank + 1
        except Exception as l_error:
            logger.error(f"Lexical search failed: {l_error}", exc_info=True)

        # --- FUSION: Reciprocal Rank Fusion (RRF) ---
        # This mathematical formula combines the ranks from both searches
        k = 60
        fused_scores = {}
        all_candidate_ids = set(vector_ranks.keys()).union(set(lexical_ranks.keys()))
        
        for prod_id in all_candidate_ids:
            try:
                product = self.product_map.get(prod_id)
                if not product:
                    continue
                    
                # 1. Strict Allergen Filtering Check
                is_safe = True
                for allergen in excluded_ingredients:
                    if allergen.lower() in product.key_ingredients.lower():
                        is_safe = False
                        logger.warning(f"Filtered out '{product.name}' post-search due to allergen: {allergen}.")
                        break
                
                # If the product contains an allergen, skip it entirely
                if not is_safe:
                    continue
                    
                # 1.5 Strict Budget Filtering Check
                real_price = product.price * (1 - (product.discount / 100)) if product.discount else product.price
                if max_price is not None and real_price > max_price:
                    continue
                    
                # 2. Score Calculation using RRF
                v_rank = vector_ranks.get(prod_id, 1000) # 1000 means it wasn't found in this search
                l_rank = lexical_ranks.get(prod_id, 1000)
                
                rrf_score = (1.0 / (k + v_rank)) + (1.0 / (k + l_rank))
                fused_scores[prod_id] = rrf_score
                
            except Exception as score_error:
                logger.error(f"Error calculating fused score for product {prod_id}: {score_error}", exc_info=True)
                
        # Fetch the top 30 most relevant safe products first (to give us a good pool to sort)
        top_relevant_ids = sorted(fused_scores.keys(), key=lambda pid: fused_scores[pid], reverse=True)[:max(top_k, 30)]
        
        # Now apply the requested sorting strategy
        if sort_by == "popularity":
            # Sort by review_count (descending)
            top_ids = sorted(top_relevant_ids, key=lambda pid: self.product_map[pid].review_count or 0, reverse=True)[:top_k]
        elif sort_by == "price_low":
            # Sort by real price (ascending)
            top_ids = sorted(top_relevant_ids, key=lambda pid: self.product_map[pid].price * (1 - (self.product_map[pid].discount or 0)/100), reverse=False)[:top_k]
        elif sort_by == "price_high":
            # Sort by real price (descending)
            top_ids = sorted(top_relevant_ids, key=lambda pid: self.product_map[pid].price * (1 - (self.product_map[pid].discount or 0)/100), reverse=True)[:top_k]
        else:
            # Default: Sort purely by relevance (RRF Score)
            top_ids = top_relevant_ids[:top_k]
        
        final_results = []
        for prod_id in top_ids:
            try:
                product = self.product_map[prod_id]
                
                # Build a local image URL from the image_paths field
                # image_paths looks like: "images_final\product-name\0.jpg | images_final\product-name\1.jpg"
                # We take the first path and convert it into a URL served by FastAPI
                local_image_url = ""
                if product.image_paths:
                    first_path = product.image_paths.split(" | ")[0].strip()
                    # Remove the "images_final\" prefix and normalize slashes for URLs
                    relative_path = first_path.replace("images_final\\", "").replace("\\", "/")
                    local_image_url = f"{settings.BASE_URL}/images/{relative_path}"
                
                final_results.append({
                    "matched_name": product.name,
                    "price": product.price,
                    "key_benefits": product.key_benefits,
                    "how_to_use": product.how_to_use,
                    "url": product.url,
                    "image_urls": local_image_url,
                    "discount": product.discount,
                    "rating": product.rating,
                    "review_count": product.review_count
                })
            except Exception as format_error:
                logger.error(f"Error formatting final result for product {prod_id}: {format_error}", exc_info=True)
                
        logger.info(f"Hybrid search returned {len(final_results)} results.")
        return final_results

# Create a single global instance to be used everywhere in the app
hybrid_search_engine = HybridSearchEngine()
