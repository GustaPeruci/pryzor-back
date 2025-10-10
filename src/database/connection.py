"""
Database configuration for Pryzor Steam Price Prediction System
Production-ready MySQL database connections
"""

import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database configuration - MySQL production
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://pryzor_user:pryzor_pass@localhost:3306/pryzor_db"
)

# Create engine with MySQL-specific configurations
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Set to True for SQL query logging in development
)

# Session configuration
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()

# Metadata for database introspection
metadata = MetaData()

def get_database():
    """
    Dependency to get database session
    Used in FastAPI endpoints for dependency injection
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_database():
    """
    Create all tables in the database
    Called during application startup
    """
    Base.metadata.create_all(bind=engine)

def test_connection():
    """
    Test database connection
    Returns True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False