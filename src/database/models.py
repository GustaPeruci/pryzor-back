"""
Modelos SQLAlchemy para o Pryzor - MySQL Only
Production MySQL database models
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
from .config import get_connection_string, is_mysql

# Base para todos os modelos
Base = declarative_base()

class Game(Base):
    """
    Game information from Steam
    Normalized table for game metadata
    """
    __tablename__ = "games"
    
    appid = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=True)
    name = Column(String(255), nullable=False, index=True)
    release_date = Column(Date, nullable=True)
    free_to_play = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship with price history
    price_history = relationship("PriceHistory", back_populates="game", cascade="all, delete-orphan")
    
    # Relationship with predictions
    predictions = relationship("PricePrediction", back_populates="game", cascade="all, delete-orphan")

class PriceHistory(Base):
    """
    Historical price data for games
    Normalized table for price tracking
    """
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    appid = Column(Integer, ForeignKey("games.appid"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    initial_price = Column(Float, nullable=False)
    final_price = Column(Float, nullable=False)
    discount = Column(Integer, nullable=False, default=0)  # Discount percentage
    created_at = Column(DateTime, default=func.now())
    
    # Relationship with game
    game = relationship("Game", back_populates="price_history")
    
    # Composite index for efficient queries
    __table_args__ = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

class PricePrediction(Base):
    """
    ML predictions for optimal purchase timing
    Stores model predictions and confidence scores
    """
    __tablename__ = "price_predictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    appid = Column(Integer, ForeignKey("games.appid"), nullable=False, index=True)
    prediction_date = Column(Date, nullable=False, default=func.current_date())
    is_good_time_to_buy = Column(Boolean, nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    predicted_discount_probability = Column(Float, nullable=True)
    days_until_next_sale = Column(Integer, nullable=True)
    model_version = Column(String(50), nullable=False)
    features_used = Column(Text, nullable=True)  # JSON string of features
    created_at = Column(DateTime, default=func.now())
    
    # Relationship with game
    game = relationship("Game", back_populates="predictions")

class ModelMetadata(Base):
    """
    Metadata about trained ML models
    Tracks model versions and performance metrics
    """
    __tablename__ = "model_metadata"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False, unique=True)
    algorithm = Column(String(100), nullable=False)
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    training_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=False)
    model_path = Column(String(255), nullable=True)
    hyperparameters = Column(Text, nullable=True)  # JSON string
    feature_importance = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=func.now())

class DataProcessingLog(Base):
    """
    Log table for ETL processes
    Tracks data pipeline execution and errors
    """
    __tablename__ = "data_processing_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    process_name = Column(String(100), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # 'running', 'completed', 'failed'
    records_processed = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())