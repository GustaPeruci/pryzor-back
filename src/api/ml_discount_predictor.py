"""
ML Discount Predictor Service - Modelo v2.0
Serviço de predição integrado ao pryzor-back
Prevê se um jogo terá desconto >20% nos próximos 30 dias
"""

import os
import pickle
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import mysql.connector
from mysql.connector import Error

logger = logging.getLogger(__name__)


class MLDiscountPredictor:
    """
    Serviço de predição usando modelo v2.0 (RandomForest com validação temporal)
    """
    
    def __init__(self, mysql_config: Dict[str, Any]):
        self.mysql_config = mysql_config
        self.model = None
        self.features = []
        self.metrics = {}
        self.version = "unknown"
        self.validation_method = "unknown"
        self.trained_at = None
        self._load_model()
    
    def _get_model_path(self) -> str:
        """Resolve o caminho do modelo"""
        # Prioridade: variável de ambiente > caminho padrão
        env_path = os.getenv("ML_MODEL_PATH")
        if env_path and os.path.exists(env_path):
            return env_path
        
        # Caminho padrão: pryzor-back/ml_model/discount_predictor.pkl
        here = os.path.dirname(__file__)
        default_path = os.path.join(here, "..", "..", "ml_model", "discount_predictor.pkl")
        return os.path.abspath(default_path)
    
    def _load_model(self) -> bool:
        """Carrega o modelo treinado"""
        try:
            model_path = self._get_model_path()
            
            if not os.path.exists(model_path):
                logger.warning(f"⚠️ Modelo não encontrado: {model_path}")
                return False
            
            with open(model_path, 'rb') as f:
                model_pkg = pickle.load(f)
            
            # Extrair componentes do pacote
            self.model = model_pkg.get('model')
            self.features = model_pkg.get('feature_names', model_pkg.get('features', []))
            self.metrics = model_pkg.get('metrics', {})
            self.version = model_pkg.get('version', 'unknown')
            self.validation_method = model_pkg.get('validation_method', 'unknown')
            self.trained_at = model_pkg.get('trained_at')
            
            # Validar modelo
            if self.model is None:
                logger.error("❌ Modelo não encontrado no pacote")
                return False
            
            if not self.features:
                logger.error("❌ Lista de features vazia")
                return False
            
            logger.info(f"✅ Modelo v{self.version} carregado com sucesso")
            logger.info(f"   Validação: {self.validation_method}")
            logger.info(f"   Features: {len(self.features)}")
            logger.info(f"   F1-Score: {self.metrics.get('f1_score', 'N/A'):.4f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo: {e}")
            return False
    
    def is_loaded(self) -> bool:
        """Verifica se o modelo está carregado"""
        return self.model is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o modelo"""
        return {
            'loaded': self.is_loaded(),
            'version': self.version,
            'validation_method': self.validation_method,
            'trained_at': self.trained_at,
            'features_count': len(self.features),
            'metrics': {
                'f1_score': self.metrics.get('f1_score'),
                'precision': self.metrics.get('precision'),
                'recall': self.metrics.get('recall'),
                'accuracy': self.metrics.get('accuracy'),
                'roc_auc': self.metrics.get('roc_auc'),
            }
        }
    
    def _get_price_history(self, appid: int, days: int = 120) -> Optional[pd.DataFrame]:
        """
        Busca histórico de preços do banco de dados
        """
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    date,
                    final_price,
                    discount
                FROM price_history
                WHERE appid = %s
                ORDER BY date DESC
                LIMIT %s
            """
            
            cursor.execute(query, (appid, days))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not rows:
                return None
            
            df = pd.DataFrame(rows)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            return df
            
        except Error as e:
            logger.error(f"Erro ao buscar histórico de preços para appid {appid}: {e}")
            return None
    
    def _get_game_info(self, appid: int) -> Optional[Dict[str, Any]]:
        """Busca informações do jogo"""
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    appid,
                    name,
                    type,
                    freetoplay as free_to_play
                FROM games
                WHERE appid = %s
            """
            
            cursor.execute(query, (appid,))
            game = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return game
            
        except Error as e:
            logger.error(f"Erro ao buscar info do jogo {appid}: {e}")
            return None
    
    def _engineer_features(self, price_history: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Gera features a partir do histórico de preços
        Deve replicar exatamente o feature engineering usado no treinamento
        """
        try:
            if len(price_history) < 30:
                return None
            
            # Pegar o registro mais recente
            latest = price_history.iloc[-1]
            
            # Features temporais
            latest_date = latest['date']
            
            features = {
                'discount_percent': float(latest['discount']),
                'final_price': float(latest['final_price']),
                'month': latest_date.month,
                'quarter': (latest_date.month - 1) // 3 + 1,
                'day_of_week': latest_date.dayofweek,
                'is_weekend': 1 if latest_date.dayofweek >= 5 else 0,
            }
            
            # Features sazonais (Steam Sales)
            # Winter Sale: dezembro/janeiro
            # Summer Sale: junho/julho
            features['is_winter_sale'] = 1 if latest_date.month in [12, 1] else 0
            features['is_summer_sale'] = 1 if latest_date.month in [6, 7] else 0
            
            return features
            
        except Exception as e:
            logger.error(f"Erro ao gerar features: {e}")
            return None
    
    def predict(self, appid: int) -> Dict[str, Any]:
        """
        Faz predição para um jogo específico
        
        Returns:
            Dict com:
            - will_have_discount: bool (predição)
            - probability: float (probabilidade da classe positiva)
            - confidence: float (confiança na predição)
            - current_discount: float (desconto atual)
            - recommendation: str (recomendação textual)
            - reasoning: List[str] (fatores que influenciaram)
        """
        if not self.is_loaded():
            return {
                'error': 'Modelo não carregado',
                'appid': appid,
                'model_loaded': False
            }
        
        try:
            # Buscar informações do jogo
            game_info = self._get_game_info(appid)
            if not game_info:
                return {
                    'error': 'Jogo não encontrado',
                    'appid': appid
                }
            
            # Verificar se é free-to-play
            if game_info.get('free_to_play'):
                return {
                    'appid': appid,
                    'game_name': game_info.get('name'),
                    'will_have_discount': False,
                    'probability': 0.0,
                    'confidence': 1.0,
                    'current_discount': 0,
                    'recommendation': 'Jogo gratuito - sem necessidade de esperar desconto',
                    'reasoning': ['Jogo é free-to-play'],
                    'model_version': self.version
                }
            
            # Buscar histórico de preços
            price_history = self._get_price_history(appid, days=120)
            if price_history is None or len(price_history) < 30:
                return {
                    'error': 'Histórico de preços insuficiente',
                    'appid': appid,
                    'game_name': game_info.get('name'),
                    'min_required': 30,
                    'found': len(price_history) if price_history is not None else 0
                }
            
            # Gerar features
            features_dict = self._engineer_features(price_history)
            if features_dict is None:
                return {
                    'error': 'Erro ao gerar features',
                    'appid': appid
                }
            
            # Criar DataFrame com features na ordem correta
            feature_vector = pd.DataFrame([features_dict])[self.features]
            
            # Fazer predição
            prediction = self.model.predict(feature_vector)[0]
            probabilities = self.model.predict_proba(feature_vector)[0]
            
            # Probabilidade da classe positiva (terá desconto)
            prob_discount = probabilities[1]
            
            # Confiança = distância da decisão (quão longe está de 0.5)
            confidence = abs(prob_discount - 0.5) * 2
            
            # Gerar recomendação
            current_discount = features_dict['discount_percent']
            
            reasoning = []
            if current_discount > 0:
                reasoning.append(f"Jogo atualmente com {current_discount:.0f}% de desconto")
            
            if features_dict['is_summer_sale']:
                reasoning.append("Período de Summer Sale (junho/julho)")
            elif features_dict['is_winter_sale']:
                reasoning.append("Período de Winter Sale (dezembro/janeiro)")
            
            # Determinar recomendação baseada na probabilidade
            if prob_discount > 0.7:
                recommendation = "WAIT"
                recommendation_text = "Alta probabilidade de desconto melhor nos próximos 30 dias"
                reasoning.append(f"Probabilidade de {prob_discount*100:.0f}% de desconto >20%")
            elif prob_discount > 0.5:
                recommendation = "WAIT"
                recommendation_text = "Probabilidade moderada de desconto nos próximos 30 dias"
                reasoning.append(f"Probabilidade de {prob_discount*100:.0f}% de desconto >20%")
            elif current_discount > 50:
                recommendation = "BUY"
                recommendation_text = "Desconto atual é excelente"
                reasoning.append(f"Desconto de {current_discount:.0f}% já está ótimo")
            else:
                recommendation = "BUY"
                recommendation_text = "Baixa probabilidade de desconto melhor em breve"
                reasoning.append(f"Apenas {prob_discount*100:.0f}% de chance de desconto >20%")
            
            return {
                'appid': appid,
                'game_name': game_info.get('name'),
                'will_have_discount': bool(prediction),
                'probability': float(prob_discount),
                'confidence': float(confidence),
                'current_discount': float(current_discount),
                'current_price': float(price_history.iloc[-1]['final_price']),
                'last_price_date': price_history.iloc[-1]['date'].strftime('%Y-%m-%d'),
                'recommendation': recommendation,
                'recommendation_text': recommendation_text,
                'reasoning': reasoning,
                'model_version': self.version,
                'prediction_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao fazer predição para appid {appid}: {e}")
            return {
                'error': str(e),
                'appid': appid
            }
    
    def batch_predict(self, appids: List[int], max_items: int = 50) -> Dict[str, Any]:
        """
        Faz predições em lote
        """
        if len(appids) > max_items:
            return {
                'error': f'Máximo de {max_items} jogos por requisição',
                'requested': len(appids),
                'max_allowed': max_items
            }
        
        results = []
        errors = []
        
        for appid in appids:
            result = self.predict(appid)
            if 'error' in result:
                errors.append(result)
            else:
                results.append(result)
        
        return {
            'predictions': results,
            'errors': errors,
            'total_requested': len(appids),
            'successful': len(results),
            'failed': len(errors),
            'model_version': self.version
        }
