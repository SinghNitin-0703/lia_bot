import csv
import logging
import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, event
from sqlalchemy.pool import NullPool

# Import our custom modules
from app.config import settings
from app.models import Base, Product, Order, User

# Set up logging so we can track database operations
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# SQLAlchemy Async Engine Setup
# ---------------------------------------------------------

# We use SQLite with the 'aiosqlite' async driver for our Noob-Friendly MVP.
# This is a local database stored in a file, which is great for development.
DATABASE_URL = "sqlite+aiosqlite:///./gluzo_v2.db"

# The engine is the main connection to the database
engine = None
try:
    # FIX for Issue #3 (Corrected): aiosqlite memory leak on per-request connections.
    # QueuePool is incompatible with async SQLite. The correct approach is using NullPool
    # and ensuring proper session management or a single shared engine.
    engine = create_async_engine(
        DATABASE_URL, 
        echo=False,
        poolclass=NullPool,
    )
    
    # FIX for Issue #2: SQLite write contention under concurrent load.
    # We enable WAL (Write-Ahead Logging) mode, which allows multiple readers and writers
    # to work at the same time without locking the entire database.
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """funxtion summary and flow in very short  """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
        
    logger.info("Database engine created successfully with WAL mode and QueuePool.")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}", exc_info=True)

# Session factory bound to our engine. 
# A session represents a "conversation" with the database.
if engine:
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False  # This allows us to use objects after the session closes
    )
else:
    AsyncSessionLocal = None


# ---------------------------------------------------------
# Database Dependency Injection
# ---------------------------------------------------------

async def get_db() -> AsyncSession: # type: ignore
    """funxtion summary and flow in very short  """
    """
    This function gives us a database session to use.
    It's used primarily for FastAPI endpoint dependency injection.
    """
    # Create a new session
    async with AsyncSessionLocal() as session:
        try:
            # Yield hands the session over to whatever function needs it
            yield session
        except Exception as e:
            logger.error(f"Error during database session: {e}", exc_info=True)
            raise
        finally:
            # The session will automatically close when we are done
            pass

# ---------------------------------------------------------
# Initialization & Data Seeding
# ---------------------------------------------------------

async def init_db() -> None:
    """funxtion summary and flow in very short  """
    """
    Creates all tables in SQLite. 
    If the Products table is empty, it reads the CSV file and fills the database with products.
    """
    logger.info("Initializing database tables...")
    
    # 1. Create all SQL tables defined in models.py
    try:
        async with engine.begin() as conn:
            # This creates the actual tables in the database file
            await conn.run_sync(Base.metadata.create_all)
            logger.info("All database tables verified/created.")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}", exc_info=True)
        return
        
    # 2. Check if the database needs seeding with CSV data
    try:
        async with AsyncSessionLocal() as session:
            # Check if we already have products in the database
            result = await session.execute(select(Product).limit(1))
            existing_product = result.scalar_one_or_none()
            
            # If we found a product, we don't need to load the CSV again
            if existing_product:
                logger.info("Database already contains product data. Skipping CSV ingestion.")
                return
                
            # 3. Perform the CSV Ingestion
            file_path = settings.CSV_FILE_PATH
            
            # Check if the CSV file actually exists before we try to open it
            if not os.path.exists(file_path):
                logger.warning(f"CSV file not found at {file_path}. Cannot seed the Product table.")
                return
                
            logger.info(f"Seeding SQL database from {file_path}...")
            
            try:
                # Open the CSV file and read its contents
                with open(file_path, mode="r", encoding="utf-8") as file:
                    reader = csv.DictReader(file)
                    
                    products_to_add = []
                    
                    # Go through each row in the CSV
                    for row in reader:
                        raw_name = row.get("name", "").strip()
                        
                        # If there is no name, skip this row
                        if not raw_name:
                            continue
                            
                        # Safely convert price to a number
                        try: 
                            price = float(row.get("price", 0.0))
                        except (ValueError, TypeError): 
                            price = 0.0
                            
                        # Safely convert discount to a number
                        try: 
                            discount = float(row.get("discount", 0.0))
                        except (ValueError, TypeError): 
                            discount = 0.0
                            
                        # Safely convert rating to a number
                        try: 
                            rating = float(row.get("rating", 4.0))
                        except (ValueError, TypeError): 
                            rating = 4.0
                            
                        # Safely convert review count to a whole number
                        try: 
                            review_count = int(float(row.get("review_count", 0)))
                        except (ValueError, TypeError): 
                            review_count = 0
                            
                        # Build a new Product object based on our SQLAlchemy model
                        new_product = Product(
                            name=raw_name,
                            price=price,
                            discount=discount,
                            brand=row.get("brand", "Unknown Brand"),
                            package=row.get("package", "Standard"),
                            size=row.get("size", "Standard"),
                            key_benefits=row.get("key_benefits", "No benefits listed."),
                            key_ingredients=row.get("key_ingredients", "No ingredients listed."),
                            ideal_for=row.get("ideal_for", "All skin types"),
                            how_to_use=row.get("how_to_use", "Follow standard instructions."),
                            rating=rating,
                            review_count=review_count,
                            image_paths=row.get("image_paths", ""),
                            image_urls=row.get("image_urls", ""),
                            url=row.get("url", "")
                        )
                        
                        # Add it to our list
                        products_to_add.append(new_product)
                        
                    # Save all the products to the database at once (bulk save)
                    session.add_all(products_to_add)
                    logger.info(f"Loaded {len(products_to_add)} products into memory.")
                    
                    # Seed a dummy user and order data for our support tools to test with
                    dummy_user = User(session_id="test-session", has_ordered=True)
                    session.add(dummy_user)
                    await session.flush() # Flush to get the generated user ID
                    
                    dummy_orders = [
                        Order(id="ORD-123", status="Delivered", user_id=dummy_user.id), 
                        Order(id="ORD-456", status="Out for Delivery", user_id=dummy_user.id),
                        Order(id="ORD-789", status="Processing", user_id=dummy_user.id)
                    ]
                    session.add_all(dummy_orders)
                    logger.info("Added dummy orders linked to test-session.")
                    
                    # Commit (save) the changes to the database
                    await session.commit()
                    logger.info("Successfully saved all data to the SQL database.")
                    
            except Exception as file_error:
                # If something went wrong reading the file, cancel the database transaction
                await session.rollback()
                logger.error(f"Failed to process CSV file and seed database: {file_error}", exc_info=True)
                
    except Exception as session_error:
        logger.error(f"Database session error during initialization: {session_error}", exc_info=True)
