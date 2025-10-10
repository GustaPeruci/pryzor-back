"""
Business logic services for Pryzor Steam Price Prediction API
Following portfolio directions: Modular architecture with separation of concerns
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
import logging
import sys
import os

# Add project paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data_pipeline'))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ml_model'))

from database.models import Game, PriceHistory, PricePrediction, ModelMetadata
from api.schemas import (
    GameResponse, GameSearchResponse, PriceHistoryResponse, 
    PredictionResponse, OpportunityResponse, MarketTrendResponse
)

logger = logging.getLogger(__name__)

class GameService:
    """Service for game-related operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def search_games(self, query: str, limit: int = 10) -> List[GameSearchResponse]:
        """
        Search games by name with fuzzy matching
        """
        try:
            # Search games with name containing query (case-insensitive)
            games = self.db.query(Game).filter(
                Game.name.ilike(f"%{query}%")
            ).limit(limit).all()
            
            results = []
            for game in games:
                # Get current price from latest price history
                latest_price = self.db.query(PriceHistory).filter(
                    PriceHistory.appid == game.appid
                ).order_by(desc(PriceHistory.date)).first()
                
                current_price = latest_price.final_price if latest_price else None
                
                results.append(GameSearchResponse(
                    appid=game.appid,
                    name=game.name,
                    type=game.type,
                    free_to_play=game.free_to_play,
                    current_price=current_price
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching games: {e}")
            return []
    
    def get_game_by_id(self, app_id: int) -> Optional[GameResponse]:
        """
        Get detailed game information by App ID
        """
        try:
            game = self.db.query(Game).filter(Game.appid == app_id).first()
            
            if not game:
                return None
            
            # Calculate price statistics
            price_stats = self._calculate_price_stats(app_id)
            
            return GameResponse(
                appid=game.appid,
                name=game.name,
                type=game.type,
                release_date=game.release_date,
                free_to_play=game.free_to_play,
                current_price=price_stats.get('current_price'),
                average_price=price_stats.get('average_price'),
                min_price=price_stats.get('min_price'),
                max_discount=price_stats.get('max_discount'),
                last_discount_date=price_stats.get('last_discount_date'),
                discount_frequency=price_stats.get('discount_frequency'),
                price_records_count=price_stats.get('price_records_count'),
                price_variance=price_stats.get('price_variance')
            )
            
        except Exception as e:
            logger.error(f"Error getting game {app_id}: {e}")
            return None
    
    def get_price_history(self, app_id: int, days: int = 365) -> List[PriceHistoryResponse]:
        """
        Get price history for a game
        """
        try:
            cutoff_date = datetime.now().date() - timedelta(days=days)
            
            price_history = self.db.query(PriceHistory).filter(
                and_(
                    PriceHistory.appid == app_id,
                    PriceHistory.date >= cutoff_date
                )
            ).order_by(PriceHistory.date).all()
            
            return [
                PriceHistoryResponse(
                    price_date=ph.date,
                    initial_price=ph.initial_price,
                    final_price=ph.final_price,
                    discount=ph.discount
                ) for ph in price_history
            ]
            
        except Exception as e:
            logger.error(f"Error getting price history for {app_id}: {e}")
            return []
    
    def get_market_trends(self, days: int = 30) -> MarketTrendResponse:
        """
        Get market trends and statistics
        """
        try:
            cutoff_date = datetime.now().date() - timedelta(days=days)
            
            # Total games with price data
            total_games = self.db.query(Game).join(PriceHistory).distinct(Game.appid).count()
            
            # Games currently on sale (latest price has discount > 0)
            games_on_sale_subquery = self.db.query(
                PriceHistory.appid,
                func.max(PriceHistory.date).label('max_date')
            ).filter(
                PriceHistory.date >= cutoff_date
            ).group_by(PriceHistory.appid).subquery()
            
            current_discounts = self.db.query(PriceHistory).join(
                games_on_sale_subquery,
                and_(
                    PriceHistory.appid == games_on_sale_subquery.c.appid,
                    PriceHistory.date == games_on_sale_subquery.c.max_date
                )
            ).all()
            
            games_on_sale = len([p for p in current_discounts if p.discount > 0])
            avg_discount = sum(p.discount for p in current_discounts if p.discount > 0) / max(games_on_sale, 1)
            
            # Price trend analysis
            price_trend = self._analyze_price_trend(cutoff_date)
            
            return MarketTrendResponse(
                period_days=days,
                total_games=total_games,
                games_on_sale=games_on_sale,
                average_discount=avg_discount,
                top_discounted_categories=[],  # Could be expanded with category analysis
                price_trend=price_trend
            )
            
        except Exception as e:
            logger.error(f"Error getting market trends: {e}")
            return MarketTrendResponse(
                period_days=days,
                total_games=0,
                games_on_sale=0,
                average_discount=0.0,
                top_discounted_categories=[],
                price_trend="stable"
            )
    
    def _calculate_price_stats(self, app_id: int) -> Dict[str, Any]:
        """Calculate price statistics for a game"""
        try:
            price_history = self.db.query(PriceHistory).filter(
                PriceHistory.appid == app_id
            ).order_by(PriceHistory.date).all()
            
            if not price_history:
                return {}
            
            # Current price (latest record)
            current_price = price_history[-1].final_price
            
            # Price statistics
            prices = [ph.final_price for ph in price_history]
            average_price = sum(prices) / len(prices)
            min_price = min(prices)
            
            # Price variance calculation
            if len(prices) > 1:
                price_variance = sum((p - average_price) ** 2 for p in prices) / len(prices)
            else:
                price_variance = 0.0
            
            # Discount statistics
            discounts = [ph.discount for ph in price_history]
            max_discount = max(discounts)
            
            # Last discount date
            last_discount_date = None
            for ph in reversed(price_history):
                if ph.discount > 0:
                    last_discount_date = ph.date
                    break
            
            # Discount frequency
            discount_frequency = len([d for d in discounts if d > 0]) / len(discounts)
            
            return {
                'current_price': current_price,
                'average_price': average_price,
                'min_price': min_price,
                'max_discount': max_discount,
                'last_discount_date': last_discount_date,
                'discount_frequency': discount_frequency,
                'price_records_count': len(price_history),
                'price_variance': price_variance
            }
            
        except Exception as e:
            logger.error(f"Error calculating price stats for {app_id}: {e}")
            return {}
    
    def _analyze_price_trend(self, cutoff_date: date) -> str:
        """Analyze overall market price trend"""
        try:
            # Simplified trend analysis
            recent_prices = self.db.query(PriceHistory).filter(
                PriceHistory.date >= cutoff_date
            ).all()
            
            if len(recent_prices) < 2:
                return "stable"
            
            # Calculate average price change
            first_half = recent_prices[:len(recent_prices)//2]
            second_half = recent_prices[len(recent_prices)//2:]
            
            first_avg = sum(p.final_price for p in first_half) / len(first_half)
            second_avg = sum(p.final_price for p in second_half) / len(second_half)
            
            change_percent = ((second_avg - first_avg) / first_avg) * 100
            
            if change_percent > 5:
                return "increasing"
            elif change_percent < -5:
                return "decreasing"
            else:
                return "stable"
                
        except Exception as e:
            logger.error(f"Error analyzing price trend: {e}")
            return "stable"


class PredictionService:
    """Service for AI prediction operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_prediction(self, app_id: int) -> Optional[PredictionResponse]:
        """
        Get AI prediction for a specific game
        """
        try:
            # Check for existing recent prediction
            recent_prediction = self.db.query(PricePrediction).filter(
                and_(
                    PricePrediction.appid == app_id,
                    PricePrediction.prediction_date >= datetime.now().date() - timedelta(days=1)
                )
            ).order_by(desc(PricePrediction.created_at)).first()
            
            if recent_prediction:
                return self._format_prediction_response(recent_prediction)
            
            # Generate new prediction
            return self._generate_new_prediction(app_id)
            
        except Exception as e:
            logger.error(f"Error getting prediction for {app_id}: {e}")
            return None
    
    def get_batch_predictions(self, app_ids: List[int]) -> List[PredictionResponse]:
        """
        Get predictions for multiple games
        """
        predictions = []
        for app_id in app_ids:
            prediction = self.get_prediction(app_id)
            if prediction:
                predictions.append(prediction)
        
        return predictions
    
    def get_top_opportunities(self, limit: int = 20) -> List[OpportunityResponse]:
        """
        Get top purchase opportunities based on AI predictions
        """
        try:
            # Get recent predictions with high confidence
            recent_predictions = self.db.query(PricePrediction).filter(
                and_(
                    PricePrediction.prediction_date >= datetime.now().date() - timedelta(days=1),
                    PricePrediction.is_good_time_to_buy == True,
                    PricePrediction.confidence_score >= 0.7
                )
            ).order_by(desc(PricePrediction.confidence_score)).limit(limit).all()
            
            opportunities = []
            for pred in recent_predictions:
                game = self.db.query(Game).filter(Game.appid == pred.appid).first()
                if not game:
                    continue
                
                # Get current price
                latest_price = self.db.query(PriceHistory).filter(
                    PriceHistory.appid == pred.appid
                ).order_by(desc(PriceHistory.date)).first()
                
                if not latest_price:
                    continue
                
                # Calculate opportunity score
                opportunity_score = self._calculate_opportunity_score(pred, latest_price)
                
                opportunities.append(OpportunityResponse(
                    appid=pred.appid,
                    game_name=game.name,
                    current_price=latest_price.final_price,
                    discount=latest_price.discount,
                    confidence_score=pred.confidence_score,
                    opportunity_score=opportunity_score,
                    reasoning=self._generate_reasoning(pred, latest_price)
                ))
            
            # Sort by opportunity score
            opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
            return opportunities
            
        except Exception as e:
            logger.error(f"Error getting top opportunities: {e}")
            return []
    
    def _generate_new_prediction(self, app_id: int) -> Optional[PredictionResponse]:
        """
        Generate new prediction using ML model (simplified version)
        """
        try:
            # Get game info
            game = self.db.query(Game).filter(Game.appid == app_id).first()
            if not game:
                return None
            
            # Get recent price history
            recent_prices = self.db.query(PriceHistory).filter(
                PriceHistory.appid == app_id
            ).order_by(desc(PriceHistory.date)).limit(30).all()
            
            if not recent_prices:
                return None
            
            # Simplified prediction logic (replace with actual ML model)
            prediction_result = self._simple_prediction_logic(recent_prices)
            
            # Save prediction to database
            new_prediction = PricePrediction(
                appid=app_id,
                prediction_date=datetime.now().date(),
                is_good_time_to_buy=prediction_result['is_good_time'],
                confidence_score=prediction_result['confidence'],
                predicted_discount_probability=prediction_result.get('discount_prob'),
                days_until_next_sale=prediction_result.get('days_to_sale'),
                model_version="simple_v1.0",
                features_used="price_history,discount_patterns"
            )
            
            self.db.add(new_prediction)
            self.db.commit()
            
            return self._format_prediction_response(new_prediction)
            
        except Exception as e:
            logger.error(f"Error generating prediction for {app_id}: {e}")
            return None
    
    def _simple_prediction_logic(self, price_history: List[PriceHistory]) -> Dict[str, Any]:
        """
        Simplified prediction logic (to be replaced with trained ML model)
        """
        if not price_history:
            return {
                'is_good_time': False,
                'confidence': 0.5,
                'discount_prob': 0.3,
                'days_to_sale': 30
            }
        
        latest = price_history[0]  # Most recent (due to desc order)
        
        # Simple rules-based prediction
        is_good_time = False
        confidence = 0.5
        
        # Check current discount
        if latest.discount >= 50:
            is_good_time = True
            confidence = 0.9
        elif latest.discount >= 25:
            is_good_time = True
            confidence = 0.7
        elif latest.discount >= 10:
            is_good_time = True
            confidence = 0.6
        
        # Check discount frequency
        discounts = [ph.discount for ph in price_history[-14:]]  # Last 14 days
        recent_discounts = len([d for d in discounts if d > 0])
        
        if recent_discounts == 0 and latest.discount == 0:
            # No recent discounts, might be due for one
            confidence = min(confidence + 0.2, 0.9)
        
        return {
            'is_good_time': is_good_time,
            'confidence': confidence,
            'discount_prob': min(recent_discounts / 14, 1.0),
            'days_to_sale': 30 - recent_discounts * 2
        }
    
    def _format_prediction_response(self, prediction: PricePrediction) -> PredictionResponse:
        """
        Format database prediction to response schema
        """
        try:
            game = self.db.query(Game).filter(Game.appid == prediction.appid).first()
            game_name = game.name if game else f"Game {prediction.appid}"
            
            # Get current price
            latest_price = self.db.query(PriceHistory).filter(
                PriceHistory.appid == prediction.appid
            ).order_by(desc(PriceHistory.date)).first()
            
            current_price = latest_price.final_price if latest_price else None
            
            # Generate recommendation text
            if prediction.is_good_time_to_buy:
                recommendation = f"✅ Good time to buy! Confidence: {prediction.confidence_score:.0%}"
            else:
                recommendation = f"⏳ Consider waiting. Confidence: {prediction.confidence_score:.0%}"
            
            # Generate reasoning
            reasoning = self._generate_prediction_reasoning(prediction, latest_price)
            
            return PredictionResponse(
                appid=prediction.appid,
                game_name=game_name,
                is_good_time_to_buy=prediction.is_good_time_to_buy,
                confidence_score=prediction.confidence_score,
                predicted_discount_probability=prediction.predicted_discount_probability,
                days_until_next_sale=prediction.days_until_next_sale,
                current_price=current_price,
                recommendation=recommendation,
                reasoning=reasoning,
                model_version=prediction.model_version,
                prediction_date=prediction.prediction_date
            )
            
        except Exception as e:
            logger.error(f"Error formatting prediction response: {e}")
            return None
    
    def _generate_prediction_reasoning(self, prediction: PricePrediction, latest_price: Optional[PriceHistory]) -> List[str]:
        """Generate human-readable reasoning for the prediction"""
        reasoning = []
        
        if latest_price:
            if latest_price.discount > 0:
                reasoning.append(f"Currently {latest_price.discount}% off (${latest_price.final_price})")
            else:
                reasoning.append(f"Full price: ${latest_price.final_price}")
        
        if prediction.confidence_score >= 0.8:
            reasoning.append("High confidence prediction based on historical patterns")
        elif prediction.confidence_score >= 0.6:
            reasoning.append("Moderate confidence prediction")
        else:
            reasoning.append("Low confidence - consider additional factors")
        
        if prediction.predicted_discount_probability and prediction.predicted_discount_probability > 0.5:
            reasoning.append(f"{prediction.predicted_discount_probability:.0%} chance of discount soon")
        
        if prediction.days_until_next_sale and prediction.days_until_next_sale < 30:
            reasoning.append(f"Next sale predicted in ~{prediction.days_until_next_sale} days")
        
        return reasoning
    
    def _calculate_opportunity_score(self, prediction: PricePrediction, latest_price: PriceHistory) -> float:
        """Calculate opportunity score (0-10)"""
        score = 0.0
        
        # Base score from confidence
        score += prediction.confidence_score * 5
        
        # Bonus for current discount
        if latest_price.discount >= 50:
            score += 3
        elif latest_price.discount >= 25:
            score += 2
        elif latest_price.discount >= 10:
            score += 1
        
        # Bonus for high discount probability
        if prediction.predicted_discount_probability and prediction.predicted_discount_probability > 0.7:
            score += 1
        
        # Bonus for predicted sale timing
        if prediction.days_until_next_sale and prediction.days_until_next_sale < 7:
            score += 1
        
        return min(score, 10.0)
    
    def _generate_reasoning(self, prediction: PricePrediction, latest_price: PriceHistory) -> List[str]:
        """Generate reasoning for opportunity"""
        reasoning = []
        
        if latest_price.discount > 0:
            reasoning.append(f"Currently on sale: {latest_price.discount}% off")
        
        if prediction.confidence_score >= 0.8:
            reasoning.append("AI highly confident in timing")
        
        if prediction.predicted_discount_probability and prediction.predicted_discount_probability < 0.3:
            reasoning.append("Discounts are rare for this game")
        
        return reasoning