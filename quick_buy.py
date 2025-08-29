"""
PRYZOR - Interface de Linha de Comando para Análise de Compra
============================================================
Sistema de consulta rápida para análise de oportunidade de compra de jogos.

Este módulo fornece uma interface simples via terminal para:
- Análise rápida de jogos específicos
- Consulta interativa com o sistema
- Demonstração dos algoritmos implementados

Uso:
    python quick_buy.py "Nome do Jogo"
    python quick_buy.py  # Para modo interativo

Autor: Gustavo Peruci
Projeto Universitário - Análise de Dados
"""

import sys
from buy_analyzer import SimpleBuyingAnalyzer

def executar_analise_rapida(nome_jogo):
    """
    Executa análise rápida de oportunidade de compra para um jogo.
    
    Args:
        nome_jogo (str): Nome do jogo para análise
        
    Returns:
        dict: Resultado da análise com score e recomendação
    """
    analyzer = SimpleBuyingAnalyzer()
    return analyzer.analyze_game(nome_jogo)

def main():
    """Função principal que coordena a execução do programa."""
    if len(sys.argv) > 1:
        # Modo linha de comando: python quick_buy.py "nome do jogo"
        nome_jogo = " ".join(sys.argv[1:])
        print(f"🚀 ANÁLISE RÁPIDA DE: {nome_jogo}")
        print("=" * 60)
        resultado = executar_analise_rapida(nome_jogo)
        print(resultado)  # Imprime o resultado da análise
    else:
        # Modo interativo
        analyzer = SimpleBuyingAnalyzer()
        
        print("🎯 ANALISADOR RÁPIDO DE COMPRAS")
        print("=" * 40)
        print("💡 Dica: Para análise direta use: python quick_buy.py 'nome do jogo'")
        
        while True:
            nome_jogo = input("\n🎮 Jogo para analisar (ou 'sair'): ").strip()
            
            if nome_jogo.lower() in ['sair', 'exit', 'quit', '']:
                print("👋 Até mais!")
                break
            
            print()
            resultado = analyzer.analyze_game(nome_jogo)
            print(resultado)  # Imprime o resultado da análise
            
            if resultado:
                print("\n" + "="*50)
                choice = input("🔄 Analisar outro jogo? (s/n): ").strip().lower()
                if choice not in ['s', 'sim', 'y', 'yes']:
                    break

if __name__ == "__main__":
    main()
