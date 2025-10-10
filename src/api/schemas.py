"""
Pydantic schemas for Pryzor Steam Price Prediction API
Following portfolio directions: Proper API design with data validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from datetime import date as date_type
from enum import Enum

class GameType(str, Enum):
    """Game type enumeration"""
    game = "game"
    dlc = "dlc"
    demo = "demo"
    unknown = "unknown"

class PriceTier(str, Enum):
    """Price tier classification"""
    free = "free"
    budget = "budget"
    mid_tier = "mid_tier"
    premium = "premium"
    aaa = "aaa"

class GameSearchResponse(BaseModel):
    """Response schema for game search results"""
    appid: int = Field(..., description="Steam App ID")
    name: str = Field(..., description="Game name")
    type: Optional[str] = Field(None, description="Game type")
    free_to_play: bool = Field(False, description="Is free-to-play game")
    current_price: Optional[float] = Field(None, description="Current price")
    
    class Config:
        from_attributes = True

class GameResponse(BaseModel):
    """Response schema for detailed game information"""
    appid: int = Field(..., description="Steam App ID")
    name: str = Field(..., description="Game name")
    type: Optional[str] = Field(None, description="Game type")
    release_date: Optional[date_type] = Field(None, description="Release date")
    free_to_play: bool = Field(False, description="Is free-to-play game")
    current_price: Optional[float] = Field(None, description="Current price")
    average_price: Optional[float] = Field(None, description="Average historical price")
    min_price: Optional[float] = Field(None, description="Lowest recorded price")
    max_discount: Optional[int] = Field(None, description="Maximum discount percentage")
    last_discount_date: Optional[date_type] = Field(None, description="Date of last discount")
    discount_frequency: Optional[float] = Field(None, description="Frequency of discounts (0-1)")
    price_records_count: Optional[int] = Field(None, description="Number of price history records")
    price_variance: Optional[float] = Field(None, description="Price variance for volatility analysis")
    
    class Config:
        from_attributes = True

class PriceHistoryResponse(BaseModel):
    """Response schema for price history data"""
    price_date: date_type = Field(..., description="Price record date")
    initial_price: float = Field(..., description="Original price")
    final_price: float = Field(..., description="Final price after discount")
    discount: int = Field(0, description="Discount percentage")
    
    class Config:
        from_attributes = True

class PredictionResponse(BaseModel):
    """Response schema for AI predictions"""
    appid: int = Field(..., description="Steam App ID")
    game_name: Optional[str] = Field(None, description="Game name")
    is_good_time_to_buy: bool = Field(..., description="AI prediction: good time to buy")
    confidence_score: float = Field(..., ge=0, le=1, description="Prediction confidence (0-1)")
    predicted_discount_probability: Optional[float] = Field(None, ge=0, le=1, description="Probability of upcoming discount")
    days_until_next_sale: Optional[int] = Field(None, ge=0, description="Estimated days until next sale")
    current_price: Optional[float] = Field(None, description="Current game price")
    recommendation: str = Field(..., description="Human-readable recommendation")
    reasoning: List[str] = Field(default_factory=list, description="Factors influencing the prediction")
    model_version: str = Field(..., description="AI model version used")
    prediction_date: date_type = Field(..., description="Date of prediction")
    
    class Config:
        from_attributes = True

class MarketTrendResponse(BaseModel):
    """Response schema for market trends"""
    period_days: int = Field(..., description="Analysis period in days")
    total_games: int = Field(..., description="Total games analyzed")
    games_on_sale: int = Field(..., description="Games currently on sale")
    average_discount: float = Field(..., description="Average discount percentage")
    top_discounted_categories: List[Dict[str, Any]] = Field(..., description="Categories with highest discounts")
    price_trend: str = Field(..., description="Overall price trend direction")
    
    class Config:
        from_attributes = True

class OpportunityResponse(BaseModel):
    """Response schema for purchase opportunities"""
    appid: int = Field(..., description="Steam App ID")
    game_name: str = Field(..., description="Game name")
    current_price: float = Field(..., description="Current price")
    discount: int = Field(0, description="Current discount percentage")
    confidence_score: float = Field(..., ge=0, le=1, description="AI confidence score")
    opportunity_score: float = Field(..., ge=0, le=10, description="Overall opportunity score (0-10)")
    reasoning: List[str] = Field(..., description="Why this is a good opportunity")
    
    class Config:
        from_attributes = True

class ModelInfoResponse(BaseModel):
    """Response schema for AI model information"""
    model_name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    algorithm: str = Field(..., description="ML algorithm used")
    accuracy: Optional[float] = Field(None, ge=0, le=1, description="Model accuracy")
    precision: Optional[float] = Field(None, ge=0, le=1, description="Model precision")
    recall: Optional[float] = Field(None, ge=0, le=1, description="Model recall")
    f1_score: Optional[float] = Field(None, ge=0, le=1, description="Model F1 score")
    training_date: datetime = Field(..., description="When the model was trained")
    status: str = Field(..., description="Model status")
    
    class Config:
        from_attributes = True

# Request schemas
class GameSearchRequest(BaseModel):
    """Request schema for game search"""
    query: str = Field(..., min_length=2, max_length=100, description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Maximum results")

class BatchPredictionRequest(BaseModel):
    """Request schema for batch predictions"""
    app_ids: List[int] = Field(..., max_items=50, description="List of Steam App IDs")
    
    class Config:
        schema_extra = {
            "example": {
                "app_ids": [730, 440, 570, 578080]
            }
        }

class PredictionRequest(BaseModel):
    """Request schema for single prediction"""
    app_id: int = Field(..., description="Steam App ID")
    force_refresh: bool = Field(False, description="Force model to recalculate prediction")

# Error response schemas
class ErrorResponse(BaseModel):
    """Standard error response schema"""
    detail: str = Field(..., description="Error description")
    error_code: Optional[str] = Field(None, description="Application-specific error code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")

class ValidationErrorResponse(BaseModel):
    """Validation error response schema"""
    detail: List[Dict[str, Any]] = Field(..., description="Validation error details")
    error_type: str = Field("validation_error", description="Error type")

# Health check schemas
class HealthCheckResponse(BaseModel):
    """Health check response schema"""
    status: str = Field(..., description="Overall system status")
    database: str = Field(..., description="Database connection status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    
class APIInfoResponse(BaseModel):
    """API information response schema"""
    message: str = Field(..., description="Welcome message")
    version: str = Field(..., description="API version")
    docs: str = Field(..., description="Documentation URL")
    status: str = Field(..., description="API status")