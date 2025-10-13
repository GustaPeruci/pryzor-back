"""
Real ML Service for Pryzor API
Integrates trained ML model with the FastAPI application
"""

import os
import sys
import pickle
import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from ml_model.steam_price_ml_pipeline import SteamPriceMLPipeline

logger = logging.getLogger(__name__)

class RealMLPredictionService:
    """
    Production ML service with trained model
    """
    
    def __init__(self, db_path: str, model_path: str = "steam_price_model.pkl"):
        self.db_path = db_path
        # Resolve model path
        # Priority: explicit env (MODEL_PATH) -> treat as file or directory; else repo root/ml_model/<file>
        env_model_path = os.getenv("MODEL_PATH")
        if env_model_path:
            if os.path.isdir(env_model_path):
                resolved = os.path.join(env_model_path, model_path)
            else:
                resolved = env_model_path
        else:
            resolved = os.path.join(project_root, "ml_model", model_path)

        self.model_path = os.path.abspath(resolved)
        self.ml_pipeline = None
        self.model_loaded = False
        self._load_model()
    
    def _load_model(self):
        """Load the trained ML model"""
        try:
            if not os.path.exists(self.model_path):
                logger.warning(f"⚠️ Model file not found: {self.model_path}")
                return False
            
            self.ml_pipeline = SteamPriceMLPipeline(self.db_path)
            success = self.ml_pipeline.load_model(self.model_path)
            
            if success:
                self.model_loaded = True
                logger.info("✅ ML model loaded successfully")
            else:
                logger.error("❌ Failed to load ML model")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error loading ML model: {e}")
            return False
    
    def predict_price_category(self, appid: int) -> Dict[str, Any]:
        """
        Real ML prediction for price category
        """
        if not self.model_loaded:
            return self._fallback_prediction(appid)
        
        try:
            # Use the trained ML pipeline for prediction
            prediction = self.ml_pipeline.predict_game_category(appid)
            
            if 'error' in prediction:
                return self._fallback_prediction(appid)
            
            # Enhance prediction with additional metadata
            prediction['model_type'] = 'real_ml'
            prediction['features_used'] = len(self.ml_pipeline.feature_columns) if self.ml_pipeline.feature_columns else 0
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ ML prediction failed for game {appid}: {e}")
            return self._fallback_prediction(appid)
    
    def _fallback_prediction(self, appid: int) -> Dict[str, Any]:
        """
        Fallback prediction using simple rules
        """
        try:
            import mysql.connector
            
            with mysql.connector.connect(
                host='localhost',
                port=3306,
                user='root',
                password='root',
                database='steam_pryzor'
            ) as conn:
                cursor = conn.cursor()
                
                # Get game info
                cursor.execute("SELECT name FROM games WHERE appid = %s", (appid,))
                game_row = cursor.fetchone()
                if not game_row:
                    return {'error': 'Game not found'}
                
                # Get price stats
                cursor.execute(
                    """
                    SELECT AVG(Finalprice), AVG(Discount), COUNT(*)
                    FROM price_history WHERE appid = %s
                    """,
                    (appid,)
                )
                
                stats_row = cursor.fetchone()
                if not stats_row or stats_row[2] == 0:
                    return {'error': 'No price history available'}
                
                avg_price = stats_row[0]
                avg_discount = stats_row[1]
                
                # Simple rule-based prediction
                if avg_price < 5:
                    category = "budget"
                    confidence = 0.75
                elif avg_price < 15:
                    category = "economy"
                    confidence = 0.70
                elif avg_price < 30:
                    category = "standard"
                    confidence = 0.72
                elif avg_price < 50:
                    category = "premium"
                    confidence = 0.68
                else:
                    category = "luxury"
                    confidence = 0.65
                
                return {
                    'appid': appid,
                    'game_name': game_row[0],
                    'predicted_category': category,
                    'confidence': confidence,
                    'model_type': 'fallback_rules',
                    'features': {
                        'avg_price': round(avg_price, 2),
                        'avg_discount': round(avg_discount, 2)
                    },
                    'prediction_date': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Fallback prediction failed: {e}")
            return {'error': f'Prediction failed: {str(e)}'}
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model
        """
        if not self.model_loaded or not self.ml_pipeline:
            return {
                'model_loaded': False,
                'model_type': 'fallback_rules',
                'message': 'Using rule-based fallback prediction'
            }
        
        try:
            model_info = {
                'model_loaded': True,
                'model_type': 'trained_ml',
                'best_model': self.ml_pipeline.best_model,
                'features_count': len(self.ml_pipeline.feature_columns) if self.ml_pipeline.feature_columns else 0,
                'model_path': self.model_path
            }
            
            # Add performance metrics if available
            if self.ml_pipeline.models and self.ml_pipeline.best_model:
                best_model_metrics = self.ml_pipeline.models.get(self.ml_pipeline.best_model, {})
                model_info['accuracy'] = best_model_metrics.get('accuracy', 'unknown')
                model_info['cv_score'] = best_model_metrics.get('cv_mean', 'unknown')
            
            return model_info
            
        except Exception as e:
            logger.error(f"❌ Error getting model info: {e}")
            return {
                'model_loaded': False,
                'error': str(e)
            }
    
    def batch_predict(self, appids: list) -> Dict[int, Dict[str, Any]]:
        """
        Batch prediction for multiple games
        """
        results = {}
        
        for appid in appids:
            try:
                prediction = self.predict_price_category(appid)
                results[appid] = prediction
            except Exception as e:
                results[appid] = {'error': f'Prediction failed: {str(e)}'}
        
        return results
    
    def retrain_model(self) -> Dict[str, Any]:
        """
        Retrain the ML model with current data
        """
        try:
            logger.info("🔄 Starting model retraining...")
            
            # Initialize new pipeline
            new_pipeline = SteamPriceMLPipeline(self.db_path)
            
            # Load and prepare data
            X, y = new_pipeline.load_and_prepare_data()
            
            if len(X) < 20:
                return {
                    'success': False,
                    'error': 'Insufficient data for retraining'
                }
            
            # Train models
            results = new_pipeline.train_models(X, y)
            
            # Save new model
            model_saved = new_pipeline.save_model(self.model_path)
            
            if model_saved:
                # Reload the model
                self._load_model()
                
                return {
                    'success': True,
                    'message': 'Model retrained successfully',
                    'best_model': new_pipeline.best_model,
                    'training_samples': len(X),
                    'model_performance': {
                        model_name: {
                            'accuracy': metrics['accuracy'],
                            'cv_score': metrics['cv_mean']
                        }
                        for model_name, metrics in results.items()
                    },
                    'retrain_date': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to save retrained model'
                }
                
        except Exception as e:
            logger.error(f"❌ Model retraining failed: {e}")
            return {
                'success': False,
                'error': f'Retraining failed: {str(e)}'
            }

# Global ML service instance
_ml_service = None

def get_ml_service(db_path: str) -> RealMLPredictionService:
    """
    Get or create ML service instance (singleton pattern)
    """
    global _ml_service
    
    if _ml_service is None:
        _ml_service = RealMLPredictionService(db_path)
    
    return _ml_service

def init_ml_service(db_path: str):
    """
    Initialize ML service at application startup
    """
    global _ml_service
    _ml_service = RealMLPredictionService(db_path)
    return _ml_service