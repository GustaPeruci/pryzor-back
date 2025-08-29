"""
Análise básica de preços usando banco normalizado
Fase 1.1: Primeira análise com dados migrados
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import os

# Adiciona o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from database_manager import DatabaseManager

class BasicAnalyzer:
    def __init__(self):
        """Inicializa o analisador básico"""
        self.db = DatabaseManager()
        self.output_path = Path(__file__).parent.parent / "data" / "analysis_output"
        self.output_path.mkdir(exist_ok=True)
        
        # Configuração para gráficos
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def get_summary_stats(self):
        """Retorna estatísticas resumidas dos dados"""
        print("📊 ESTATÍSTICAS GERAIS DO BANCO")
        print("=" * 50)
        
        stats = self.db.get_database_stats()
        for key, value in stats.items():
            print(f"📈 {key.replace('_', ' ').title()}: {value}")
        
        return stats
    
    def analyze_price_trends(self):
        """Analisa tendências de preço por jogo"""
        print("\n📈 ANÁLISE DE TENDÊNCIAS DE PREÇO")
        print("=" * 50)
        
        # Busca dados dos últimos 2 anos
        df = self.db.get_price_history(start_date='2023-01-01')
        
        if df.empty:
            print("❌ Nenhum dado encontrado para análise")
            return
        
        # Converte data para datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Estatísticas por jogo
        game_stats = df.groupby('name').agg({
            'price': ['min', 'max', 'mean', 'std', 'count'],
            'date': ['min', 'max']
        }).round(2)
        
        game_stats.columns = ['Preço_Min', 'Preço_Max', 'Preço_Médio', 'Desvio_Padrão', 'Registros', 'Data_Inicial', 'Data_Final']
        game_stats['Variação_%'] = ((game_stats['Preço_Max'] - game_stats['Preço_Min']) / game_stats['Preço_Min'] * 100).round(1)
        
        print("\n🎮 ESTATÍSTICAS POR JOGO:")
        print(game_stats.to_string())
        
        # Salva estatísticas
        game_stats.to_csv(self.output_path / "game_statistics.csv")
        print(f"\n💾 Estatísticas salvas em: {self.output_path / 'game_statistics.csv'}")
        
        return game_stats
    
    def find_best_deals(self, top_n=5):
        """Encontra as melhores oportunidades de compra"""
        print(f"\n🔥 TOP {top_n} OPORTUNIDADES DE COMPRA")
        print("=" * 50)
        
        # Busca preços atuais vs histórico
        latest_prices = self.db.get_latest_prices()
        all_history = self.db.get_price_history()
        
        if latest_prices.empty or all_history.empty:
            print("❌ Dados insuficientes para análise")
            return
        
        deals = []
        
        for _, row in latest_prices.iterrows():
            game_name = row['name']
            current_price = row['price']
            
            # Histórico do jogo
            game_history = all_history[all_history['name'] == game_name]
            
            if len(game_history) > 5:  # Mínimo de 5 registros
                min_price = game_history['price'].min()
                max_price = game_history['price'].max()
                avg_price = game_history['price'].mean()
                
                # Calcula score da oportunidade (0-100)
                # Quanto menor o preço atual em relação ao histórico, melhor
                price_position = (current_price - min_price) / (max_price - min_price) if max_price > min_price else 0.5
                discount_from_avg = (avg_price - current_price) / avg_price if avg_price > 0 else 0
                
                opportunity_score = max(0, min(100, (1 - price_position) * 50 + discount_from_avg * 50))
                
                deals.append({
                    'Jogo': game_name,
                    'Preço_Atual': f"R$ {current_price:.2f}",
                    'Preço_Mínimo': f"R$ {min_price:.2f}",
                    'Preço_Médio': f"R$ {avg_price:.2f}",
                    'Score_Oportunidade': f"{opportunity_score:.1f}/100",
                    'Recomendação': self._get_recommendation(opportunity_score)
                })
        
        # Ordena por score
        deals_df = pd.DataFrame(deals)
        if not deals_df.empty:
            deals_df['Score_Num'] = deals_df['Score_Oportunidade'].str.extract(r'(\d+\.?\d*)').astype(float)
            deals_df = deals_df.sort_values('Score_Num', ascending=False).head(top_n)
            deals_df = deals_df.drop('Score_Num', axis=1)
            
            print(deals_df.to_string(index=False))
            
            # Salva análise
            deals_df.to_csv(self.output_path / "best_deals.csv", index=False)
            print(f"\n💾 Análise salva em: {self.output_path / 'best_deals.csv'}")
        
        return deals_df
    
    def _get_recommendation(self, score):
        """Retorna recomendação baseada no score"""
        if score >= 80:
            return "🔥 COMPRE AGORA!"
        elif score >= 60:
            return "👍 Boa oportunidade"
        elif score >= 40:
            return "🤔 Preço razoável"
        elif score >= 20:
            return "⏳ Espere mais"
        else:
            return "❌ Preço alto"
    
    def create_price_chart(self, game_name=None):
        """Cria gráfico de evolução de preços"""
        print("\n📊 GERANDO GRÁFICO DE PREÇOS")
        print("=" * 50)
        
        df = self.db.get_price_history()
        
        if df.empty:
            print("❌ Nenhum dado para gráfico")
            return
        
        df['date'] = pd.to_datetime(df['date'])
        
        # Se jogo específico foi solicitado
        if game_name:
            df = df[df['name'].str.contains(game_name, case=False, na=False)]
            if df.empty:
                print(f"❌ Jogo '{game_name}' não encontrado")
                return
        
        # Cria gráfico
        plt.figure(figsize=(15, 8))
        
        for game in df['name'].unique()[:10]:  # Máximo 10 jogos para legibilidade
            game_data = df[df['name'] == game].sort_values('date')
            plt.plot(game_data['date'], game_data['price'], marker='o', linewidth=2, label=game, alpha=0.8)
        
        plt.title('Evolução de Preços dos Jogos', fontsize=16, fontweight='bold')
        plt.xlabel('Data', fontsize=12)
        plt.ylabel('Preço (R$)', fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Salva gráfico
        chart_path = self.output_path / "price_evolution.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"📊 Gráfico salvo em: {chart_path}")
    
    def run_basic_analysis(self):
        """Executa análise básica completa"""
        print("🔍 INICIANDO ANÁLISE BÁSICA DOS DADOS")
        print("=" * 60)
        
        # 1. Estatísticas gerais
        self.get_summary_stats()
        
        # 2. Análise de tendências
        self.analyze_price_trends()
        
        # 3. Melhores oportunidades
        self.find_best_deals()
        
        # 4. Gráfico de evolução
        self.create_price_chart()
        
        print("\n✅ ANÁLISE BÁSICA CONCLUÍDA!")
        print(f"📁 Resultados salvos em: {self.output_path}")

if __name__ == "__main__":
    analyzer = BasicAnalyzer()
    analyzer.run_basic_analysis()
