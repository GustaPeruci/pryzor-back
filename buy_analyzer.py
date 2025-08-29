"""
PRYZOR - Analisador de Oportunidade de Compra
==============================================
Sistema de Análise Estatística para Recomendação de Compra de Jogos

Este módulo implementa um algoritmo de análise baseado em:
- Posição percentil do preço atual
- Análise de tendências recentes
- Histórico de descontos
- Score ponderado de 0-100

Autor: Gustavo Peruci
Projeto Universitário - Análise de Dados
"""

from datetime import datetime, timedelta
from src.database_manager import DatabaseManager
import statistics

class SimpleBuyingAnalyzer:
    """
    Classe principal para análise de oportunidade de compra.
    
    O sistema funciona calculando um score de 0-100 baseado em:
    - 40% do peso: posição do preço atual (percentil)
    - 30% do peso: tendência recente de preços
    - 20% do peso: análise de descontos históricos
    - 10% do peso: ajustes para jogos gratuitos
    """
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def buscar_dados_jogo(self, nome_jogo):
        """
        Busca dados históricos de um jogo específico.
        
        Args:
            nome_jogo (str): Nome do jogo para buscar
            
        Returns:
            tuple: (nome_exato, dados_historicos) ou (None, None) se não encontrado
        """
        cursor = self.db.get_connection().cursor()
        
        # Busca flexível por nome (permite busca parcial)
        cursor.execute("SELECT id, name FROM games WHERE name LIKE %s", (f"%{nome_jogo}%",))
        resultado = cursor.fetchone()
        
        if not resultado:
            return None, None
        
        game_id, nome_exato = resultado
        
        # Buscar histórico de preços ordenado por data
        cursor.execute("""
            SELECT price, discount_percent, timestamp
            FROM price_history 
            WHERE game_id = %s
            ORDER BY timestamp
        """, (game_id,))
        
        dados_historicos = cursor.fetchall()
        return nome_exato, dados_historicos
    
    def analisar_posicao_preco(self, precos):
        """
        Analisa a posição do preço atual em relação ao histórico.
        
        Calcula o percentil do preço atual e determina se está
        em uma faixa favorável para compra (preços baixos = bom para comprar).
        
        Args:
            precos (list): Lista de preços históricos
            
        Returns:
            tuple: (posicao_textual, score_0_100, estatisticas_detalhadas)
        """
        if len(precos) < 2:
            return "indefinido", 50, {}
        
        preco_atual = float(precos[-1])
        todos_precos = [float(p) for p in precos]
        
        # Cálculo de estatísticas descritivas
        preco_min = min(todos_precos)
        preco_max = max(todos_precos)
        preco_medio = statistics.mean(todos_precos)
        preco_mediano = statistics.median(todos_precos)
        
        # Cálculo do percentil (quantos preços são menores que o atual)
        precos_menores = sum(1 for p in todos_precos if p < preco_atual)
        percentil = int((precos_menores / len(todos_precos)) * 100)
        
        # Determinação da posição textual
        if percentil <= 20:
            posicao = "muito baixo"
            score = 90  # Excelente para comprar
        elif percentil <= 40:
            posicao = "baixo"
            score = 75  # Bom para comprar
        elif percentil <= 60:
            posicao = "médio"
            score = 50  # Neutro
        elif percentil <= 80:
            posicao = "alto"
            score = 25  # Não recomendado
        else:
            posicao = "muito alto"
            score = 10  # Definitivamente não comprar
        
        estatisticas = {
            'current': preco_atual,
            'min': preco_min,
            'max': preco_max,
            'avg': preco_medio,
            'median': preco_mediano
        }
        
        return posicao, score, estatisticas
        median_price = statistics.median(all_prices)
        
        # Posição percentual do preço atual
        if max_price == min_price:
            percentile = 50
        else:
            percentile = (current_price - min_price) / (max_price - min_price) * 100
        
        # Classificar posição
        if percentile <= 20:
            position = "muito baixo"
            score = 90
        elif percentile <= 40:
            position = "baixo"
            score = 75
        elif percentile <= 60:
            position = "médio"
            score = 50
        elif percentile <= 80:
            position = "alto"
            score = 25
        else:
            position = "muito alto"
            score = 10
        
        return position, score, {
            'current': current_price,
            'min': min_price,
            'max': max_price,
            'avg': avg_price,
            'median': median_price,
            'percentile': percentile
        }
    
    def analyze_recent_trend(self, data):
        """Analisa tendência recente (últimos registros)"""
        if len(data) < 3:
            return "indefinido", 0
        
        # Pegar últimos 5 registros ou todos se menos que 5
        recent_count = min(5, len(data))
        recent_data = data[-recent_count:]
        
        prices = [float(row[0]) for row in recent_data]
        
        # Comparar primeiro e último preço do período recente
        price_change = prices[-1] - prices[0]
        price_change_pct = (price_change / prices[0]) * 100 if prices[0] > 0 else 0
        
        if abs(price_change_pct) < 5:
            trend = "estável"
            trend_score = 0
        elif price_change_pct > 0:
            trend = "subindo"
            trend_score = -10  # Ruim para comprar
        else:
            trend = "descendo"
            trend_score = 15   # Bom para comprar
        
        return trend, trend_score, price_change_pct
    
    def analyze_discounts(self, data):
        """Analisa padrão de descontos"""
        discount_records = [row for row in data if float(row[1]) > 0]
        
        if not discount_records:
            return {
                'has_discounts': False,
                'score': 0,
                'message': "Jogo nunca teve desconto registrado"
            }
        
        # Estatísticas de desconto
        discounts = [float(row[1]) for row in discount_records]
        avg_discount = statistics.mean(discounts)
        max_discount = max(discounts)
        discount_freq = len(discount_records) / len(data) * 100
        
        # Último desconto
        last_discount_date = max([row[2] for row in discount_records])
        days_since_discount = (datetime.now() - last_discount_date).days
        
        # Score baseado em padrões
        score = 0
        
        if avg_discount > 30:
            score += 10  # Descontos bons
        
        if discount_freq > 20:
            score -= 5   # Frequente em promoção - pode esperar
        
        if days_since_discount > 60:
            score += 10  # Faz tempo que não tem desconto
        elif days_since_discount < 7:
            score += 15  # Desconto muito recente
        
        message = f"Desconto médio: {avg_discount:.0f}%, máximo: {max_discount:.0f}%"
        if days_since_discount:
            message += f", último há {days_since_discount} dias"
        
        return {
            'has_discounts': True,
            'avg_discount': avg_discount,
            'max_discount': max_discount,
            'frequency': discount_freq,
            'days_since': days_since_discount,
            'score': score,
            'message': message
        }
    
    def calculate_final_score(self, price_score, trend_score, discount_score, current_price):
        """Calcula score final de recomendação"""
        
        # Jogo gratuito
        if current_price == 0:
            return 100
        
        # Score base a partir do preço
        base_score = price_score + trend_score + discount_score
        
        # Normalizar entre 0-100
        final_score = max(0, min(100, base_score))
        
        return final_score
    
    def get_recommendation(self, score, price_stats, trend_info, discount_info):
        """Gera recomendação final"""
        
        if price_stats['current'] == 0:
            return {
                'emoji': '🎮',
                'title': 'JOGO GRATUITO',
                'message': 'Baixe agora mesmo!',
                'action': 'Instalar'
            }
        
        if score >= 80:
            emoji = '💚'
            title = 'COMPRE AGORA'
            message = 'Excelente oportunidade!'
            action = 'Comprar'
        elif score >= 65:
            emoji = '💛'
            title = 'BOM MOMENTO'
            message = 'Boa oportunidade de compra'
            action = 'Considerar compra'
        elif score >= 45:
            emoji = '🧡'
            title = 'MOMENTO NEUTRO'
            message = 'Depende da sua prioridade'
            action = 'Avaliar'
        else:
            emoji = '❤️'
            title = 'AGUARDAR'
            message = 'Melhor esperar uma oportunidade'
            action = 'Aguardar promoção'
        
        return {
            'emoji': emoji,
            'title': title,
            'message': message,
            'action': action
        }
    
    def analyze_game(self, game_name):
        """Análise completa de um jogo"""
        print(f"🔍 ANALISANDO: {game_name}")
        print("=" * 50)
        
        # Buscar dados
        exact_name, data = self.get_game_data(game_name)
        
        if exact_name is None:
            print(f"❌ Jogo '{game_name}' não encontrado!")
            print("💡 Use list_games() para ver jogos disponíveis")
            return None
        
        if not data or len(data) < 2:
            print(f"❌ Dados insuficientes para '{exact_name}'")
            print(f"   Apenas {len(data) if data else 0} registros encontrados")
            return None
        
        print(f"✅ Jogo: {exact_name}")
        print(f"📊 Registros: {len(data)}")
        print(f"📅 Período: {data[0][2].strftime('%Y-%m-%d')} até {data[-1][2].strftime('%Y-%m-%d')}")
        
        # Análises
        prices = [row[0] for row in data]
        position, price_score, price_stats = self.analyze_price_position(prices)
        trend, trend_score, trend_pct = self.analyze_recent_trend(data)
        discount_info = self.analyze_discounts(data)
        
        # Score final
        final_score = self.calculate_final_score(
            price_score, trend_score, discount_info['score'], price_stats['current']
        )
        
        # Recomendação
        recommendation = self.get_recommendation(final_score, price_stats, 
                                               (trend, trend_pct), discount_info)
        
        # Exibir resultados
        print(f"\n💰 PREÇO ATUAL: R$ {price_stats['current']:.2f}")
        print(f"📊 POSIÇÃO NO HISTÓRICO: {position.upper()} ({price_stats['percentile']:.0f}° percentil)")
        print(f"📈 TENDÊNCIA RECENTE: {trend.upper()}", end="")
        if trend != "indefinido":
            print(f" ({trend_pct:+.1f}%)")
        else:
            print()
        
        print(f"🏷️ DESCONTOS: {discount_info['message']}")
        
        print(f"\n{recommendation['emoji']} RECOMENDAÇÃO (Score: {final_score}/100):")
        print(f"   {recommendation['title']}: {recommendation['message']}")
        print(f"   Ação sugerida: {recommendation['action']}")
        
        # Detalhes do preço
        print(f"\n📋 ESTATÍSTICAS DE PREÇO:")
        print(f"   Mínimo histórico: R$ {price_stats['min']:.2f}")
        print(f"   Máximo histórico: R$ {price_stats['max']:.2f}")
        print(f"   Preço médio: R$ {price_stats['avg']:.2f}")
        print(f"   Mediana: R$ {price_stats['median']:.2f}")
        
        # Dicas específicas
        print(f"\n💡 DICAS:")
        if final_score >= 75:
            print("   • Preço está em ótima oportunidade")
            if trend == "descendo":
                print("   • Tendência de queda - aproveite!")
        elif final_score >= 50:
            print("   • Preço razoável, depende do seu interesse")
        else:
            print("   • Recomendo aguardar uma promoção melhor")
            if discount_info['has_discounts']:
                print(f"   • Este jogo costuma ter até {discount_info['max_discount']:.0f}% de desconto")
        
        return {
            'game': exact_name,
            'score': final_score,
            'recommendation': recommendation,
            'price_stats': price_stats,
            'trend': trend
        }
    
    def list_games(self):
        """Lista jogos disponíveis para análise"""
        cursor = self.db.get_connection().cursor()
        
        cursor.execute("""
            SELECT g.name, COUNT(ph.id) as records,
                   MIN(ph.price) as min_price, MAX(ph.price) as max_price,
                   MAX(ph.timestamp) as last_update
            FROM games g
            JOIN price_history ph ON g.id = ph.game_id
            GROUP BY g.id, g.name
            HAVING records >= 2
            ORDER BY records DESC, g.name
        """)
        
        games = cursor.fetchall()
        
        print("🎮 JOGOS DISPONÍVEIS PARA ANÁLISE:")
        print("=" * 70)
        print("Nome                             | Dados | Preço Min-Max  | Última Atualização")
        print("-" * 70)
        
        for name, records, min_price, max_price, last_update in games:
            min_p = float(min_price)
            max_p = float(max_price)
            
            if min_p == max_p == 0:
                price_range = "GRATUITO     "
            elif min_p == 0:
                price_range = f"R$ 0-{max_p:.0f}    "
            else:
                price_range = f"R$ {min_p:.0f}-{max_p:.0f}"
            
            last_date = last_update.strftime('%Y-%m-%d')
            
            print(f"{name[:32]:32} | {records:4d}  | {price_range:14} | {last_date}")
        
        return games


def main():
    """Interface principal"""
    analyzer = SimpleBuyingAnalyzer()
    
    print("🎯 ANALISADOR DE OPORTUNIDADE DE COMPRA")
    print("=" * 50)
    print("Digite o nome de um jogo para saber se é bom momento para comprar!")
    
    while True:
        print("\n📋 OPÇÕES:")
        print("1. Analisar jogo específico")
        print("2. Ver jogos disponíveis")
        print("0. Sair")
        
        choice = input("\n🎯 Escolha: ").strip()
        
        if choice == "1":
            game_name = input("\n🎮 Nome do jogo: ").strip()
            if game_name:
                print()
                analyzer.analyze_game(game_name)
            else:
                print("❌ Digite um nome válido!")
                
        elif choice == "2":
            print()
            analyzer.list_games()
            
        elif choice == "0":
            print("\n👋 Até mais!")
            break
            
        else:
            print("❌ Opção inválida!")


if __name__ == "__main__":
    main()
