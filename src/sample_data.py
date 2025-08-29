"""
Dados de demonstração para quando o banco MySQL não estiver disponível.
"""

SAMPLE_GAMES = [
    {
        'steam_id': 730,
        'nome': 'Counter-Strike 2',
        'preco_atual': 0.0,
        'desconto_atual': 0,
        'categoria': 'FPS',
        'data_lancamento': '2012-08-21',
        'avaliacoes_positivas': 85
    },
    {
        'steam_id': 570,
        'nome': 'Dota 2',
        'preco_atual': 0.0,
        'desconto_atual': 0,
        'categoria': 'MOBA',
        'data_lancamento': '2013-07-09',
        'avaliacoes_positivas': 82
    },
    {
        'steam_id': 440,
        'nome': 'Team Fortress 2',
        'preco_atual': 0.0,
        'desconto_atual': 0,
        'categoria': 'FPS',
        'data_lancamento': '2007-10-10',
        'avaliacoes_positivas': 92
    },
    {
        'steam_id': 271590,
        'nome': 'Grand Theft Auto V',
        'preco_atual': 89.90,
        'desconto_atual': 50,
        'categoria': 'Action',
        'data_lancamento': '2015-04-14',
        'avaliacoes_positivas': 88
    },
    {
        'steam_id': 1172470,
        'nome': 'Apex Legends',
        'preco_atual': 0.0,
        'desconto_atual': 0,
        'categoria': 'Battle Royale',
        'data_lancamento': '2020-11-04',
        'avaliacoes_positivas': 79
    }
]

SAMPLE_PREDICTIONS = [
    {
        'steam_id': 271590,
        'nome': 'Grand Theft Auto V',
        'preco_atual': 89.90,
        'preco_previsto': 67.43,
        'desconto_esperado': 25,
        'score_compra': 75,
        'recomendacao': 'Comprar agora',
        'confianca': 85
    },
    {
        'steam_id': 730,
        'nome': 'Counter-Strike 2',
        'preco_atual': 0.0,
        'preco_previsto': 0.0,
        'desconto_esperado': 0,
        'score_compra': 95,
        'recomendacao': 'Jogo gratuito',
        'confianca': 100
    }
]

SAMPLE_TEMPORAL_VALIDATION = {
    'summary': {
        'total_predictions': 150,
        'unique_games': 25,
        'period_start': '2024-01-01',
        'period_end': '2024-08-29',
        'mean_error': 8.5,
        'median_error': 6.2,
        'max_error': 25.0,
        'mean_error_pct': 12.3,
        'r2_approx': 0.78
    },
    'games_analysis': [
        {
            'nome': 'Grand Theft Auto V',
            'total_predictions': 15,
            'mean_error': 7.2,
            'mean_error_pct': 10.1,
            'best_prediction': 95.2,
            'worst_prediction': 76.8
        },
        {
            'nome': 'The Witcher 3',
            'total_predictions': 12,
            'mean_error': 5.8,
            'mean_error_pct': 8.7,
            'best_prediction': 98.5,
            'worst_prediction': 82.1
        }
    ]
}
