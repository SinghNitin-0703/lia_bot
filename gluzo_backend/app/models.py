from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, Boolean, ForeignKey, JSON
from typing import List, Optional

# This Base class is the foundation for all our SQLAlchemy database tables
# Think of it as the blueprint that all our other tables will follow
Base = declarative_base()

# ---------------------------------------------------------
# User Database Table
# ---------------------------------------------------------

class User(Base):
    """
    Represents a user communicating with the bot.
    This tells the database what information we want to save about each person.
    """
    # The actual name of the table inside the database
    __tablename__ = "users"

    # Unique database identifier (like a row number)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # We use the session ID as the unique identifier for the user
    # 'unique=True' means no two users can have the same session ID
    session_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    
    # We store preferences (like skin type, allergies) as a flexible JSON string
    # This allows us to easily save complex data without making a bunch of new columns
    preferences: Mapped[Optional[str]] = mapped_column(JSON, default="{}")
    
    # Boolean (True/False) flag to determine if they are a new prospect or an existing customer
    has_ordered: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationship tying users to their specific orders
    # This tells the database how to find all the orders this user has made
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")


# ---------------------------------------------------------
# Product Database Table
# ---------------------------------------------------------

class Product(Base):
    """
    Represents our skincare catalog, fully mapped to SQL from the original CSV layout.
    Each property here corresponds to a column in the database table.
    """
    # The actual name of the table inside the database
    __tablename__ = "products"

    # We use a standard integer ID as the primary key to avoid CSV duplicate name errors
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Product name
    name: Mapped[str] = mapped_column(String, index=True)
    
    # Pricing metrics (stored as floating point numbers for decimals)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    
    # General metadata about the physical product
    brand: Mapped[str] = mapped_column(String, default="")
    package: Mapped[str] = mapped_column(String, default="")
    size: Mapped[str] = mapped_column(String, default="")
    
    # NLP / Feature extraction strings
    # These are used heavily by our AI to search for products
    key_benefits: Mapped[str] = mapped_column(String, default="")
    key_ingredients: Mapped[str] = mapped_column(String, default="")
    ideal_for: Mapped[str] = mapped_column(String, default="")
    how_to_use: Mapped[str] = mapped_column(String, default="")
    
    # Ratings metrics
    rating: Mapped[float] = mapped_column(Float, default=4.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Visuals and Links for the user to see the product
    image_paths: Mapped[str] = mapped_column(String, default="")
    image_urls: Mapped[str] = mapped_column(String, default="")
    url: Mapped[str] = mapped_column(String, default="")


# ---------------------------------------------------------
# Order Tracking Table
# ---------------------------------------------------------

class Order(Base):
    """
    Represents a transactional order linked to a specific user.
    Used for customer support tracking.
    """
    # The actual name of the table inside the database
    __tablename__ = "orders"

    # Standard primary key (e.g., ORD-123)
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    
    # Foreign key linking back to the User table. 
    # This says "this order belongs to the user with this specific ID".
    # Nullable true for mock data seeding flexibility.
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # The current status of the order (e.g., "Delivered", "Processing")
    status: Mapped[str] = mapped_column(String, default="Processing")
    
    # Relationship back to the User object
    # This allows us to easily access the user's information from an order object
    user: Mapped[Optional["User"]] = relationship("User", back_populates="orders")
